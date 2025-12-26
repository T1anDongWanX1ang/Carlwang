#!/bin/bash

# Twitter数据爬虫生产环境部署脚本

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

print_info "🚀 开始部署Twitter数据爬虫服务"

# 1. 检查环境
print_info "检查部署环境..."

if [ ! -f "requirements.txt" ]; then
    print_error "未找到requirements.txt文件"
    exit 1
fi

# 2. 检查Python版本
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
print_info "Python版本: $python_version"

# 3. 创建虚拟环境
if [ ! -d "venv" ]; then
    print_info "创建虚拟环境..."
    python3 -m venv venv
fi

# 4. 激活虚拟环境并安装依赖
print_info "安装依赖包..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. 初始化配置文件
if [ ! -f "config/config.json" ]; then
    print_info "初始化配置文件..."
    if [ -f "config/config.json.template" ]; then
        cp config/config.json.template config/config.json
        print_success "配置文件已创建: config/config.json"
    else
        print_error "未找到配置模板文件: config/config.json.template"
        exit 1
    fi
fi

# 6. 环境变量配置
if [ ! -f ".env" ]; then
    print_warning "未找到.env文件"
    
    if [ -f ".env.template" ]; then
        print_info "复制环境变量模板..."
        cp .env.template .env
        print_warning "请编辑 .env 文件并填入实际的API密钥和数据库配置"
        print_info "编辑命令: nano .env 或 vim .env"
        
        # 询问是否继续
        echo -n "是否已配置环境变量? (y/N): "
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_error "请先配置环境变量后再部署"
            exit 1
        fi
    else
        print_error "未找到环境变量模板文件"
        exit 1
    fi
fi

# 7. 加载环境变量
if [ -f ".env" ]; then
    print_info "加载环境变量..."
    export $(grep -v '^#' .env | xargs)
fi

# 8. 验证配置
print_info "验证配置..."
if ! python3 env_config.py; then
    print_error "配置验证失败，请检查环境变量"
    exit 1
fi

# 9. 测试连接
print_info "测试数据库和API连接..."
if ! python3 main.py --mode test; then
    print_error "连接测试失败"
    exit 1
fi

# 10. 设置systemd服务（可选）
if command -v systemctl >/dev/null 2>&1; then
    echo -n "是否设置systemd服务? (y/N): "
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        setup_systemd_service
    fi
fi

print_success "🎉 部署完成！"
print_info "启动服务命令:"
print_info "  ./start_service.sh start     # 启动服务"
print_info "  ./start_service.sh status    # 查看状态"
print_info "  ./start_service.sh logs      # 查看日志"

# systemd服务设置函数
setup_systemd_service() {
    local service_name="twitter-crawler"
    local service_file="/etc/systemd/system/${service_name}.service"
    local work_dir="$(pwd)"
    
    print_info "设置systemd服务..."
    
    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=Twitter Data Crawler Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$work_dir
Environment=PATH=$work_dir/venv/bin
EnvironmentFile=$work_dir/.env
ExecStart=$work_dir/venv/bin/python $work_dir/main.py --mode schedule
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable "$service_name"
    
    print_success "systemd服务已设置: $service_name"
    print_info "服务管理命令:"
    print_info "  sudo systemctl start $service_name"
    print_info "  sudo systemctl status $service_name"
    print_info "  sudo systemctl stop $service_name"
}