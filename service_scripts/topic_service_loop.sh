#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/logs/topic_service.log"
PYTHON_CMD="python3 main.py --mode topic"
INTERVAL=300

run_topic_analysis() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting topic analysis..." >> "$LOG_FILE"
    cd "$SCRIPT_DIR"
    $PYTHON_CMD >> "$LOG_FILE" 2>&1
    local exit_code=$?
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Topic analysis completed (exit code: $exit_code)" >> "$LOG_FILE"
    return $exit_code
}

while true; do
    run_topic_analysis
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Waiting 5 minutes for next run..." >> "$LOG_FILE"
    sleep $INTERVAL
done
