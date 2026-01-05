# Jumpserver 部署指南 - Carlos 分支

本指南详细说明如何在 jumpserver（云服务器）上部署 Carlwang 项目的 carlos 分支。

## 前置条件

- 已有 jumpserver 服务器访问权限
- 服务器上已安装 Python 3.8+ 和 Git
- 有 GitHub 访问权限（可能需要配置 SSH key 或 Personal Access Token）

---

## 第一部分：代码拉取（从 Main 切换到 Carlos 分支）

### 场景 1: 之前部署过 main 分支，现在切换到 carlos 分支

```bash
# 1. SSH 登录到 jumpserver
ssh your-username@your-jumpserver-host

# 2. 进入项目目录
cd /path/to/Carlwang

# 3. 停止所有正在运行的服务
# 停止主服务
if [ -f twitter-crawler.pid ]; then
    kill $(cat twitter-crawler.pid) 2>/dev/null
    rm twitter-crawler.pid
fi

# 停止 KOL following 服务
if [ -f daily_kol_following_crawler/kol_following.pid ]; then
    kill $(cat daily_kol_following_crawler/kol_following.pid) 2>/dev/null
fi

# 停止 KOL tweet 服务
if [ -f daily_kol_tweet_crawler/kol_tweet.pid ]; then
    kill $(cat daily_kol_tweet_crawler/kol_tweet.pid) 2>/dev/null
fi

# 或者使用 pkill（如果服务脚本在运行）
pkill -f "python.*main.py"
pkill -f "python.*fetch_kol_followings"

# 4. 备份当前的配置文件（非常重要！）
cp config/config.json config/config.json.backup_before_carlos
cp .env .env.backup_before_carlos 2>/dev/null  # 如果有 .env 文件

# 5. 查看当前状态
git status
git branch

# 6. 提交或暂存当前修改（如果有的话）
# 如果有未提交的修改，建议先暂存
git stash save "备份 main 分支修改 $(date +%Y%m%d_%H%M%S)"

# 7. 获取最新的远程分支信息
git fetch origin

# 8. 切换到 carlos 分支
git checkout carlos

# 9. 拉取 carlos 分支最新代码
git pull origin carlos
```

### 场景 2: 首次部署（全新安装）

```bash
# 1. SSH 登录到 jumpserver
ssh your-username@your-jumpserver-host

# 2. 选择部署目录并克隆代码
cd /opt  # 或其他合适的目录
git clone -b carlos https://github.com/T1anDongWanX1ang/Carlwang.git
cd Carlwang

# 3. 验证分支
git branch
# 应该显示 * carlos
```

---

## 第二部分：环境配置

### 1. 创建 Python 虚拟环境

```bash
# 在项目根目录下
cd /path/to/Carlwang

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 验证虚拟环境
which python  # 应该显示 /path/to/Carlwang/venv/bin/python
```

### 2. 安装 Python 依赖

```bash
# 确保虚拟环境已激活
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

# 验证安装
pip list
```

### 3. 配置文件设置

#### 方法 A: 从本地复制配置文件（推荐）

**在本地 Mac 上操作：**

```bash
# 在本地 Mac 的项目目录下
cd /Users/qmk/Documents/QC/twitter/Carlwang

# 使用 scp 上传配置文件到 jumpserver
scp config/config.json your-username@jumpserver-host:/path/to/Carlwang/config/

# 或者如果有多个配置文件需要同步
scp config/config.json \
    config/config_new.json \
    your-username@jumpserver-host:/path/to/Carlwang/config/
```

**在 jumpserver 上操作：**

```bash
# 验证文件已上传
ls -lh config/config.json

# 如果上传了 config_new.json，重命名为 config.json
mv config/config_new.json config/config.json
```

#### 方法 B: 在服务器上手动创建配置文件

```bash
# 在 jumpserver 上
cd /path/to/Carlwang

# 复制模板文件
cp config/config.template.json config/config.json

# 编辑配置文件
vim config/config.json
# 或使用 nano
nano config/config.json
```

**需要修改的关键配置项：**

