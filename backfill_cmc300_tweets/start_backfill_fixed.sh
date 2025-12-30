#!/bin/bash
# 项目推文回填脚本启动器（修复版）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/backfill_project_tweets_fixed.py"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}   项目推文回填工具 (CMC300) - 修复版${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# 检查Python脚本是否存在
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}❌ 错误: 找不到回填脚本${NC}"
    echo -e "   期望位置: $PYTHON_SCRIPT"
    exit 1
fi

# 显示使用说明
show_usage() {
    echo -e "${GREEN}使用方法 (修复版 - 一次性拉取):${NC}"
    echo ""
    echo -e "  ${YELLOW}1. 补充12月22日到今天的数据（推荐）:${NC}"
    echo -e "     ./start_backfill_fixed.sh --start-date 2024-12-22"
    echo ""
    echo -e "  ${YELLOW}2. 指定最大页数:${NC}"
    echo -e "     ./start_backfill_fixed.sh --start-date 2024-12-22 --max-pages 300"
    echo ""
    echo -e "  ${YELLOW}3. 指定日期范围:${NC}"
    echo -e "     ./start_backfill_fixed.sh --start-date 2024-12-22 --end-date 2024-12-28"
    echo ""
    echo -e "${GREEN}参数说明:${NC}"
    echo -e "  --start-date DATE     开始日期，格式: YYYY-MM-DD (必需)"
    echo -e "  --end-date DATE       结束日期，格式: YYYY-MM-DD (可选，默认到今天)"
    echo -e "  --max-pages N         总最大页数（默认200页，约4000条推文）"
    echo -e "  --page-size N         每页大小（默认100条）"
    echo ""
    echo -e "${YELLOW}⚡ 修复说明:${NC}"
    echo -e "  ✅ 一次性拉取所有数据，不会重复调用API"
    echo -e "  ✅ 成本降低约70-80%"
    echo -e "  ✅ 数据库自动去重"
    echo ""
}

# 如果没有参数且请求帮助
if [ "$1" = "-h" ] || [ "$1" = "--help" ] || [ -z "$1" ]; then
    show_usage
    exit 0
fi

# 运行回填脚本
echo -e "${GREEN}🚀 启动回填任务 (修复版)...${NC}"
echo ""

python3 "$PYTHON_SCRIPT" "$@"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ 回填任务完成！${NC}"
else
    echo -e "${RED}❌ 回填任务失败（退出码: $EXIT_CODE）${NC}"
fi

exit $EXIT_CODE
