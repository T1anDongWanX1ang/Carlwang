#!/bin/bash

# 日常推文爬取 - 快速操作脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_menu() {
    clear
    echo "=================================================="
    echo -e "${BLUE}📊 日常推文爬取服务 - 快速操作${NC}"
    echo "=================================================="
    echo ""
    echo "1. 启动服务"
    echo "2. 停止服务"
    echo "3. 重启服务"
    echo "4. 查看状态"
    echo "5. 查看日志 (实时)"
    echo "6. 查看日志 (最新100行)"
    echo "7. 查看成本统计"
    echo "8. 执行单次爬取"
    echo "9. 退出"
    echo ""
    echo "=================================================="
    echo -n "请选择操作 [1-9]: "
}

while true; do
    show_menu
    read choice

    case $choice in
        1)
            echo ""
            ./start_service_project_twitterapi.sh start
            echo ""
            read -p "按回车键继续..."
            ;;
        2)
            echo ""
            ./start_service_project_twitterapi.sh stop
            echo ""
            read -p "按回车键继续..."
            ;;
        3)
            echo ""
            ./start_service_project_twitterapi.sh restart
            echo ""
            read -p "按回车键继续..."
            ;;
        4)
            echo ""
            ./check_status.sh
            echo ""
            read -p "按回车键继续..."
            ;;
        5)
            echo ""
            echo -e "${YELLOW}实时日志监控 (按 Ctrl+C 退出)${NC}"
            echo ""
            tail -f ../service_scripts/service_project_twitterapi.log
            ;;
        6)
            echo ""
            ./start_service_project_twitterapi.sh logs 100
            echo ""
            read -p "按回车键继续..."
            ;;
        7)
            echo ""
            ./monitor_daily_cost.sh
            echo ""
            read -p "按回车键继续..."
            ;;
        8)
            echo ""
            ./start_service_project_twitterapi.sh once
            echo ""
            read -p "按回车键继续..."
            ;;
        9)
            echo ""
            echo -e "${GREEN}感谢使用！${NC}"
            exit 0
            ;;
        *)
            echo ""
            echo -e "${YELLOW}无效的选择，请重新输入${NC}"
            sleep 2
            ;;
    esac
done
