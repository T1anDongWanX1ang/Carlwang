#!/bin/bash

# 历史数据回填成本估算脚本
# 不实际拉取数据，仅估算成本

DAYS=${1:-5}

echo "=========================================="
echo "📊 历史数据回填成本估算"
echo "=========================================="
echo "回填天数: ${DAYS} 天"
echo ""

# 假设每个项目列表每天的推文数量
# 可以根据实际情况调整
TWEETS_PER_LIST_PER_DAY=200

# 项目列表数量（从配置文件读取）
LIST_COUNT=3

# 计算总推文数
TOTAL_TWEETS=$((TWEETS_PER_LIST_PER_DAY * LIST_COUNT * DAYS))

# TwitterAPI.io 定价: $0.15 per 1,000 tweets
COST_PER_1000=0.15
TOTAL_COST=$(echo "scale=4; $TOTAL_TWEETS * $COST_PER_1000 / 1000" | bc)

echo "估算参数:"
echo "  - 项目列表数: ${LIST_COUNT} 个"
echo "  - 每列表每天推文数: ${TWEETS_PER_LIST_PER_DAY} 条 (估算)"
echo "  - 总推文数: ${TOTAL_TWEETS} 条"
echo ""
echo "成本估算:"
echo "  - 单价: \$${COST_PER_1000} / 1,000 条推文"
echo "  - 预估总成本: \$${TOTAL_COST} USD"
echo ""
echo "不同天数对比:"
echo "----------------------------------------"

for d in 1 3 5 7 10 15; do
    tweets=$((TWEETS_PER_LIST_PER_DAY * LIST_COUNT * d))
    cost=$(echo "scale=4; $tweets * $COST_PER_1000 / 1000" | bc)
    printf "  %2d 天: %5d 条推文 → \$%.4f USD\n" $d $tweets $cost
done

echo "=========================================="
echo ""
echo "💡 建议:"
echo "  1. 如果预算充足，可以直接运行:"
echo "     ./backfill_history.sh ${DAYS}"
echo ""
echo "  2. 如果想更精确，可以先查看最近的实际数据量:"
echo "     grep '获取.*条推文' service_scripts/service_project_twitterapi.log | tail -20"
echo ""
echo "  3. 成本可接受后，直接运行一次完整回填，避免重复"
echo "=========================================="
