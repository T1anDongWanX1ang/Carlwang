#!/bin/bash

# 分天回填历史数据脚本 - 已废弃
# 由于 --hours-limit 参数的限制，此脚本会产生大量重复数据
# 请直接使用 backfill_history.sh 一次性回填

echo "⚠️  此脚本已废弃，请使用 backfill_history.sh"
echo ""
echo "示例："
echo "  ./backfill_history.sh 5    # 回填最近5天的数据"
echo ""
exit 1
