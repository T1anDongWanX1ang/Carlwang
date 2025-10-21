#!/bin/bash

# Topic Analysis Service Management Script
# Executes topic analysis every 5 minutes (python main.py --mode topic)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/topic_service.pid"
LOG_FILE="$SCRIPT_DIR/logs/topic_service.log"
PYTHON_CMD="python3 main.py --mode topic"
INTERVAL=900  # 15 minutes in seconds

# Ensure logs directory exists
mkdir -p "$SCRIPT_DIR/logs"

run_topic_analysis() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting topic analysis..."
    cd "$SCRIPT_DIR"
    $PYTHON_CMD
    local exit_code=$?
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Topic analysis completed (exit code: $exit_code)"
    return $exit_code
}

start_service() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Topic service already running with PID $(cat $PID_FILE)"
        return 1
    fi
    
    echo "Starting topic analysis service (every 5 minutes)..."
    
    # Create a separate script for the service loop
    cat > "$SCRIPT_DIR/topic_service_loop.sh" << 'EOF'
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
EOF
    
    chmod +x "$SCRIPT_DIR/topic_service_loop.sh"
    
    # Start service in background with anti-sleep protection
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - use caffeinate to prevent sleep
        nohup caffeinate -i "$SCRIPT_DIR/topic_service_loop.sh" &
    else
        # Linux - use nice for priority
        nohup nice -n -10 "$SCRIPT_DIR/topic_service_loop.sh" &
    fi
    
    echo $! > "$PID_FILE"
    echo "Topic service started with PID $!"
    echo "Logs: $LOG_FILE"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Next run: $(date -v+5M '+%Y-%m-%d %H:%M:%S')"
    else
        echo "Next run: $(date -d '+5 minutes' '+%Y-%m-%d %H:%M:%S')"
    fi
}

stop_service() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Topic service not running (no PID file)"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping topic service (PID: $PID)..."
        kill "$PID"
        
        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if kill -0 "$PID" 2>/dev/null; then
            echo "Force stopping..."
            kill -9 "$PID"
        fi
        
        rm -f "$PID_FILE"
        echo "Topic service stopped"
    else
        echo "Topic service not running"
        rm -f "$PID_FILE"
    fi
}

status_service() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Topic service running with PID $(cat $PID_FILE)"
        
        # Show last execution time from logs
        if [ -f "$LOG_FILE" ]; then
            echo "Last execution:"
            grep -E "Starting topic analysis|completed" "$LOG_FILE" | tail -2
        fi
        
        # Calculate next run time
        if [ -f "$LOG_FILE" ]; then
            last_start=$(grep "Starting topic analysis" "$LOG_FILE" | tail -1 | cut -d' ' -f1-2)
            if [ -n "$last_start" ]; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    # macOS date format
                    next_run=$(date -v+5M "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "Unknown")
                else
                    # Linux date format
                    next_run=$(date -d "$last_start + 5 minutes" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "Unknown")
                fi
                echo "Next run: $next_run"
            fi
        fi
        return 0
    else
        echo "Topic service not running"
        return 1
    fi
}

run_once() {
    echo "Running topic analysis once..."
    cd "$SCRIPT_DIR"
    run_topic_analysis
}

show_logs() {
    local lines=${1:-50}
    if [ -f "$LOG_FILE" ]; then
        echo "=== Last $lines lines of topic service logs ==="
        tail -n "$lines" "$LOG_FILE"
    else
        echo "No log file found at $LOG_FILE"
    fi
}

case "$1" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        stop_service
        sleep 2
        start_service
        ;;
    status)
        status_service
        ;;
    once)
        run_once
        ;;
    logs)
        show_logs "$2"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|once|logs [lines]}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the topic analysis service (every 5 minutes)"
        echo "  stop     - Stop the topic analysis service"
        echo "  restart  - Restart the topic analysis service"
        echo "  status   - Check service status and next run time"
        echo "  once     - Run topic analysis once immediately"
        echo "  logs     - Show service logs (default: 50 lines)"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 once"
        echo "  $0 logs 100"
        exit 1
        ;;
esac