# CentOS 7 OpenSSL兼容性修复指南

## 🚨 问题描述

在CentOS 7服务器上运行应用时遇到以下错误：

```bash
ImportError: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'OpenSSL 1.0.2k-fips  26 Jan 2017'
```

## 🔍 原因分析

- **CentOS 7** 默认使用 **OpenSSL 1.0.2k**
- **urllib3 v2** 要求 **OpenSSL 1.1.1+**
- 导致依赖包不兼容

## ⚡ 快速修复

### 方案1：自动修复脚本（推荐）

```bash
# 在服务器上执行
./fix_centos7.sh
```

### 方案2：手动修复

```bash
# 1. 删除现有虚拟环境
rm -rf venv

# 2. 创建新虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装兼容版本依赖
pip install --upgrade pip
pip install -r requirements-centos7.txt

# 4. 测试
python3 main.py --mode test
```

### 方案3：直接安装兼容版本

```bash
source venv/bin/activate
pip install "urllib3>=1.26.12,<2.0.0"
pip install "requests>=2.28.0,<2.32.0"
pip install "openai>=0.28.0,<1.0.0"
```

## ✅ 验证修复

修复后运行测试：

```bash
# 测试连接
python3 main.py --mode test

# 单次执行
./start_service.sh once
```

成功输出应包含：
```
✅ 数据库连接: ✓ 成功
✅ API连接: ✓ 成功
```

## 🔧 兼容版本说明

| 包名 | 标准版本 | CentOS 7兼容版本 |
|------|----------|------------------|
| urllib3 | >=2.0.0 | >=1.26.12,<2.0.0 |
| requests | >=2.32.0 | >=2.28.0,<2.32.0 |
| openai | >=1.0.0 | >=0.28.0,<1.0.0 |

## 🐳 其他解决方案

### Docker方式（推荐生产环境）

```bash
# 使用Docker避免系统依赖问题
docker build -t twitter-crawler .
docker run -d \
  --name twitter-crawler \
  -e TWEETSCOUT_API_KEY=your-key \
  -e OPENAI_API_KEY=your-key \
  --restart unless-stopped \
  twitter-crawler
```

### 系统升级（高级）

```bash
# 升级到CentOS 8/Rocky Linux 8（不推荐生产环境）
sudo dnf upgrade --refresh
```

## 📋 预防措施

1. **使用兼容版本依赖文件**：
   ```bash
   pip install -r requirements-centos7.txt
   ```

2. **锁定版本**：
   ```bash
   pip freeze > requirements.lock
   ```

3. **容器化部署**：避免系统依赖问题

## 🆘 仍有问题？

如果仍然遇到问题，请：

1. 检查Python版本：`python3 --version`
2. 检查OpenSSL版本：`openssl version`
3. 查看详细错误：`python3 main.py --mode test`
4. 提供完整错误日志

## 📞 技术支持

- 查看完整部署指南：`DEPLOYMENT_GUIDE.md`
- 快速修复脚本：`./fix_centos7.sh`