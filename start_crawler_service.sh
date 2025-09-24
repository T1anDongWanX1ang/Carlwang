#!/bin/bash

# Twitter Crawler Service Management Script
# Manages the scheduled crawler service (python main.py --mode schedule --interval 5)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/crawler_service.pid"
LOG_FILE="$SCRIPT_DIR/logs/crawler_service.log"
PYTHON_CMD="python main.py --mode schedule --interval 5"

# Ensure logs directory exists
mkdir -p "$SCRIPT_DIR/logs"

start_service() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Service already running with PID $(cat $PID_FILE)"
        return 1
    fi
    
    echo "Starting crawler service..."
    
    # Start service in background with anti-sleep protection
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - use caffeinate to prevent sleep
        nohup caffeinate -i $PYTHON_CMD >> "$LOG_FILE" 2>&1 &
    else
        # Linux - use nice for priority
        nohup nice -n -10 $PYTHON_CMD >> "$LOG_FILE" 2>&1 &
    fi
    
    echo $! > "$PID_FILE"
    echo "Service started with PID $!"
    echo "Logs: $LOG_FILE"
}

stop_service() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Service not running (no PID file)"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping service (PID: $PID)..."
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
        echo "Service stopped"
    else
        echo "Service not running"
        rm -f "$PID_FILE"
    fi
}

status_service() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Service running with PID $(cat $PID_FILE)"
        return 0
    else
        echo "Service not running"
        return 1
    fi
}

show_logs() {
    local lines=${1:-50}
    if [ -f "$LOG_FILE" ]; then
        echo "=== Last $lines lines of service logs ==="
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
    logs)
        show_logs "$2"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [lines]}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the crawler service"
        echo "  stop     - Stop the crawler service"
        echo "  restart  - Restart the crawler service"
        echo "  status   - Check service status"
        echo "  logs     - Show service logs (default: 50 lines)"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 logs 100"
        exit 1
        ;;
esac