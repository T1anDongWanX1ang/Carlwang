#!/bin/bash

# CentOS 7 OpenSSL兼容性修复脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info "🔧 CentOS 7 OpenSSL兼容性修复开始"

# 检查系统版本
if [[ -f /etc/redhat-release ]]; then
    OS_VERSION=$(cat /etc/redhat-release)
    print_info "检测到系统: $OS_VERSION"
else
    print_warning "无法检测系统版本，继续执行修复"
fi

# 检查OpenSSL版本
OPENSSL_VERSION=$(openssl version 2>/dev/null || echo "未检测到OpenSSL")
print_info "OpenSSL版本: $OPENSSL_VERSION"

# 检查Python版本
PYTHON_VERSION=$(python3 --version 2>/dev/null || echo "Python3 未安装")
print_info "Python版本: $PYTHON_VERSION"

# 1. 备份现有虚拟环境
if [ -d "venv" ]; then
    print_info "备份现有虚拟环境..."
    mv venv venv_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
fi

# 2. 创建新的虚拟环境
print_info "创建新的虚拟环境..."
python3 -m venv venv

# 3. 激活虚拟环境
source venv/bin/activate

# 4. 升级pip
print_info "升级pip..."
pip install --upgrade pip

# 5. 安装兼容版本依赖
print_info "安装兼容版本依赖..."
if [ -f "requirements-centos7.txt" ]; then
    pip install -r requirements-centos7.txt
    print_success "已安装CentOS 7兼容依赖"
else
    print_warning "未找到requirements-centos7.txt，使用标准依赖"
    # 手动安装兼容版本
    pip install "requests>=2.28.0,<2.32.0"
    pip install "urllib3>=1.26.12,<2.0.0"
    pip install "pymysql>=1.0.0"
    pip install "python-dateutil>=2.8.0"
    pip install "openai>=0.28.0,<1.0.0"
    pip install "certifi>=2021.5.25,<2023.0.0"
    pip install "charset-normalizer>=2.0.0,<4.0.0"
    pip install "idna>=2.10,<4.0.0"
fi

# 6. 验证安装
print_info "验证依赖安装..."
python3 -c "
import requests
import urllib3
import pymysql
import openai
print('✅ 所有依赖导入成功')
print(f'requests版本: {requests.__version__}')
print(f'urllib3版本: {urllib3.__version__}')
print(f'pymysql版本: {pymysql.__version__}')
print(f'openai版本: {openai.__version__}')
"

# 7. 测试连接
print_info "测试应用连接..."
if python3 main.py --mode test; then
    print_success "✅ 应用测试通过"
else
    print_error "❌ 应用测试失败，请检查配置"
    exit 1
fi

print_success "🎉 CentOS 7兼容性修复完成！"
print_info "现在可以运行:"
print_info "  ./start_service.sh once      # 单次执行"
print_info "  ./start_service.sh start     # 启动服务"

# 清理
deactivate 2>/dev/null || true