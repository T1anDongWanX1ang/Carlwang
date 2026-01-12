#!/bin/bash

# Twitter项目推文历史指标更新脚本
# 用途: 每天运行一次，更新过去7天的推文互动数据（点赞、转发等）
# 建议 Cron 配置: 0 12 * * * /path/to/daily_tweet_crawler/run_update_metrics.sh

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录 (假设脚本在 daily_tweet_crawler 下，根目录在上一级)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

# 日志文件位置
LOG_FILE="$SCRIPT_DIR/logs/update_metrics.log"
mkdir -p "$SCRIPT_DIR/logs"

echo "==================================================" >> "$LOG_FILE"
echo "开始运行历史指标更新任务: $(date)" >> "$LOG_FILE"

# 设置环境变量，确保使用 twitterapi 后端
export TWITTER_API_BACKEND=twitterapi

# 运行更新 (默认7天)
# 使用项目根目录下的 venv
if [[ "$OSTYPE" == "darwin"* ]]; then
    "$PROJECT_ROOT/venv/bin/python" "$PROJECT_ROOT/main.py" --mode update-metrics --days 7 >> "$LOG_FILE" 2>&1
else
    "$PROJECT_ROOT/venv/bin/python" "$PROJECT_ROOT/main.py" --mode update-metrics --days 7 >> "$LOG_FILE" 2>&1
fi

EXIT_CODE=$?

echo "任务结束: $(date) (退出码: $EXIT_CODE)" >> "$LOG_FILE"
echo "==================================================" >> "$LOG_FILE"

exit $EXIT_CODE
