#!/bin/bash
# Marco数据生成定时任务设置脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
MARCO_LOG="$LOG_DIR/marco_cron.log"
PID_FILE="$SCRIPT_DIR/marco_daemon.pid"

# 创建日志目录
mkdir -p "$LOG_DIR"

echo "🚀 Marco数据生成定时任务设置"
echo "📁 项目目录: $SCRIPT_DIR"
echo "📝 日志文件: $MARCO_LOG"

# 函数：显示帮助信息
show_help() {
    cat << EOF
🎯 Marco定时任务管理脚本

用法:
  $0 [command]

命令:
  install-cron    安装crontab定时任务（每30分钟执行一次）
  remove-cron     移除crontab定时任务
  start-daemon    启动守护进程模式
  stop-daemon     停止守护进程模式
  status         查看服务状态
  logs           查看日志
  test           测试Marco数据生成
  help           显示此帮助信息

定时任务模式:
  - crontab模式: 每30分钟由系统调度执行一次
  - daemon模式: 长期运行的守护进程，内部每30分钟执行一次

推荐使用crontab模式，更稳定可靠。
EOF
}

# 函数：安装crontab定时任务
install_cron() {
    echo "📅 安装crontab定时任务..."
    
    # 检查是否已存在相关任务
    if crontab -l 2>/dev/null | grep -q "run_marco.py"; then
        echo "⚠️ 检测到已存在Marco相关的crontab任务"
        echo "现有任务:"
        crontab -l 2>/dev/null | grep "run_marco.py"
        echo ""
        read -p "是否要覆盖现有任务? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ 已取消安装"
            return 1
        fi
        
        # 移除现有的Marco任务
        crontab -l 2>/dev/null | grep -v "run_marco.py" | crontab -
    fi
    
    # 添加新的定时任务
    (crontab -l 2>/dev/null; echo "# Marco数据生成 - 每30分钟执行一次") | crontab -
    (crontab -l 2>/dev/null; echo "*/30 * * * * cd $SCRIPT_DIR && python run_marco.py --quiet --log-file $MARCO_LOG") | crontab -
    (crontab -l 2>/dev/null; echo "# Marco数据回填 - 每天凌晨1点执行") | crontab -
    (crontab -l 2>/dev/null; echo "0 1 * * * cd $SCRIPT_DIR && python run_marco.py today --quiet --log-file $MARCO_LOG") | crontab -
    
    echo "✅ crontab定时任务安装成功!"
    echo ""
    echo "📋 当前crontab任务:"
    crontab -l | grep -E "(Marco|run_marco)"
    echo ""
    echo "📝 日志文件: $MARCO_LOG"
    echo "🔍 查看日志: tail -f $MARCO_LOG"
}

# 函数：移除crontab定时任务
remove_cron() {
    echo "🗑️ 移除crontab定时任务..."
    
    if crontab -l 2>/dev/null | grep -q "run_marco.py"; then
        # 移除Marco相关的任务和注释
        crontab -l 2>/dev/null | grep -v "run_marco.py" | grep -v "# Marco数据" | crontab -
        echo "✅ crontab定时任务已移除"
    else
        echo "⚠️ 没有找到Marco相关的crontab任务"
    fi
}

# 函数：启动守护进程模式
start_daemon() {
    echo "🚀 启动Marco守护进程..."
    
    # 检查是否已在运行
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "⚠️ Marco守护进程已在运行 (PID: $(cat $PID_FILE))"
        return 1
    fi
    
    # 启动守护进程
    cd "$SCRIPT_DIR"
    nohup python run_marco.py daemon --log-file "$MARCO_LOG" > "$LOG_DIR/daemon_stdout.log" 2>&1 &
    DAEMON_PID=$!
    echo $DAEMON_PID > "$PID_FILE"
    
    echo "✅ Marco守护进程已启动 (PID: $DAEMON_PID)"
    echo "📝 日志文件: $MARCO_LOG"
    echo "🔍 查看日志: tail -f $MARCO_LOG"
    echo "🛑 停止命令: $0 stop-daemon"
}

# 函数：停止守护进程模式  
stop_daemon() {
    echo "🛑 停止Marco守护进程..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 $PID 2>/dev/null; then
            kill -TERM $PID
            echo "📡 已发送终止信号到进程 $PID"
            
            # 等待进程退出
            for i in {1..10}; do
                if ! kill -0 $PID 2>/dev/null; then
                    echo "✅ Marco守护进程已停止"
                    rm -f "$PID_FILE"
                    return 0
                fi
                sleep 1
            done
            
            # 如果进程仍在运行，强制杀死
            if kill -0 $PID 2>/dev/null; then
                kill -KILL $PID
                echo "💥 强制终止Marco守护进程"
            fi
        else
            echo "⚠️ PID文件存在但进程未运行"
        fi
        rm -f "$PID_FILE"
    else
        echo "⚠️ 没有找到Marco守护进程PID文件"
    fi
}

# 函数：查看服务状态
show_status() {
    echo "📊 Marco服务状态:"
    echo ""
    
    # 检查crontab任务
    echo "📅 Crontab任务:"
    if crontab -l 2>/dev/null | grep -q "run_marco.py"; then
        echo "✅ 已安装定时任务:"
        crontab -l | grep -E "(Marco|run_marco)" | sed 's/^/  /'
    else
        echo "❌ 未安装定时任务"
    fi
    echo ""
    
    # 检查守护进程
    echo "🚀 守护进程:"
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "✅ 守护进程运行中 (PID: $(cat $PID_FILE))"
    else
        echo "❌ 守护进程未运行"
    fi
    echo ""
    
    # 检查最近的日志
    if [ -f "$MARCO_LOG" ]; then
        echo "📝 最近的日志 (最后5行):"
        tail -5 "$MARCO_LOG" | sed 's/^/  /'
    else
        echo "📝 日志文件不存在: $MARCO_LOG"
    fi
}

# 函数：查看日志
show_logs() {
    if [ -f "$MARCO_LOG" ]; then
        echo "📝 Marco日志文件: $MARCO_LOG"
        echo "🔍 实时查看日志 (按Ctrl+C退出):"
        tail -f "$MARCO_LOG"
    else
        echo "❌ 日志文件不存在: $MARCO_LOG"
    fi
}

# 函数：测试Marco数据生成
test_marco() {
    echo "🧪 测试Marco数据生成..."
    cd "$SCRIPT_DIR"
    python run_marco.py test
    echo ""
    echo "📊 尝试生成一次Marco数据..."
    python run_marco.py
}

# 主逻辑
case "${1:-help}" in
    install-cron)
        install_cron
        ;;
    remove-cron)
        remove_cron
        ;;
    start-daemon)
        start_daemon
        ;;
    stop-daemon)
        stop_daemon
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    test)
        test_marco
        ;;
    help|*)
        show_help
        ;;
esac