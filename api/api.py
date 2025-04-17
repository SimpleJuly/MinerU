import os
import sys
import time
import uuid
import shutil
from typing import Dict, List, Optional, Union

# 强制使用CPU模式
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["OMP_NUM_THREADS"] = "1"

# 添加项目根目录到Python路径，以便能够导入本地模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Request, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod
import aiofiles
from pydantic import BaseModel

app = FastAPI(title="MinerU API", description="PDF解析和文档挖掘服务")

# 存储任务状态和结果的字典
tasks = {}

class TaskStatus(BaseModel):
    id: str
    status: str  # "pending", "processing", "completed", "failed"
    filename: str
    created_at: float
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    result_path: Optional[str] = None

@app.post("/upload/sync")
async def upload_sync(file: UploadFile = File(...)):
    """
    同步上传并解析文件，等待解析完成后返回结果
    """
    # 准备环境
    task_id = str(uuid.uuid4())
    filename = file.filename
    output_dir = f"output/{task_id}"
    local_image_dir, local_md_dir = f"{output_dir}/images", output_dir
    image_dir = "images"

    os.makedirs(local_image_dir, exist_ok=True)

    try:
        # 使用 aiofiles 异步打开文件并写入数据
        temp_file_path = f"{output_dir}/{filename}"
        async with aiofiles.open(temp_file_path, 'wb') as f:
            await f.write(await file.read())
        
        with open(temp_file_path, 'rb') as f:
            pdf_bytes = f.read()
        
        # 创建输出目录
        image_writer = FileBasedDataWriter(local_image_dir)
        md_writer = FileBasedDataWriter(local_md_dir)
        
        # 创建数据集实例
        ds = PymuDocDataset(pdf_bytes)
        
        # 推理
        if ds.classify() == SupportedPdfParseMethod.OCR:
            infer_result = ds.apply(doc_analyze, ocr=True)
            pipe_result = infer_result.pipe_ocr_mode(image_writer)
        else:
            infer_result = ds.apply(doc_analyze, ocr=False)
            pipe_result = infer_result.pipe_txt_mode(image_writer)
        
        # 获取markdown内容
        md_content = pipe_result.get_markdown(image_dir)
        
        # 保存结果
        md_file_path = f"{output_dir}/result.md"
        async with aiofiles.open(md_file_path, 'w') as f:
            await f.write(md_content)
        
        # 记录任务
        tasks[task_id] = TaskStatus(
            id=task_id,
            status="completed",
            filename=filename,
            created_at=time.time(),
            completed_at=time.time(),
            result_path=md_file_path
        )
        
        return {
            "task_id": task_id,
            "status": "completed",
            "message": "文件处理成功",
            "md_content": md_content
        }
    
    except Exception as e:
        # 记录失败状态
        if task_id in tasks:
            tasks[task_id].status = "failed"
            tasks[task_id].error_message = str(e)
        
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

async def process_file_async(task_id: str, filename: str, file_path: str):
    """
    异步处理文件的后台任务
    """
    try:
        if task_id not in tasks:
            return
            
        output_dir = f"output/{task_id}"
        local_image_dir, local_md_dir = f"{output_dir}/images", output_dir
        image_dir = "images"
        
        # 确保目录存在
        os.makedirs(local_image_dir, exist_ok=True)
        
        # 更新任务状态
        tasks[task_id].status = "processing"
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            tasks[task_id].status = "failed"
            tasks[task_id].error_message = "找不到上传的文件"
            return
            
        # 读取文件
        with open(file_path, 'rb') as f:
            pdf_bytes = f.read()
            
        if not pdf_bytes:
            tasks[task_id].status = "failed"
            tasks[task_id].error_message = "文件内容为空"
            return
        
        # 创建输出目录
        image_writer = FileBasedDataWriter(local_image_dir)
        md_writer = FileBasedDataWriter(local_md_dir)
        
        # 创建数据集实例
        ds = PymuDocDataset(pdf_bytes)
        
        # 推理
        if ds.classify() == SupportedPdfParseMethod.OCR:
            infer_result = ds.apply(doc_analyze, ocr=True)
            pipe_result = infer_result.pipe_ocr_mode(image_writer)
        else:
            infer_result = ds.apply(doc_analyze, ocr=False)
            pipe_result = infer_result.pipe_txt_mode(image_writer)
        
        # 获取markdown内容
        md_content = pipe_result.get_markdown(image_dir)
        
        # 保存结果
        md_file_path = f"{output_dir}/result.md"
        async with aiofiles.open(md_file_path, 'w') as f:
            await f.write(md_content)
        
        # 更新任务状态为已完成
        tasks[task_id].status = "completed"
        tasks[task_id].completed_at = time.time()
        tasks[task_id].result_path = md_file_path
        
    except Exception as e:
        # 更新任务状态为失败
        if task_id in tasks:
            tasks[task_id].status = "failed"
            tasks[task_id].error_message = str(e)

@app.post("/upload/async")
async def upload_async(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    异步上传文件，立即返回任务ID，后台处理文件
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
            created_at=time.time()
        )
        
        # 添加异步处理任务
        background_tasks.add_task(process_file_async, task_id, filename, temp_file_path)
        
        return {
            "task_id": task_id,
            "status": "pending",
            "message": "文件已接收，正在后台处理"
        }
    except Exception as e:
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
    