```json
{
  "api": {
    "headers": {
      "X-API-Key": "your_actual_tweetscout_api_key",
      "ApiKey": "your_actual_tweetscout_api_key"
    },
    "default_params": {
      "list_ids_kol": ["your_kol_list_id"],
      "list_ids_project": ["your_project_list_id"]
    }
  },
  "api_twitterapi": {
    "headers": {
      "X-API-Key": "your_twitterapi_io_key"
    }
  },
  "chatgpt": {
    "api_key": "your_gemini_or_openai_api_key",
    "base_url": "your_api_base_url",
    "model": "your_model_name"
  },
  "database": {
    "host": "35.215.99.34",
    "port": 13216,
    "database": "public_data",
    "username": "tele",
    "password": "your_database_password"
  },
  "cost_db": {
    "host": "35.215.99.34",
    "port": 13215,
    "username": "alarm_user",
    "password": "your_cost_db_password",
    "database": "tp_alarm"
  }
}
```

### 4. 环境变量配置（可选但推荐）

对于敏感信息，可以使用环境变量代替写入配置文件：

```bash
# 创建 .env 文件（该文件在 .gitignore 中）
cat > .env << 'EOF'
# API Keys
TWEETSCOUT_API_KEY=your_tweetscout_api_key
TWITTERAPI_IO_KEY=your_twitterapi_io_key
GEMINI_API_KEY=your_gemini_api_key

# Database
DB_HOST=35.215.99.34
DB_PORT=13216
DB_NAME=public_data
DB_USER=tele
DB_PASSWORD=your_database_password

# Cost Database
COST_DB_HOST=35.215.99.34
COST_DB_PORT=13215
COST_DB_USER=alarm_user
COST_DB_PASSWORD=your_cost_db_password
COST_DB_NAME=tp_alarm
EOF

# 设置权限（确保只有当前用户可读）
chmod 600 .env

# 加载环境变量（每次运行前需要执行）
source .env
```

### 5. 创建必要的目录

```bash
# 创建日志目录
mkdir -p logs

# 创建缓存目录
mkdir -p .kol_cache
mkdir -p .kol_cache_new

# 设置权限
chmod 755 logs .kol_cache .kol_cache_new
```

---

## 第三部分：服务启动

### 1. 测试配置

在启动服务之前，先测试配置是否正确：

```bash
# 激活虚拟环境
source venv/bin/activate

# 测试数据库连接
python main.py --mode test

# 如果看到连接成功的消息，说明配置正确
```

### 2. 单次运行测试

```bash
# KOL Following 单次抓取测试
cd daily_kol_following_crawler
python fetch_kol_followings_new.py --test
cd ..

# KOL Tweet 单次抓取测试
python main.py --mode once

# Project Tweet 单次抓取测试
python src/crawler.py
```

### 3. 启动定时服务

#### 3.1 KOL Following 爬虫服务

```bash
cd daily_kol_following_crawler
./start_service_kol_following.sh start

# 检查状态
./start_service_kol_following.sh status

# 查看日志
./start_service_kol_following.sh logs
```

#### 3.2 KOL Tweet 爬虫服务

```bash
cd daily_kol_tweet_crawler
./start_service_kol_tweet.sh start

# 检查状态
./start_service_kol_tweet.sh status

# 查看日志
./start_service_kol_tweet.sh logs
```

#### 3.3 Project Tweet 爬虫服务

```bash
cd daily_tweet_crawler
./start_service_project_twitterapi.sh start

# 检查状态
./start_service_project_twitterapi.sh status

# 查看日志
./start_service_project_twitterapi.sh logs
```

### 4. 使用 Crontab 定时任务（推荐用于生产环境）

```bash
# 编辑 crontab
crontab -e

# 添加以下定时任务（示例）
# 每5分钟运行 KOL Following 爬虫
*/5 * * * * cd /path/to/Carlwang/daily_kol_following_crawler && ./start_service_kol_following.sh monitor >> /path/to/Carlwang/logs/cron_kol_following.log 2>&1

# 每5分钟运行 KOL Tweet 爬虫
*/5 * * * * cd /path/to/Carlwang/daily_kol_tweet_crawler && ./start_service_kol_tweet.sh monitor >> /path/to/Carlwang/logs/cron_kol_tweet.log 2>&1

# 每天凌晨1点运行成本报告
0 1 * * * cd /path/to/Carlwang && /path/to/Carlwang/venv/bin/python -c "from daily_kol_following_crawler.monitor_daily_cost import generate_report; generate_report()" >> /path/to/Carlwang/logs/daily_report.log 2>&1

# 保存退出（vim: :wq 或 nano: Ctrl+X, Y, Enter）
```

