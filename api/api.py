import os
import sys
import time
import uuid
import shutil
import tempfile
from io import StringIO
from typing import Dict, List, Optional, Union, Tuple

# 强制使用CPU模式
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["OMP_NUM_THREADS"] = "1"

# 添加项目根目录到Python路径，以便能够导入本地模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Request, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader, DataWriter
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod
from magic_pdf.operators.models import InferenceResult
from magic_pdf.operators.pipes import PipeResult
import aiofiles
from pydantic import BaseModel
from loguru import logger

app = FastAPI(title="MinerU API", description="PDF解析和文档挖掘服务")

# 存储任务状态和结果的字典
tasks = {}

# 支持的文件扩展名
pdf_extensions = [".pdf"]
office_extensions = [".ppt", ".pptx", ".doc", ".docx"]
image_extensions = [".png", ".jpg", ".jpeg"]

class TaskStatus(BaseModel):
    id: str
    status: str  # "pending", "processing", "completed", "failed"
    filename: str
    created_at: float
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    result_path: Optional[str] = None
    result_content: Optional[str] = None

class MemoryDataWriter(DataWriter):
    """内存数据写入器，用于将结果保存到内存而非文件"""
    def __init__(self):
        self.buffer = StringIO()

    def write(self, path: str, data: bytes) -> None:
        if isinstance(data, str):
            self.buffer.write(data)
        else:
            self.buffer.write(data.decode("utf-8"))

    def write_string(self, path: str, data: str) -> None:
        self.buffer.write(data)

    def get_value(self) -> str:
        return self.buffer.getvalue()

    def close(self):
        self.buffer.close()

def init_writers(
    output_path: str,
    output_image_path: str,
) -> Tuple[FileBasedDataWriter, FileBasedDataWriter]:
    """
    初始化写入器
    
    Args:
        output_path: 输出目录路径
        output_image_path: 图像输出目录路径
        
    Returns:
        包含写入器的元组 (writer, image_writer)
    """
    # 创建目录
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(output_image_path, exist_ok=True)
    
    # 创建写入器
    writer = FileBasedDataWriter(output_path)
    image_writer = FileBasedDataWriter(output_image_path)
    
    return writer, image_writer

def process_file(
    file_bytes: bytes,
    file_extension: str,
    parse_method: str,
    image_writer: FileBasedDataWriter,
) -> Tuple[InferenceResult, PipeResult]:
    """
    处理文件内容
    
    Args:
        file_bytes: 文件的二进制内容
        file_extension: 文件扩展名
        parse_method: 解析方法 ('ocr', 'txt', 'auto')
        image_writer: 图像写入器
        
    Returns:
        返回推理结果和管道结果的元组
    """
    ds = None
    
    if file_extension.lower() in pdf_extensions:
        ds = PymuDocDataset(file_bytes)
    elif file_extension.lower() in office_extensions:
        # Office文件处理暂未实现
        raise HTTPException(status_code=400, detail="暂不支持Office文件格式")
    elif file_extension.lower() in image_extensions:
        # 图片文件处理暂未实现
        raise HTTPException(status_code=400, detail="暂不支持图片文件格式")
    else:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_extension}")
    
    infer_result = None
    pipe_result = None
    
    try:
        if parse_method == "ocr":
            infer_result = ds.apply(doc_analyze, ocr=True)
            pipe_result = infer_result.pipe_ocr_mode(image_writer)
        elif parse_method == "txt":
            infer_result = ds.apply(doc_analyze, ocr=False)
            pipe_result = infer_result.pipe_txt_mode(image_writer)
        else:  # auto
            if ds.classify() == SupportedPdfParseMethod.OCR:
                infer_result = ds.apply(doc_analyze, ocr=True)
                pipe_result = infer_result.pipe_ocr_mode(image_writer)
            else:
                infer_result = ds.apply(doc_analyze, ocr=False)
                pipe_result = infer_result.pipe_txt_mode(image_writer)
    except Exception as e:
        logger.error(f"处理文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理文件时出错: {str(e)}")
        
    return infer_result, pipe_result

