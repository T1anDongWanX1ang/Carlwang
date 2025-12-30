# 远程服务器OpenAI库升级指南

## 问题描述

服务器报错：`module 'openai' has no attribute 'OpenAI'`

**根本原因：** OpenAI库版本过旧（0.28.x），不支持新的 `openai.OpenAI` 类

## 解决方案

### 步骤1：连接到远程服务器

```bash
ssh your-server
cd /path/to/twitter-crawler
```

### 步骤2：检查当前OpenAI版本

```bash
# 激活虚拟环境
source venv/bin/activate

# 检查版本
pip show openai
# 或
python -c "import openai; print(openai.__version__)"
```

**预期看到：** openai 0.28.x ❌

### 步骤3：升级OpenAI库

```bash
# 确保在虚拟环境中
source venv/bin/activate

# 升级到2.0以上版本
pip install --upgrade "openai>=2.0.0"
```

**升级过程：**
```
Collecting openai>=2.0.0
  Downloading openai-2.7.1-py3-none-any.whl (1.0 MB)
Installing collected packages: openai
  Attempting uninstall: openai
    Found existing installation: openai 0.28.1
    Uninstalling openai-0.28.1:
      Successfully uninstalled openai-0.28.1
Successfully installed openai-2.7.1 ...
```

### 步骤4：验证升级

```bash
python << 'EOF'
import openai
print(f"✅ OpenAI 版本: {openai.__version__}")
print(f"✅ 支持 OpenAI 类: {hasattr(openai, 'OpenAI')}")
print(f"✅ 支持 RateLimitError: {hasattr(openai, 'RateLimitError')}")
EOF
```

**预期输出：**
```
✅ OpenAI 版本: 2.7.1
✅ 支持 OpenAI 类: True
✅ 支持 RateLimitError: True
```

### 步骤5：重启服务

```bash
# 停止服务
./start_service.sh stop

# 等待3秒
sleep 3

# 重新启动服务（使用优化后的配置）
./start_service.sh start 30 5 20

# 检查服务状态
./start_service.sh status
```

### 步骤6：验证服务正常

```bash
# 查看最新日志
tail -100 service.log | grep -E "(ChatGPT请求成功|速率限制|RateLimitError)"

# 应该看到成功的日志，而不是速率限制错误
# ✅ ChatGPT请求成功，生成内容长度: XXX
```

## 一键修复脚本

如果需要快速修复，可以在服务器上创建并运行此脚本：

```bash
#!/bin/bash
# fix_openai_server.sh

echo "=== OpenAI库升级脚本 ==="
cd /path/to/twitter-crawler

echo "1. 激活虚拟环境..."
source venv/bin/activate

echo "2. 检查当前版本..."
python -c "import openai; print(f'当前版本: {openai.__version__}')"

echo "3. 升级OpenAI库..."
pip install --upgrade "openai>=2.0.0"

echo "4. 验证升级..."
python << 'EOF'
import openai
print(f"✅ OpenAI 版本: {openai.__version__}")
print(f"✅ 支持 OpenAI 类: {hasattr(openai, 'OpenAI')}")
print(f"✅ 支持 RateLimitError: {hasattr(openai, 'RateLimitError')}")
EOF

echo "5. 重启服务..."
./start_service.sh restart 30 5 20

echo "✅ 修复完成！"
echo "使用以下命令检查日志："
echo "  tail -f service.log"
```

**使用方法：**
```bash
# 上传脚本
scp fix_openai_server.sh your-server:/path/to/twitter-crawler/

# SSH到服务器执行
ssh your-server
cd /path/to/twitter-crawler
chmod +x fix_openai_server.sh
./fix_openai_server.sh
```

## 注意事项

### 1. Python版本要求
OpenAI 2.x 要求 Python >= 3.7.1

```bash
python --version  # 确保 >= 3.7.1
```

### 2. 依赖库
升级会同时安装新的依赖：
- httpx
- pydantic >= 2.0
- anyio
- distro

### 3. 配置文件
确保 `config/config.json` 中的 API key 是有效的：
- ✅ `sk-proj-...` (Project Key, 配额高)
- ⚠️ `sk-svcacct-...` (Service Account, 配额低)

### 4. 环境变量（可选）
如果服务器使用环境变量：
```bash
export OPENAI_API_KEY="sk-proj-..."
```

但**注意：当前代码不读取环境变量**，直接从 `config.json` 读取。

## 故障排查

### 问题1：pip命令不存在
```bash
# 使用python -m pip
python -m pip install --upgrade "openai>=2.0.0"
```

### 问题2：权限不足
```bash
# 使用--user参数
pip install --user --upgrade "openai>=2.0.0"
```

### 问题3：网络问题
```bash
# 使用国内镜像
pip install --upgrade "openai>=2.0.0" -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题4：虚拟环境未激活
```bash
# 确保看到(venv)提示符
which python  # 应该指向 venv/bin/python
```

### 问题5：升级后仍报错
```bash
# 清理缓存重新安装
pip uninstall openai -y
pip cache purge
pip install "openai>=2.0.0"
```

## 验证修复成功的标志

✅ **日志中应该看到：**
```
2025-11-06 XX:XX:XX - src.api.chatgpt_client - DEBUG - 发起ChatGPT请求 (尝试 1/3)
2025-11-06 XX:XX:XX - src.api.chatgpt_client - DEBUG - ChatGPT请求成功，生成内容长度: XXX
```

✅ **不应该再看到：**
```
❌ RateLimitError详情: module 'openai' has no attribute 'OpenAI'
❌ ChatGPT速率限制，等待 X 秒后重试 (每次都失败)
```

✅ **推文数据正常：**
```sql
-- 检查最近的推文是否有project_id或topic_id
SELECT 
    id_str,
    project_id,
    topic_id,
    is_valid,
    created_at
FROM twitter_tweet
WHERE created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
ORDER BY created_at DESC
LIMIT 10;
```

应该看到 `project_id` 或 `topic_id` 有值的记录。

## 参考链接

- OpenAI Python SDK 迁移指南: https://github.com/openai/openai-python/discussions/742
- OpenAI API文档: https://platform.openai.com/docs/api-reference
- 项目requirements.txt: 已更新为 `openai>=2.0.0`

