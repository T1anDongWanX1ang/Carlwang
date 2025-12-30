# Twitter数据爬取服务管理

本目录提供了两个脚本来管理Twitter数据爬取服务：

## 🚀 快速启动

### 方式1：使用Bash脚本（推荐新手）

```bash
# 启动服务（默认5分钟间隔）
./start_service.sh start

# 查看服务状态
./start_service.sh status

# 查看日志
./start_service.sh logs

# 停止服务
./start_service.sh stop
```

### 方式2：使用Python脚本（推荐高级用户）

```bash
# 安装依赖
pip install psutil

# 启动服务
python3 service_manager.py start

# 查看详细状态
python3 service_manager.py status

# 实时监控服务
python3 service_manager.py monitor

# 停止服务
python3 service_manager.py stop
```

## 📋 详细使用说明

### Bash脚本 (start_service.sh)

```bash
# 基本命令
./start_service.sh start                    # 默认配置启动
./start_service.sh start 10                 # 10分钟间隔
./start_service.sh start 5 5 50             # 5分钟间隔，5页，每页50条
./start_service.sh stop                     # 停止服务
./start_service.sh restart                  # 重启服务
./start_service.sh status                   # 查看状态
./start_service.sh logs 100                 # 查看最新100行日志
./start_service.sh help                     # 显示帮助
```

### Python脚本 (service_manager.py)

```bash
# 服务管理
python3 service_manager.py start --interval 10 --max-pages 3 --page-size 100
python3 service_manager.py stop
python3 service_manager.py restart
python3 service_manager.py status

# 日志和监控
python3 service_manager.py logs --lines 100
python3 service_manager.py monitor          # 实时监控（Ctrl+C退出）

# 配置管理
python3 service_manager.py config           # 查看配置
```

## ⚙️ 配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| interval | 爬取间隔（分钟） | 5 |
| max-pages | 每次最大页数 | 3 |
| page-size | 每页推文数 | 100 |

## 📁 生成的文件

- `twitter-crawler.pid` - 进程ID文件
- `service.log` - 服务运行日志
- `service_config.json` - Python脚本配置文件（自动生成）

## 🔧 高级功能（Python脚本特有）

### 实时监控
```bash
python3 service_manager.py monitor
```
- 显示实时状态、内存、CPU使用情况
- 自动重启功能（如果启用）
- 资源使用警告

### 自动配置
Python脚本会自动创建配置文件 `service_config.json`：

```json
{
  "interval": 5,
  "max_pages": 3,
  "page_size": 100,
  "auto_restart": true,
  "max_memory_mb": 500,
  "max_cpu_percent": 80
}
```

## 🛠️ 故障排除

### 服务启动失败
1. 检查Python环境：`python3 --version`
2. 检查依赖：`pip install -r requirements.txt`
3. 检查权限：`chmod +x start_service.sh service_manager.py`

### 日志查看
```bash
# 实时查看日志
tail -f service.log

# 查看错误日志
grep -i error service.log

# 查看最新状态
./start_service.sh status
```

### 清理残留进程
```bash
# 手动清理所有爬虫进程
pkill -f "python.*main.py.*schedule"
rm -f twitter-crawler.pid
```

## 📊 推荐配置

### 开发环境
```bash
./start_service.sh start 10 2 50  # 10分钟间隔，轻量配置
```

### 生产环境
```bash
./start_service.sh start 5 5 100  # 5分钟间隔，高效配置
```

### 测试环境
```bash
./start_service.sh start 1 1 10   # 1分钟间隔，快速测试
```