---

## 第四部分：验证部署

### 1. 检查服务运行状态

```bash
# 查看所有相关进程
ps aux | grep python | grep -E 'main.py|fetch_kol'

# 查看 PID 文件
ls -lh *.pid
ls -lh daily_*/*.pid

# 检查日志文件
tail -f logs/twitter_crawler.log
tail -f daily_kol_following_crawler/service.log
tail -f daily_kol_tweet_crawler/service.log
```

### 2. 监控成本数据入库

```bash
# 查看 KOL Following 成本
cd daily_kol_following_crawler
./monitor_daily_cost.sh

# 查看 KOL Tweet 成本
cd ../daily_kol_tweet_crawler
./monitor_daily_cost.sh

# 查看 Project Tweet 成本
cd ../daily_tweet_crawler
./monitor_daily_cost.sh
```

### 3. 检查数据库是否有新数据

```bash
# 使用 Python 快速查询
python3 << 'EOF'
import pymysql
from datetime import datetime

conn = pymysql.connect(
    host='35.215.99.34',
    port=13216,
    user='tele',
    password='your_password',
    database='public_data'
)
cursor = conn.cursor()

# 检查最新的 tweet
cursor.execute("SELECT COUNT(*), MAX(created_at) FROM twitter_tweet WHERE created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)")
result = cursor.fetchone()
print(f"最近1小时新增推文: {result[0]}条")
print(f"最新推文时间: {result[1]}")

# 检查成本数据
conn2 = pymysql.connect(
    host='35.215.99.34',
    port=13215,
    user='alarm_user',
    password='your_cost_password',
    database='tp_alarm'
)
cursor2 = conn2.cursor()
cursor2.execute("SELECT * FROM api_cost_tracking ORDER BY created_at DESC LIMIT 5")
print("\n最近5条成本记录:")
for row in cursor2.fetchall():
    print(row)

cursor.close()
conn.close()
cursor2.close()
conn2.close()
EOF
```

---

## 第五部分：常见问题排查

### 问题 1: 虚拟环境找不到

```bash
# 症状：ImportError: No module named 'requests'
# 解决：确保使用虚拟环境的 Python

# 检查当前 Python
which python

# 应该显示类似：/path/to/Carlwang/venv/bin/python
# 如果不是，重新激活虚拟环境
source venv/bin/activate
```

### 问题 2: 权限错误

```bash
# 症状：Permission denied
# 解决：给脚本添加执行权限

chmod +x daily_kol_following_crawler/start_service_kol_following.sh
chmod +x daily_kol_tweet_crawler/start_service_kol_tweet.sh
chmod +x daily_tweet_crawler/start_service_project_twitterapi.sh
chmod +x daily_kol_following_crawler/monitor_daily_cost.sh
chmod +x daily_kol_tweet_crawler/monitor_daily_cost.sh
chmod +x daily_tweet_crawler/monitor_daily_cost.sh
```

### 问题 3: 配置文件找不到

```bash
# 症状：FileNotFoundError: config/config.json
# 解决：确认配置文件存在

ls -lh config/config.json

# 如果不存在，从模板创建
cp config/config.template.json config/config.json
# 然后编辑配置
```

### 问题 4: 数据库连接失败

```bash
# 症状：Can't connect to MySQL server
# 解决方法：

# 1. 检查网络连接
ping 35.215.99.34

# 2. 检查端口是否可达
telnet 35.215.99.34 13216
# 或
nc -zv 35.215.99.34 13216

# 3. 检查防火墙规则（如果在云服务器上）
# 确保 jumpserver 的出站规则允许访问 35.215.99.34:13216

# 4. 验证数据库凭证
mysql -h 35.215.99.34 -P 13216 -u tele -p
# 输入密码后应该能连接
```

### 问题 5: API 调用失败

```bash
# 症状：API request failed with status 401/403
# 解决：检查 API key 是否正确

# 验证 TweetScout API key
curl -H "X-API-Key: your_api_key" \
     "https://api.tweetscout.io/v2/list-tweets?list_id=test"

# 如果返回 401，说明 API key 无效，需要更新 config.json
```

---

## 第六部分：服务管理命令速查表

