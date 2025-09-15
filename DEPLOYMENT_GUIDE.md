# 生产环境部署指南

## 🚀 部署概述

本指南介绍如何在生产环境中安全地部署Twitter数据爬虫服务。

## 📋 API密钥配置方案

### 当前开发环境配置
- **位置**: `config/config.json`
- **状态**: 包含实际API密钥，不会被Git追踪
- **安全**: ✅ 被`.gitignore`排除

### 生产环境配置方案

#### 方案1：环境变量配置（推荐）

**优势：**
- ✅ 最安全，密钥不存储在文件中
- ✅ 支持容器化部署
- ✅ 支持CI/CD管道
- ✅ 符合12-factor应用原则

**步骤：**

1. **克隆仓库到生产服务器**
   ```bash
   git clone https://github.com/T1anDongWanX1ang/Carlwang.git
   cd Carlwang
   ```

2. **运行自动部署脚本**
   ```bash
   ./deploy.sh
   ```

3. **配置环境变量**
   ```bash
   # 复制环境变量模板
   cp .env.template .env
   
   # 编辑环境变量文件
   nano .env
   ```

   填入实际值：
   ```bash
   TWEETSCOUT_API_KEY=678dd1dd-d278-46e9-a6f1-a28dea950469
   OPENAI_API_KEY=sk-svcacct-pqEw9JjDzc0vul6fCMRjhaz...
   DB_HOST=34.46.218.219
   DB_NAME=public_data
   DB_USER=transaction
   DB_PASSWORD=trans_dskke33@72hxcys
   DB_PORT=9030
   ```

4. **验证配置**
   ```bash
   python3 env_config.py
   python3 main.py --mode test
   ```

5. **启动服务**
   ```bash
   ./start_service.sh start
   ```

#### 方案2：配置文件方式

**步骤：**
1. 在生产服务器上手动创建配置文件：
   ```bash
   cp config/config.json.template config/config.json
   nano config/config.json
   ```

2. 替换占位符为实际值

3. 设置文件权限：
   ```bash
   chmod 600 config/config.json
   chown $USER:$USER config/config.json
   ```

## 🐳 容器化部署

### Docker方式

**1. 创建Dockerfile**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chmod +x start_service.sh

EXPOSE 8080
CMD ["python", "main.py", "--mode", "schedule"]
```

**2. 构建和运行**
```bash
# 构建镜像
docker build -t twitter-crawler .

# 运行容器
docker run -d \
  --name twitter-crawler \
  -e TWEETSCOUT_API_KEY=your-key \
  -e OPENAI_API_KEY=your-key \
  -e DB_HOST=your-host \
  -e DB_PASSWORD=your-password \
  --restart unless-stopped \
  twitter-crawler
```

### Docker Compose

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  twitter-crawler:
    build: .
    environment:
      - TWEETSCOUT_API_KEY=${TWEETSCOUT_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DB_HOST=${DB_HOST}
      - DB_PASSWORD=${DB_PASSWORD}
    env_file:
      - .env
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
```

## ☁️ 云服务部署

### AWS EC2
```bash
# 在EC2实例上
sudo yum update -y
sudo yum install python3 git -y
git clone https://github.com/T1anDongWanX1ang/Carlwang.git
cd Carlwang
./deploy.sh
```

### 腾讯云CVM
```bash
# 在CVM实例上
sudo apt update
sudo apt install python3 python3-pip git -y
git clone https://github.com/T1anDongWanX1ang/Carlwang.git
cd Carlwang
./deploy.sh
```

## 🔐 安全最佳实践

1. **API密钥安全**
   - ✅ 使用环境变量存储
   - ✅ 定期轮换密钥
   - ✅ 设置API访问限制

2. **文件权限**
   ```bash
   chmod 600 .env config/config.json
   ```

3. **网络安全**
   - 配置防火墙规则
   - 使用HTTPS连接
   - 限制数据库访问IP

4. **监控和日志**
   - 定期检查service.log
   - 设置异常告警
   - 监控API使用量

## 🔧 生产环境管理

### 服务管理
```bash
# 启动服务
./start_service.sh start

# 查看状态
./start_service.sh status

# 查看日志
./start_service.sh logs

# 停止服务
./start_service.sh stop

# 重启服务
./start_service.sh restart
```

### systemd服务（推荐）
```bash
# 设置开机自启
sudo systemctl enable twitter-crawler

# 查看服务状态
sudo systemctl status twitter-crawler

# 查看服务日志
sudo journalctl -u twitter-crawler -f
```

### 监控和维护
```bash
# 监控脚本
./start_service.sh monitor

# 查看数据库状态
python3 main.py --mode test

# 手动执行一次
./start_service.sh once
```

## 🆘 故障排除

### 常见问题

1. **API连接失败**
   - 检查API密钥是否正确
   - 检查网络连接
   - 验证API额度

2. **数据库连接失败**
   - 检查数据库凭据
   - 验证网络连通性
   - 检查数据库服务状态

3. **服务启动失败**
   ```bash
   # 查看详细日志
   ./start_service.sh logs
   
   # 测试配置
   python3 main.py --mode test
   ```

### 日志分析
```bash
# 查看错误日志
grep "ERROR" service.log

# 查看最新日志
tail -f service.log

# 按时间过滤
grep "2024-01-01" service.log
```

## 📞 技术支持

如有部署问题，请：
1. 检查DEPLOYMENT_GUIDE.md
2. 查看service.log日志
3. 运行配置测试：`python3 main.py --mode test`