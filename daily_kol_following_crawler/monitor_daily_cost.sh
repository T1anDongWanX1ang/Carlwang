#!/bin/bash

# KOL Following 爬取服务 - 成本统计脚本
# 显示 API 调用成本、KOL 处理统计等

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/service_kol_following.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo ""
echo "=================================================="
echo -e "${CYAN}📊 KOL Following 爬取服务 - 成本统计${NC}"
echo "=================================================="
echo ""

if [ ! -f "$LOG_FILE" ]; then
    echo -e "${RED}❌ 日志文件不存在: $LOG_FILE${NC}"
    exit 1
fi

# 统计数据
TOTAL_RUNS=$(grep -c "开始执行 KOL Following 爬取" "$LOG_FILE" 2>/dev/null || echo "0")
SUCCESS_RUNS=$(grep -c "KOL Following 爬取完成" "$LOG_FILE" 2>/dev/null || echo "0")
FAILED_RUNS=$(grep -c "KOL Following 爬取失败" "$LOG_FILE" 2>/dev/null || echo "0")

# API 调用统计（使用 $NF 提取最后一个字段，即数字）
API_CALLS=$(grep "API调用次数:" "$LOG_FILE" 2>/dev/null | awk '{sum+=$NF} END {print sum+0}')
CACHE_HITS=$(grep -c "缓存命中" "$LOG_FILE" 2>/dev/null || echo "0")

# KOL 处理统计
TOTAL_KOLS_PROCESSED=$(grep "已处理:" "$LOG_FILE" 2>/dev/null | awk '{sum+=$NF} END {print sum+0}')
SUCCESS_KOLS=$(grep "成功:" "$LOG_FILE" 2>/dev/null | awk '{sum+=$NF} END {print sum+0}')
FAILED_KOLS=$(grep "失败:" "$LOG_FILE" 2>/dev/null | awk '{sum+=$NF} END {print sum+0}')

# Following 数据统计
TOTAL_FOLLOWINGS=$(grep "总关注用户数:" "$LOG_FILE" 2>/dev/null | awk '{sum+=$NF} END {print sum+0}')
INSERTED_FOLLOWINGS=$(grep "新增入库:" "$LOG_FILE" 2>/dev/null | awk '{sum+=$NF} END {print sum+0}')
SKIPPED_FOLLOWINGS=$(grep "已存在跳过:" "$LOG_FILE" 2>/dev/null | awk '{sum+=$NF} END {print sum+0}')

# API 成本估算
# TwitterAPI following 端点返回完整用户资料，按 User Profiles 计费
# 定价：$0.18 per 1,000 user profiles
# 每次API调用返回200个用户资料，成本：0.18 × (200/1000) = $0.036 per request
COST_PER_API_CALL=0.036
TOTAL_COST=$(echo "$API_CALLS * $COST_PER_API_CALL" | bc -l 2>/dev/null || echo "0")

echo -e "${GREEN}总运行次数:${NC} $TOTAL_RUNS 次"
echo -e "${GREEN}  - 成功:${NC} $SUCCESS_RUNS 次"
echo -e "${GREEN}  - 失败:${NC} $FAILED_RUNS 次"
echo ""

echo "=================================================="
echo -e "${MAGENTA}💰 API 调用统计${NC}"
echo "=================================================="
echo ""
echo -e "${GREEN}API 调用次数:${NC} $API_CALLS 次"
echo -e "${GREEN}缓存命中次数:${NC} $CACHE_HITS 次"
# 格式化成本显示，确保有前导0
TOTAL_COST_FORMATTED=$(printf "%.2f" $TOTAL_COST)
echo -e "${GREEN}预估总成本:${NC} \$$TOTAL_COST_FORMATTED USD (按 \$$COST_PER_API_CALL/次)"
echo ""

if [ $API_CALLS -gt 0 ]; then
    AVG_COST_PER_RUN=$(echo "scale=6; $TOTAL_COST / $TOTAL_RUNS" | bc -l 2>/dev/null || echo "0")
    AVG_COST_FORMATTED=$(printf "%.6f" $AVG_COST_PER_RUN)
    echo -e "${YELLOW}平均每次运行成本:${NC} \$$AVG_COST_FORMATTED USD"
