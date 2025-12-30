#!/bin/bash
# KOL推文回填脚本启动器

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/backfill_kol_tweets.py"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}   KOL推文回填工具${NC}"
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
    echo -e "${GREEN}使用方法:${NC}"
    echo ""
    echo -e "  ${YELLOW}1. 回填最近7天（默认）:${NC}"
    echo -e "     ./start_backfill.sh"
    echo ""
    echo -e "  ${YELLOW}2. 回填指定天数:${NC}"
    echo -e "     ./start_backfill.sh --days 14"
    echo ""
    echo -e "  ${YELLOW}3. 回填指定日期范围:${NC}"
    echo -e "     ./start_backfill.sh --start-date 2024-12-20 --end-date 2024-12-27"
    echo ""
    echo -e "  ${YELLOW}4. 控制每个list的最大页数:${NC}"
    echo -e "     ./start_backfill.sh --days 7 --max-pages 10"
    echo ""
    echo -e "${GREEN}参数说明:${NC}"
    echo -e "  --days N          回填最近N天的数据（默认7天）"
    echo -e "  --start-date DATE 开始日期，格式: YYYY-MM-DD"
    echo -e "  --end-date DATE   结束日期，格式: YYYY-MM-DD"
    echo -e "  --max-pages N     每个list每天最大页数（默认15页）"
    echo ""
}

# 如果没有参数且请求帮助
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_usage
    exit 0
fi

# 运行回填脚本
echo -e "${GREEN}🚀 启动回填任务...${NC}"
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
