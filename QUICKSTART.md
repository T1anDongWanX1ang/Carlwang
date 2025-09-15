# 快速开始指南

## 1. 环境准备

确保系统已安装Python 3.7+：

```bash
python3 --version
```

## 2. 安装和配置

### 克隆或下载项目后，进入项目目录：

```bash
cd twitter-crawler
```

### 使用便捷脚本（推荐）：

```bash
# 测试连接
./run.sh test

# 单次执行
./run.sh once

# 定时调度
./run.sh schedule
```

### 或手动操作：

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 3. 配置API密钥

编辑 `config/config.json` 文件，更新您的API密钥：

```json
{
  "api": {
    "headers": {
      "ApiKey": "your-actual-api-key-here"
    },
    "default_params": {
      "list_id": "your-twitter-list-id"
    }
  }
}
```

## 4. 配置数据库

更新数据库连接信息：

```json
{
  "database": {
    "host": "your-database-host",
    "port": 9030,
    "username": "your-username",
    "password": "your-password",
    "database": "your-database-name"
  }
}
```

## 5. 运行测试

```bash
python main.py --mode test
```

如果看到"所有连接测试通过"，说明配置正确。

## 6. 开始使用

### 单次执行：
```bash
python main.py --mode once
```

### 定时调度（每5分钟）：
```bash
python main.py --mode schedule
```

### 自定义参数：
```bash
# 指定列表ID和分页参数
python main.py --mode once --list-id 1896516371435122886 --max-pages 3 --page-size 50

# 指定调度间隔为10分钟
python main.py --mode schedule --interval 10
```

## 7. 监控日志

日志文件位置：`logs/twitter_crawler.log`

实时查看日志：
```bash
tail -f logs/twitter_crawler.log
```

## 常见问题

### Q: API返回403错误怎么办？
A: 检查API密钥是否正确，以及是否超出了调用限制。

### Q: 数据库连接失败怎么办？
A: 检查数据库配置信息，确保网络连通性和账号权限。

### Q: 如何停止定时调度？
A: 按 `Ctrl+C` 即可优雅停止程序。

### Q: 如何修改抓取间隔？
A: 编辑配置文件中的 `scheduler.interval_minutes` 或使用 `--interval` 参数。

### Q: 数据重复怎么办？
A: 程序使用UPSERT操作，相同ID的推文会自动更新而不会重复插入。

## 下一步

1. 根据实际需求调整配置参数
2. 设置生产环境的进程管理（如systemd）
3. 配置监控和告警
4. 定期备份数据库
5. 根据API限制调整抓取频率 