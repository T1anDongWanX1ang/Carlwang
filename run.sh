#!/bin/bash

# Twitter数据爬虫启动脚本

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3"
    exit 1
fi

# 检查依赖
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖包..."
pip install -r requirements.txt

# 根据参数选择运行模式
case "${1:-once}" in
    "test")
        echo "运行连接测试..."
        python main.py --mode test
        ;;
    "once")
        echo "执行单次爬取..."
        python main.py --mode once
        ;;
    "schedule")
        echo "启动定时调度..."
        python main.py --mode schedule
        ;;
    "topic")
        echo "运行话题分析..."
        python main.py --mode topic
        ;;
    "kol")
        echo "运行KOL分析..."
        python main.py --mode kol
        ;;
    "project")
        echo "运行项目分析..."
        python main.py --mode project
        ;;
    *)
        echo "使用方法: $0 [test|once|schedule|topic|kol|project]"
        echo "  test     - 测试连接"
        echo "  once     - 单次执行"
        echo "  schedule - 定时调度"
        echo "  topic    - 话题分析"
        echo "  kol      - KOL分析"
        echo "  project  - 项目分析"
        exit 1
        ;;
esac 