#!/bin/bash
# KOL推文流式回填脚本启动器

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/backfill_kol_tweets_streaming.py"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}   KOL推文流式回填工具（边拉边存）${NC}"
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
    echo -e "${GREEN}✨ 流式回填特性:${NC}"
    echo -e "   - 边拉边存：拉取1页 → 立即保存 → 拉取下一页"
    echo -e "   - 中断安全：按Ctrl+C中断后，已保存数据不会丢失"
    echo -e "   - 智能早停：根据推文时间自动停止，不会过度拉取"
    echo -e "   - 成本可控：每拉一页都会显示进度和成本"
    echo ""
    echo -e "${GREEN}使用方法:${NC}"
    echo ""
    echo -e "  ${YELLOW}1. 回填最近7天（推荐）:${NC}"
    echo -e "     ./start_backfill_streaming.sh"
    echo ""
    echo -e "  ${YELLOW}2. 回填指定天数:${NC}"
    echo -e "     ./start_backfill_streaming.sh --days 14"
    echo ""
    echo -e "  ${YELLOW}3. 测试模式（只处理1个list，验证流程）:${NC}"
    echo -e "     ./start_backfill_streaming.sh --test"
    echo ""
    echo -e "${GREEN}参数说明:${NC}"
    echo -e "  --days N    回填最近N天的数据（默认7天）"
    echo -e "  --test      测试模式，只处理1个list验证流程"
    echo ""
    echo -e "${YELLOW}💡 建议：首次使用先运行测试模式确认无误${NC}"
    echo ""
}

# 如果没有参数且请求帮助
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_usage
    exit 0
fi

# 运行回填脚本
echo -e "${GREEN}🚀 启动流式回填任务...${NC}"
echo ""

python3 "$PYTHON_SCRIPT" "$@"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ 回填任务完成！${NC}"
elif [ $EXIT_CODE -eq 1 ]; then
    echo -e "${YELLOW}⚠️  回填任务中断或部分失败${NC}"
    echo -e "${YELLOW}   已保存的数据不会丢失，可以重新运行继续${NC}"
else
    echo -e "${RED}❌ 回填任务失败（退出码: $EXIT_CODE）${NC}"
fi

exit $EXIT_CODE
