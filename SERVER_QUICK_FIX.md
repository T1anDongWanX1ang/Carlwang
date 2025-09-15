# 服务器快速修复指南

## 🚨 常见问题快速解决

### 问题1：配置文件不存在

**错误信息：**
```
FileNotFoundError: 配置文件不存在: /path/to/config/config.json
```

**快速解决：**
```bash
# 方案1：使用初始化脚本
./init_config.sh

# 方案2：手动创建
cp config/config.json.template config/config.json

# 方案3：使用交互式配置
python3 setup_config.py
```

**配置API密钥：**
```bash
# 编辑配置文件
nano config/config.json

# 替换以下占位符：
# YOUR_TWEETSCOUT_API_KEY → 您的实际TweetScout API密钥
# YOUR_OPENAI_API_KEY → 您的实际OpenAI API密钥
# YOUR_DATABASE_HOST → 您的实际数据库主机地址
# YOUR_DATABASE_PASSWORD → 您的实际数据库密码
```

### 问题2：OpenSSL兼容性（CentOS 7）

**错误信息：**
```
ImportError: urllib3 v2 only supports OpenSSL 1.1.1+
```

**快速解决：**
```bash
# 自动修复（推荐）
./fix_centos7.sh

# 手动修复
pip install "urllib3>=1.26.12,<2.0.0"
pip install "requests>=2.28.0,<2.32.0"
```

## 🔧 完整修复流程

**在您的服务器上执行以下命令：**

```bash
# 1. 更新代码
cd /home/centos/Project/Carlwang
git pull

# 2. 修复依赖问题（CentOS 7）
./fix_centos7.sh

# 3. 创建配置文件
./init_config.sh

# 4. 配置API密钥
nano config/config.json
# 填入实际的API密钥和数据库配置

# 5. 测试配置
python3 main.py --mode test

# 6. 运行服务
./start_service.sh once
```

## 📋 配置模板

**config/config.json 完整配置示例：**

```json
{
  "api": {
    "base_url": "https://api.tweetscout.io/v2",
    "endpoints": {
      "list_tweets": "/list-tweets"
    },
    "headers": {
      "Accept": "application/json",
      "ApiKey": "YOUR_TWEETSCOUT_API_KEY"
    },
    "default_params": {
      "list_id": "1896516371435122886"
    },
    "pagination": {
      "page_size": 100,
      "max_pages": 10
    },
    "timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 5
  },
  "chatgpt": {
    "api_key": "YOUR_OPENAI_API_KEY",
    "model": "gpt-3.5-turbo",
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 2,
    "batch_size": 10,
    "enable_topic_analysis": true,
    "enable_sentiment_analysis": true,
    "enable_kol_analysis": true,
    "enable_project_analysis": true
  },
  "database": {
    "type": "mysql",
    "host": "YOUR_DATABASE_HOST",
    "port": 9030,
    "database": "YOUR_DATABASE_NAME",
    "username": "YOUR_DATABASE_USERNAME",
    "password": "YOUR_DATABASE_PASSWORD",
    "tables": {
      "tweet": "twitter_tweet",
      "user": "twitter_user",
      "topic": "topics",
      "kol": "kols",
      "project": "twitter_projects"
    },
    "connection_pool": {
      "max_connections": 10,
      "min_connections": 1,
      "connection_timeout": 30,
      "idle_timeout": 600
    },
    "options": {
      "useUnicode": true,
      "characterEncoding": "utf8",
      "serverTimezone": "GMT",
      "useSSL": false,
      "allowPublicKeyRetrieval": true
    }
  }
}
```

## ✅ 验证修复

**成功标志：**

1. **配置测试通过：**
   ```bash
   python3 main.py --mode test
   # 输出：✅ 数据库连接: ✓ 成功
   #      ✅ API连接: ✓ 成功
   ```

2. **服务正常启动：**
   ```bash
   ./start_service.sh once
   # 应该开始爬取数据，无报错
   ```

## 🆘 仍有问题？

**诊断步骤：**

1. **检查Python版本：**
   ```bash
   python3 --version  # 应该 >= 3.7
   ```

2. **检查配置文件：**
   ```bash
   ls -la config/
   cat config/config.json | head -20
   ```

3. **检查依赖版本：**
   ```bash
   pip list | grep -E "(urllib3|requests|openai)"
   ```

4. **查看详细错误：**
   ```bash
   python3 -c "from src.crawler import crawler"
   ```

**联系技术支持时请提供：**
- 系统版本：`cat /etc/redhat-release`
- Python版本：`python3 --version`
- 错误完整堆栈信息