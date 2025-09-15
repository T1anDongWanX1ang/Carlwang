#!/bin/bash

# 配置文件初始化脚本
# 用于在服务器部署时创建必要的配置文件

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

print_info "🔧 配置文件初始化"

# 检查config目录
if [ ! -d "config" ]; then
    print_error "config目录不存在"
    exit 1
fi

# 检查模板文件
if [ ! -f "config/config.json.template" ]; then
    print_error "配置模板文件不存在: config/config.json.template"
    exit 1
fi

# 如果配置文件已存在，询问是否覆盖
if [ -f "config/config.json" ]; then
    echo -n "配置文件已存在，是否覆盖？(y/N): "
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_info "跳过配置文件创建"
        exit 0
    fi
fi

print_info "从模板创建配置文件..."
cp config/config.json.template config/config.json

print_success "✅ 配置文件已创建: config/config.json"
print_warning "⚠️  请编辑配置文件，替换以下占位符为实际值："
print_info "  - YOUR_TWEETSCOUT_API_KEY"
print_info "  - YOUR_OPENAI_API_KEY" 
print_info "  - YOUR_DATABASE_HOST"
print_info "  - YOUR_DATABASE_NAME"
print_info "  - YOUR_DATABASE_USERNAME"
print_info "  - YOUR_DATABASE_PASSWORD"

echo ""
print_info "📝 编辑命令："
print_info "  nano config/config.json"
print_info "  vim config/config.json"

echo ""
print_info "🔑 或者使用交互式配置脚本："
print_info "  python3 setup_config.py"

echo ""
print_info "✅ 配置完成后，运行测试："
print_info "  python3 main.py --mode test"