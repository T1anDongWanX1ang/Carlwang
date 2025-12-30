# 项目设置指南

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/T1anDongWanX1ang/Carlwang.git
cd Carlwang
```

### 2. 安装依赖
```bash
# 创建虚拟环境 (推荐)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置设置 ⚠️ **必须步骤**

项目为了安全考虑，不包含实际的API密钥和数据库凭据。您需要配置自己的凭据：

#### 方法一：使用配置脚本（推荐）
```bash
python setup_config.py
```

按照提示输入：
- TweetScout API Key
- OpenAI API Key (sk-...)
- 数据库连接信息

#### 方法二：手动编辑配置文件
1. 复制配置模板：
   ```bash
   cp config/config.json.template config/config.json
   ```

2. 编辑 `config/config.json`，替换以下占位符：
   - `YOUR_TWEETSCOUT_API_KEY` → 您的TweetScout API密钥
   - `YOUR_OPENAI_API_KEY` → 您的OpenAI API密钥（sk-开头）
   - `YOUR_DATABASE_HOST` → 数据库主机地址
   - `YOUR_DATABASE_NAME` → 数据库名称
   - `YOUR_DATABASE_USERNAME` → 数据库用户名
   - `YOUR_DATABASE_PASSWORD` → 数据库密码

### 4. 测试配置
```bash
python main.py --mode test
```

如果显示 "✅ 数据库连接测试成功" 和 "✅ API连接测试成功"，说明配置正确。

### 5. 开始使用
```bash
# 单次爬取
python main.py --mode once

# 定时爬取（推荐用于生产环境）
./start_service.sh start
```

## 🔧 服务管理

### 启动/停止服务
```bash
# 启动服务
./start_service.sh start

# 停止服务
./start_service.sh stop

# 重启服务
./start_service.sh restart

# 查看状态
./start_service.sh status

# 查看日志
./start_service.sh logs
```

## 📋 获取API密钥

### TweetScout API
1. 访问 [TweetScout官网](https://tweetscout.io/)
2. 注册账号并获取API密钥
3. 将密钥填入配置文件

### OpenAI API
1. 访问 [OpenAI官网](https://platform.openai.com/)
2. 创建账号并获取API密钥
3. 密钥格式：`sk-...`

### 数据库配置
项目支持MySQL/Doris数据库，需要提供：
- 主机地址和端口
- 数据库名称
- 用户名和密码

## ⚠️ 安全提醒

- **不要**将包含真实API密钥的配置文件提交到Git
- `config/config.json` 已被添加到 `.gitignore`
- 如需分享配置，请使用 `config.json.template`

## 🆘 常见问题

### Q: 为什么运行时提示"配置文件错误"？
A: 请确保已正确设置配置文件，运行 `python setup_config.py` 重新配置。

### Q: 数据库连接失败？
A: 检查数据库凭据是否正确，网络连接是否正常。

### Q: API调用失败？
A: 检查API密钥是否有效，是否有足够的调用额度。

### Q: 如何重置配置？
A: 运行 `python setup_config.py reset`

## 📞 获取帮助

如有问题，请：
1. 检查日志文件：`logs/twitter_crawler.log`
2. 运行测试命令：`python main.py --mode test`
3. 查看项目文档：`README.md`