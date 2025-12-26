#!/bin/bash

# 快速启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Twitter KOL推文爬取服务 快速启动 ===${NC}"
echo ""
echo "使用默认配置启动服务..."
echo "  - 间隔: 60分钟"
echo "  - 最大页数: 50页"
echo "  - 每页条数: 100条"
echo "  - 时间限制: 3小时"
echo ""

./start_service_kol_tweet.sh start

echo ""
echo "提示："
echo "  - 查看状态: ./check_status.sh"
echo "  - 查看日志: ./start_service_kol_tweet.sh logs"
echo "  - 停止服务: ./start_service_kol_tweet.sh stop"
