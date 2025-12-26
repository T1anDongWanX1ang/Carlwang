#!/bin/bash

# 历史数据回填脚本
# 用于补充最近N天的推文数据

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 默认回填5天
DAYS=${1:-5}
HOURS=$((DAYS * 24))

echo "=========================================="
echo "开始回填最近 ${DAYS} 天的历史数据"
echo "时间窗口: ${HOURS} 小时"
echo "=========================================="

# 使用TwitterAPI后端，拉取历史数据
TWITTER_API_BACKEND=twitterapi "$SCRIPT_DIR/venv/bin/python" main.py --mode project-once \
    --hours-limit $HOURS \
    --max-pages 100 \
    --page-size 100

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "=========================================="
    echo "✅ 历史数据回填完成！"
    echo "=========================================="
else
    echo "=========================================="
    echo "❌ 历史数据回填失败 (退出码: $EXIT_CODE)"
    echo "=========================================="
fi

exit $EXIT_CODE