| 操作 | 命令 |
|------|------|
| 启动 KOL Following | `cd daily_kol_following_crawler && ./start_service_kol_following.sh start` |
| 停止 KOL Following | `cd daily_kol_following_crawler && ./start_service_kol_following.sh stop` |
| 查看 KOL Following 状态 | `cd daily_kol_following_crawler && ./start_service_kol_following.sh status` |
| 查看 KOL Following 日志 | `cd daily_kol_following_crawler && ./start_service_kol_following.sh logs` |
| 启动 KOL Tweet | `cd daily_kol_tweet_crawler && ./start_service_kol_tweet.sh start` |
| 停止 KOL Tweet | `cd daily_kol_tweet_crawler && ./start_service_kol_tweet.sh stop` |
| 查看成本统计 | `cd daily_kol_following_crawler && ./monitor_daily_cost.sh` |
| 手动执行一次爬取 | `source venv/bin/activate && python main.py --mode once` |
| 查看所有运行的服务 | `ps aux \| grep python \| grep -E 'main.py\|fetch_kol'` |
| 停止所有服务 | `pkill -f "python.*main.py"; pkill -f "fetch_kol_followings"` |

---

## 第七部分：重要注意事项

### 1. 配置文件安全

- **永远不要**将 `config/config.json` 提交到 Git
- 使用 `config.template.json` 作为模板参考
- 敏感信息优先使用环境变量

### 2. 日志管理

```bash
# 定期清理旧日志（避免磁盘占满）
find logs/ -name "*.log" -mtime +30 -delete

# 或设置 logrotate
cat > /etc/logrotate.d/carlwang << 'EOF'
/path/to/Carlwang/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

### 3. 监控和告警

建议设置以下监控：
- 服务进程是否存活
- API 调用成本是否超出预算
- 数据库连接是否正常
- 磁盘空间是否充足

### 4. 定期备份

```bash
# 创建备份脚本
cat > /path/to/Carlwang/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/carlwang/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# 备份配置
cp -r config/ "$BACKUP_DIR/"

# 备份缓存
cp -r .kol_cache_new/ "$BACKUP_DIR/"

# 备份日志（最近7天）
find logs/ -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/" \;

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x /path/to/Carlwang/backup.sh

# 添加到 crontab（每天凌晨2点备份）
0 2 * * * /path/to/Carlwang/backup.sh
```

---

## 快速部署命令总结

如果你已经熟悉流程，可以使用以下一键部署脚本：

```bash
#!/bin/bash
# 快速部署脚本 - quick_deploy.sh

set -e  # 遇到错误立即退出

echo "=== Carlwang Carlos 分支快速部署 ==="

# 1. 停止现有服务
echo "[1/7] 停止现有服务..."
pkill -f "python.*main.py" 2>/dev/null || true
pkill -f "fetch_kol_followings" 2>/dev/null || true

# 2. 拉取最新代码
echo "[2/7] 拉取 carlos 分支最新代码..."
git checkout carlos
git pull origin carlos

# 3. 创建虚拟环境
echo "[3/7] 设置 Python 虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 4. 安装依赖
echo "[4/7] 安装 Python 依赖..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 5. 创建必要目录
echo "[5/7] 创建目录..."
mkdir -p logs .kol_cache .kol_cache_new

# 6. 配置文件检查
echo "[6/7] 检查配置文件..."
if [ ! -f "config/config.json" ]; then
    echo "错误: config/config.json 不存在!"
    echo "请从本地上传或从模板创建"
    exit 1
fi

# 7. 启动服务
echo "[7/7] 启动服务..."
cd daily_kol_following_crawler && ./start_service_kol_following.sh start
cd ../daily_kol_tweet_crawler && ./start_service_kol_tweet.sh start

echo "=== 部署完成! ==="
echo "使用以下命令查看服务状态:"
echo "  ps aux | grep python | grep -E 'main.py|fetch_kol'"
```

保存为 `quick_deploy.sh`，然后：
```bash
chmod +x quick_deploy.sh
./quick_deploy.sh
```

---

## 联系与支持

如遇问题，请检查：
1. `logs/twitter_crawler.log` - 主程序日志
2. `daily_kol_following_crawler/service.log` - KOL Following 服务日志
3. `daily_kol_tweet_crawler/service.log` - KOL Tweet 服务日志

祝部署顺利！