@app.post("/upload/sync")
async def upload_sync(file: UploadFile = File(...), parse_method: str = "auto"):
    """
    同步上传并解析文件，等待解析完成后返回结果
    
    Args:
        file: 要上传的文件
        parse_method: 解析方法，可以是auto, ocr, txt。默认为auto。
    """
    # 准备环境
    task_id = str(uuid.uuid4())
    filename = file.filename
    file_extension = os.path.splitext(filename)[1]
    output_dir = f"output/{task_id}"
    local_image_dir = f"{output_dir}/images"
    image_dir = "images"

    try:
        # 初始化写入器
        md_writer, image_writer = init_writers(output_dir, local_image_dir)
        
        # 读取文件内容
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="上传文件为空")
        
        # 保存原始文件
        temp_file_path = f"{output_dir}/{filename}"
        async with aiofiles.open(temp_file_path, 'wb') as f:
            await f.write(file_content)
        
        # 处理文件
        _, pipe_result = process_file(file_content, file_extension, parse_method, image_writer)
        
        # 获取markdown内容
        md_content = pipe_result.get_markdown(image_dir)
        
        # 保存结果
        md_file_path = f"{output_dir}/result.md"
        async with aiofiles.open(md_file_path, 'w', encoding='utf-8') as f:
            await f.write(md_content)
        
        # 记录任务
        tasks[task_id] = TaskStatus(
            id=task_id,
            status="completed",
            filename=filename,
            created_at=time.time(),
            completed_at=time.time(),
            result_path=md_file_path,
            result_content=md_content
        )
        
        return {
            "task_id": task_id,
            "status": "completed",
            "message": "文件处理成功",
            "md_content": md_content
        }
    
    except HTTPException as he:
        # 直接重新抛出HTTP异常
        raise he
    except Exception as e:
        logger.error(f"处理文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

async def process_file_async(task_id: str, filename: str, file_path: str, parse_method: str = "auto"):
    """
    异步处理文件的后台任务
    """
    try:
        if task_id not in tasks:
            return
            
        output_dir = f"output/{task_id}"
        local_image_dir = f"{output_dir}/images"
        image_dir = "images"
        file_extension = os.path.splitext(filename)[1]
        
        # 更新任务状态
        tasks[task_id].status = "processing"
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            tasks[task_id].status = "failed"
            tasks[task_id].error_message = "找不到上传的文件"
            return
            
        # 读取文件
        with open(file_path, 'rb') as f:
            file_content = f.read()
            
        if not file_content:
            tasks[task_id].status = "failed"
            tasks[task_id].error_message = "文件内容为空"
            return
        
        # 初始化写入器
        md_writer, image_writer = init_writers(output_dir, local_image_dir)
        
        # 处理文件
        _, pipe_result = process_file(file_content, file_extension, parse_method, image_writer)
        
        # 获取markdown内容
        md_content = pipe_result.get_markdown(image_dir)
        
        # 保存结果
        md_file_path = f"{output_dir}/result.md"
        async with aiofiles.open(md_file_path, 'w', encoding='utf-8') as f:
            await f.write(md_content)
        
        # 更新任务状态为已完成
        tasks[task_id].status = "completed"
        tasks[task_id].completed_at = time.time()
        tasks[task_id].result_path = md_file_path
        tasks[task_id].result_content = md_content
        
    except Exception as e:
        logger.error(f"异步处理文件时出错: {str(e)}")
        # 更新任务状态为失败
        if task_id in tasks:
            tasks[task_id].status = "failed"
            tasks[task_id].error_message = str(e)

@app.post("/upload/async")
async def upload_async(background_tasks: BackgroundTasks, file: UploadFile = File(...), parse_method: str = "auto"):
    """
    异步上传文件，立即返回任务ID，后台处理文件
    
    Args:
        file: 要上传的文件
        parse_method: 解析方法，可以是auto, ocr, txt。默认为auto。
    """
    try:
        task_id = str(uuid.uuid4())
        filename = file.filename if file.filename else f"document_{task_id}.pdf"
        output_dir = f"output/{task_id}"
        
        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(f"{output_dir}/images", exist_ok=True)
        
        # 保存上传的文件
        temp_file_path = f"{output_dir}/{filename}"
        content = await file.read()
        
        if not content:
            return JSONResponse(
                status_code=400,
                content={"error": "上传文件为空"}
            )
        
        async with aiofiles.open(temp_file_path, 'wb') as f:
            await f.write(content)
        
        # 创建任务记录
        tasks[task_id] = TaskStatus(
            id=task_id,
            status="pending",
            filename=filename,
            created_at=time.time(),
            result_path=None
        )
        
        # 添加异步处理任务
        background_tasks.add_task(process_file_async, task_id, filename, temp_file_path, parse_method)
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "文件已接收，正在后台处理"
        }
    except Exception as e:
        logger.error(f"异步上传文件时出错: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"上传文件失败: {str(e)}"}
        )

@app.get("/tasks")
async def list_tasks():
    """
    获取所有任务列表
    """
    return {"tasks": list(tasks.values())}

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """
    获取指定任务的状态
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return tasks[task_id]

@app.get("/download/{task_id}")
async def download_result(task_id: str):
    """
    下载指定任务的处理结果
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    
    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"任务尚未完成，当前状态: {task.status}")
    
    if not task.result_path or not os.path.exists(task.result_path):
        raise HTTPException(status_code=404, detail="结果文件不存在")
    
    return FileResponse(
        path=task.result_path,
        filename=f"{task.filename.split('.')[0]}_result.md",
        media_type="text/markdown"
    )

@app.get("/download/{task_id}/zip")
async def download_result_zip(task_id: str):
    """
    下载指定任务的完整处理结果（包括图片）的ZIP压缩包
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    
    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"任务尚未完成，当前状态: {task.status}")
    
    output_dir = f"output/{task_id}"
    if not os.path.exists(output_dir):
        raise HTTPException(status_code=404, detail="结果目录不存在")
    
    # 创建ZIP文件
    zip_path = f"{output_dir}.zip"
    shutil.make_archive(output_dir, 'zip', output_dir)
    
    return FileResponse(
        path=zip_path,
        filename=f"{task.filename.split('.')[0]}_result.zip",
        media_type="application/zip"
    )

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """
    删除指定任务及其资源
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 删除任务目录
    output_dir = f"output/{task_id}"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    
    # 删除ZIP文件(如果存在)
    zip_path = f"{output_dir}.zip"
    if os.path.exists(zip_path):
        os.remove(zip_path)
    
    # 从字典中移除任务
    del tasks[task_id]
    
    return {"message": "任务已删除"}
    
