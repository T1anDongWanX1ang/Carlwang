#!/bin/bash
# 实时监控回填进度

LOG_FILE="/Users/qmk/Documents/QC/twitter/Carlwang/backfill_cmc300_tweets/logs/twitter_crawler.log"

echo "=========================================="
echo "  📊 实时监控 - 按 Ctrl+C 停止"
echo "=========================================="
echo ""

while true; do
    clear
    echo "=========================================="
    echo "  📊 项目推文回填实时监控"
    echo "=========================================="
    echo ""
    echo "⏰ 当前时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # API调用次数
    API_COUNT=$(grep -E "\[API调用\] 请求 #[0-9]+" "$LOG_FILE" | tail -1 | grep -oE "#[0-9]+" | tr -d '#')
    echo "🔗 API调用次数: ${API_COUNT:-0} 次"

    # 获取的推文总数
    TWEETS=$(grep "获取.*条推文.*累计:" "$LOG_FILE" | tail -1 | grep -oE "累计: [0-9]+" | awk '{print $2}')
    echo "📥 API获取推文: ${TWEETS:-0} 条"

    # 有效推文数（时间窗口内）
    VALID=$(grep "累计.*条有效" "$LOG_FILE" | tail -3 | tail -1 | grep -oE "累计 [0-9]+ 条有效" | awk '{print $2}')
    echo "✅ 有效推文数: ${VALID:-0} 条（在时间窗口内）"

    # 累计成本
    COST=$(grep "累计成本:" "$LOG_FILE" | tail -1 | grep -oE "\$[0-9]+\.[0-9]+" | tr -d '$')
    echo "💰 累计成本: \$${COST:-0.000} USD"

    # 当前页数
    PAGE=$(grep "获取第.*页.*最多.*页" "$LOG_FILE" | tail -1 | grep -oE "第 [0-9]+ 页")
    MAX_PAGE=$(grep "获取第.*页.*最多.*页" "$LOG_FILE" | tail -1 | grep -oE "最多 [0-9]+ 页" | awk '{print $2}')
    echo "📄 当前页数: ${PAGE:-第0页} / ${MAX_PAGE:-0页}"

    echo ""
    echo "=========================================="
    echo "  🕒 最新推文时间 (最近5条)"
    echo "=========================================="
    echo ""

    # 最新推文的创建时间
    grep "推文.*简化增强完成" "$LOG_FILE" | tail -5 | while read line; do
        timestamp=$(echo "$line" | awk '{print $1, $2}')
        tweet_id=$(echo "$line" | grep -oE "项目推文 [0-9]+" | awk '{print $2}')
        sentiment=$(echo "$line" | grep -oE "sentiment=[^,]+" | cut -d'=' -f2)
        echo "  [$timestamp] Tweet ID: $tweet_id | 情绪: $sentiment"
    done

    echo ""
    echo "=========================================="
    echo "  📌 当前状态"
    echo "=========================================="
    echo ""

    # 检查当前在做什么
    CURRENT_STATUS=$(tail -3 "$LOG_FILE" | grep -E "INFO" | tail -1 | awk -F' - ' '{print $NF}')
    echo "$CURRENT_STATUS"

    echo ""
    echo "=========================================="

    # 检查是否完成
    if tail -20 "$LOG_FILE" | grep -qE "回填完成统计|回填任务完成"; then
        echo ""
        echo "🎉 回填完成！"
        echo ""
        break
    fi

    sleep 5
done

echo ""
echo "监控结束"