fi

echo ""
echo "=================================================="
echo -e "${BLUE}👥 KOL 处理统计${NC}"
echo "=================================================="
echo ""
echo -e "${GREEN}累计处理 KOL:${NC} $TOTAL_KOLS_PROCESSED 个"
echo -e "${GREEN}  - 成功:${NC} $SUCCESS_KOLS 个"
echo -e "${GREEN}  - 失败:${NC} $FAILED_KOLS 个"
echo ""

if [ $SUCCESS_KOLS -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=2; $SUCCESS_KOLS * 100 / $TOTAL_KOLS_PROCESSED" | bc -l 2>/dev/null || echo "0")
    echo -e "${YELLOW}成功率:${NC} ${SUCCESS_RATE}%"
fi

echo ""
echo "=================================================="
echo -e "${CYAN}📋 Following 数据统计${NC}"
echo "=================================================="
echo ""
echo -e "${GREEN}累计获取 Following:${NC} $TOTAL_FOLLOWINGS 条"
echo -e "${GREEN}累计新增入库:${NC} $INSERTED_FOLLOWINGS 条"
echo -e "${GREEN}累计已存在跳过:${NC} $SKIPPED_FOLLOWINGS 条"
echo ""

if [ $TOTAL_FOLLOWINGS -gt 0 ] && [ $SUCCESS_KOLS -gt 0 ]; then
    AVG_FOLLOWING_PER_KOL=$(echo "scale=2; $TOTAL_FOLLOWINGS / $SUCCESS_KOLS" | bc -l 2>/dev/null || echo "0")
    echo -e "${YELLOW}平均每个 KOL Following 数:${NC} $AVG_FOLLOWING_PER_KOL 个"
fi

if [ $INSERTED_FOLLOWINGS -gt 0 ] && [ $API_CALLS -gt 0 ]; then
    COST_PER_FOLLOWING=$(echo "scale=6; $TOTAL_COST / $INSERTED_FOLLOWINGS" | bc -l 2>/dev/null || echo "0")
    COST_PER_FOLLOWING_FORMATTED=$(printf "%.6f" $COST_PER_FOLLOWING)
    echo -e "${YELLOW}平均每条 Following 成本:${NC} \$$COST_PER_FOLLOWING_FORMATTED USD"
fi

echo ""
echo "=================================================="
echo -e "${MAGENTA}💡 成本预估${NC}"
echo "=================================================="
echo ""

# 按当前配置预估月成本
# 默认配置：每天运行一次，每次处理10个KOL
RUNS_PER_DAY=1  # 默认每天1次
DAYS_PER_MONTH=30

if [ $TOTAL_RUNS -gt 0 ]; then
    MONTHLY_COST=$(echo "scale=2; $AVG_COST_PER_RUN * $RUNS_PER_DAY * $DAYS_PER_MONTH" | bc -l 2>/dev/null || echo "0")
    MONTHLY_COST_FORMATTED=$(printf "%.2f" $MONTHLY_COST)
    echo -e "${YELLOW}预估月成本:${NC} \$$MONTHLY_COST_FORMATTED USD (按每天${RUNS_PER_DAY}次运行)"
fi

echo ""

# 最近一次运行的详细信息
echo "=================================================="
echo -e "${CYAN}🔍 最近一次运行详情${NC}"
echo "=================================================="
echo ""

LAST_START=$(grep "开始执行 KOL Following 爬取" "$LOG_FILE" 2>/dev/null | tail -1)
LAST_END=$(grep "KOL Following 爬取完成\|KOL Following 爬取失败" "$LOG_FILE" 2>/dev/null | tail -1)

if [ -n "$LAST_START" ]; then
    echo -e "${GREEN}最近开始时间:${NC}"
    echo "  $LAST_START"
fi

if [ -n "$LAST_END" ]; then
    echo -e "${GREEN}最近结束状态:${NC}"
    echo "  $LAST_END"
fi

echo ""
echo "=================================================="
echo ""
