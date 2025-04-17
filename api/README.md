# MinerU API 服务

本项目是MinerU的API服务，提供PDF文档解析和文本挖掘功能的HTTP接口。

## 功能特性

- **同步上传解析**：上传文件并等待解析完成
- **异步上传解析**：快速上传文件，后台处理
- **任务管理**：查询解析任务状态
- **结果下载**：下载解析后的Markdown文件
- **批量导出**：下载包含图片的完整解析结果

## 部署指南

### 前提条件

- Docker 和 Docker Compose
- Git
- 如需GPU加速，要求安装了nvidia-docker

### 在服务器上部署

1. **克隆项目**

```bash
git clone https://github.com/opendatalab/MinerU.git
cd MinerU
```

2. **构建和启动API服务**

```bash
cd api
docker-compose up -d
```

对于GPU服务器，请修改`docker-compose.yml`文件，取消GPU相关配置的注释，然后再启动服务。

3. **验证服务是否正常运行**

```bash
curl http://localhost:8000/tasks
```

正常情况下，应该返回一个空的任务列表。

### 配置HTTPS（推荐）

如果需要在公网环境下使用，强烈建议配置HTTPS。您可以使用Nginx作为反向代理，并配置SSL证书：

```bash
# 安装Nginx
apt-get update
apt-get install -y nginx certbot python3-certbot-nginx

# 配置Nginx
cat > /etc/nginx/sites-available/mineru-api <<EOF
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# 启用配置
ln -s /etc/nginx/sites-available/mineru-api /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# 配置SSL证书
certbot --nginx -d your-domain.com
```

## API接口文档

启动服务后，访问 `http://your-domain-or-ip:8000/docs` 获取完整的API文档。

### 主要接口

- `POST /upload/sync` - 同步上传并解析文件
- `POST /upload/async` - 异步上传文件进行解析
- `GET /tasks` - 获取所有任务列表
- `GET /tasks/{task_id}` - 获取特定任务状态
- `GET /download/{task_id}` - 下载解析结果
- `GET /download/{task_id}/zip` - 下载完整结果（包含图片）
- `DELETE /tasks/{task_id}` - 删除任务及资源

## 使用示例

### 上传文件 (同步)

```bash
curl -X POST "http://your-domain-or-ip:8000/upload/sync" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-document.pdf"
```

### 上传文件 (异步)

```bash
curl -X POST "http://your-domain-or-ip:8000/upload/async" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-document.pdf"
```

### 查询状态

```bash
curl -X GET "http://your-domain-or-ip:8000/tasks/YOUR-TASK-ID" \
  -H "accept: application/json"
```

### 下载结果

```bash
curl -X GET "http://your-domain-or-ip:8000/download/YOUR-TASK-ID" \
  -o result.md
```

## 维护指南

### 查看容器日志

```bash
docker-compose logs -f mineru-api
```

### 更新服务

```bash
# 拉取最新代码
git pull

# 重新构建并启动服务
docker-compose down
docker-compose up --build -d
```

### 数据备份

所有解析结果存储在Docker卷`mineru_data`中，可以使用以下命令进行备份：

```bash
docker run --rm -v mineru_data:/data -v $(pwd):/backup ubuntu tar czf /backup/mineru_data_backup.tar.gz /data
```

## 常见问题解决

1. **服务无法启动**
   - 检查Docker日志: `docker-compose logs mineru-api`
   - 确认端口8000未被占用: `netstat -tuln | grep 8000`

2. **解析失败**
   - 检查上传的PDF文件格式是否正确
   - 查看容器日志寻找错误信息

3. **性能问题**
   - 如果有GPU，确保正确配置了GPU支持
   - 对于大文件处理，建议使用异步API 