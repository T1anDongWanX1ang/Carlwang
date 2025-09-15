#!/usr/bin/env python3
"""
Marco数据计算简化启动脚本
简化复杂的命令行参数，提供直观的启动方式
支持定时任务运行，包含完整的错误处理和日志记录
"""
import sys
import os
import signal
import time
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.marco_processor import marco_processor
from src.database.marco_dao import marco_dao
from src.utils.logger import setup_logger
import logging


# 全局变量用于控制程序退出
should_exit = False

def signal_handler(signum, frame):
    """信号处理器，用于优雅地退出程序"""
    global should_exit
    print(f"\n📡 接收到信号 {signum}，正在优雅退出...")
    should_exit = True

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # 终止信号


def print_help():
    """显示帮助信息"""
    print("""
🚀 Marco数据计算简化启动脚本

常用命令：
  python run_marco.py                    # 生成最新数据
  python run_marco.py now               # 生成最新数据（同上）
  python run_marco.py daemon            # 以守护进程模式运行（每30分钟自动生成）
  python run_marco.py today             # 回填今天的数据
  python run_marco.py week              # 回填最近7天数据
  python run_marco.py month             # 回填最近30天数据
  python run_marco.py stats             # 查看统计信息
  python run_marco.py test              # 测试连接
  python run_marco.py help              # 显示帮助

高级用法：
  python run_marco.py 2025-01-01        # 回填指定日期的数据
  python run_marco.py 2025-01-01 2025-01-07  # 回填指定日期范围

定时任务模式：
  python run_marco.py daemon            # 守护进程模式，每30分钟生成一次
  python run_marco.py --quiet           # 静默模式，减少输出（适合crontab）
  python run_marco.py --log-file path   # 指定日志文件路径

注意：
- 所有时间都自动对齐到30分钟间隔
- 已存在的数据会被自动跳过
- 使用真实AI模型进行计算
- 守护进程模式适合长期运行，crontab模式适合定时调用
    """)


def generate_latest(quiet_mode=False):
    """生成最新Marco数据"""
    logger = logging.getLogger(__name__)
    
    if not quiet_mode:
        print("📊 生成最新Marco数据...")
    
    try:
        now = datetime.now()
        latest_timestamp = now.replace(minute=(now.minute // 30) * 30, second=0, microsecond=0)
        
        logger.info(f"开始生成Marco数据，目标时间: {latest_timestamp}")
        
        # 检查是否已存在数据（避免重复生成）
        if marco_dao.exists_for_timestamp(latest_timestamp):
            if not quiet_mode:
                print(f"⏰ 时间点 {latest_timestamp} 的数据已存在，跳过生成")
            logger.info(f"Marco数据已存在，跳过: {latest_timestamp}")
            return True
        
        if not quiet_mode:
            print(f"⏰ 目标时间: {latest_timestamp}")
        
        marco_data = marco_processor.process_tweets_to_marco(latest_timestamp, lookback_hours=4)
        
        if marco_data:
            if marco_dao.insert(marco_data):
                if not quiet_mode:
                    print(f"✅ 成功生成Marco数据!")
                    print(f"   情感指数: {marco_data.sentiment_index:.2f}")
                    print(f"   AI总结: {marco_data.summary[:100]}...")
                
                logger.info(f"Marco数据生成成功: 时间={latest_timestamp}, 情感指数={marco_data.sentiment_index:.2f}")
                return True
            else:
                error_msg = "保存Marco数据失败"
                if not quiet_mode:
                    print(f"❌ {error_msg}")
                logger.error(error_msg)
                return False
        else:
            error_msg = "生成Marco数据失败，可能是没有足够的推文数据"
            if not quiet_mode:
                print(f"❌ {error_msg}")
            logger.warning(error_msg)
            return False
            
    except Exception as e:
        error_msg = f"生成最新Marco数据异常: {e}"
        if not quiet_mode:
            print(f"❌ {error_msg}")
        logger.error(error_msg, exc_info=True)
        return False


def backfill_days(days):
    """回填指定天数的数据"""
    print(f"📈 回填最近{days}天的Marco数据...")
    
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        print(f"⏰ 时间范围: {start_date.date()} 到 {end_date.date()}")
        
        timestamps = marco_processor.generate_timestamp_sequence(start_date, end_date)
        print(f"📅 需要处理 {len(timestamps)} 个时间点")
        
        success_count = 0
        skip_count = 0
        
        for i, timestamp in enumerate(timestamps, 1):
            # 显示进度
            if i % 10 == 0 or i == len(timestamps):
                print(f"   进度: {i}/{len(timestamps)}")
            
            # 检查是否已存在
            if marco_dao.exists_for_timestamp(timestamp):
                skip_count += 1
                continue
            
            # 生成Marco数据
            marco_data = marco_processor.process_tweets_to_marco(timestamp)
            
            if marco_data and marco_dao.insert(marco_data):
                success_count += 1
        
        print(f"✅ 回填完成!")
        print(f"   成功生成: {success_count} 条")
        print(f"   跳过已存在: {skip_count} 条")
        return True
        
    except Exception as e:
        print(f"❌ 回填数据异常: {e}")
        return False


def backfill_date_range(start_str, end_str=None):
    """回填指定日期范围的数据"""
    try:
        # 解析开始日期
        start_date = datetime.strptime(start_str, '%Y-%m-%d')
        
        # 解析结束日期
        if end_str:
            end_date = datetime.strptime(end_str, '%Y-%m-%d')
            end_date = end_date.replace(hour=23, minute=59)
        else:
            # 如果只指定一天，就是当天的数据
            end_date = start_date.replace(hour=23, minute=59)
        
        print(f"📊 生成日期范围的Marco数据...")
        print(f"⏰ 时间范围: {start_date.date()} 到 {end_date.date()}")
        
        timestamps = marco_processor.generate_timestamp_sequence(start_date, end_date)
        print(f"📅 需要处理 {len(timestamps)} 个时间点")
        
        success_count = 0
        skip_count = 0
        
        for i, timestamp in enumerate(timestamps, 1):
            # 显示进度
            if i % 10 == 0 or i == len(timestamps):
                print(f"   进度: {i}/{len(timestamps)}")
            
            # 检查是否已存在
            if marco_dao.exists_for_timestamp(timestamp):
                skip_count += 1
                continue
            
            # 生成Marco数据
            marco_data = marco_processor.process_tweets_to_marco(timestamp)
            
            if marco_data and marco_dao.insert(marco_data):
                success_count += 1
        
        print(f"✅ 生成完成!")
        print(f"   成功生成: {success_count} 条")
        print(f"   跳过已存在: {skip_count} 条")
        return True
        
    except ValueError:
        print("❌ 日期格式错误，请使用: YYYY-MM-DD")
        return False
    except Exception as e:
        print(f"❌ 生成数据异常: {e}")
        return False


def show_stats():
    """显示统计信息"""
    print("📊 Marco数据统计信息")
    
    try:
        stats = marco_dao.get_statistics()
        
        print(f"📈 总记录数: {stats.get('total_records', 0)}")
        print(f"📊 平均情感指数: {stats.get('average_sentiment', 0):.2f}")
        print(f"⏰ 时间范围: {stats.get('earliest_timestamp', 'N/A')} ~ {stats.get('latest_timestamp', 'N/A')}")
        
        # 显示最新几条记录
        latest_records = marco_dao.get_latest(5)
        if latest_records:
            print("\n📋 最新Marco数据:")
            for record in latest_records:
                print(f"   {record.timestamp} | 情感指数: {record.sentiment_index:.2f}")
                if record.summary:
                    print(f"   总结: {record.summary[:80]}...")
                print("   " + "-" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ 获取统计信息异常: {e}")
        return False


def run_daemon_mode():
    """守护进程模式，每30分钟生成一次Marco数据"""
    logger = logging.getLogger(__name__)
    
    print("🚀 启动Marco数据守护进程模式")
    print("📅 每30分钟生成一次Marco数据（基于最近4小时推文）")
    print("🛑 按Ctrl+C优雅退出")
    
    logger.info("Marco守护进程启动")
    
    # 计算下一个30分钟对齐的时间点
    def get_next_30min_timestamp():
        now = datetime.now()
        # 计算下一个30分钟对齐点
        if now.minute < 30:
            next_time = now.replace(minute=30, second=0, microsecond=0)
        else:
            next_time = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        return next_time
    
    try:
        # 启动时立即生成一次数据
        print("\n📊 启动时立即生成一次Marco数据...")
        generate_latest(quiet_mode=False)
        
        while not should_exit:
            # 计算下一个执行时间
            next_run_time = get_next_30min_timestamp()
            now = datetime.now()
            wait_seconds = (next_run_time - now).total_seconds()
            
            print(f"\n⏰ 下次执行时间: {next_run_time}")
            print(f"⏳ 等待 {wait_seconds/60:.1f} 分钟...")
            logger.info(f"下次Marco数据生成时间: {next_run_time}")
            
            # 等待到下一个执行时间
            while wait_seconds > 0 and not should_exit:
                sleep_time = min(60, wait_seconds)  # 每分钟检查一次退出信号
                time.sleep(sleep_time)
                wait_seconds -= sleep_time
                
                if wait_seconds > 0:
                    print(f"⏳ 还需等待 {wait_seconds/60:.1f} 分钟...")
            
            if should_exit:
                break
                
            # 执行Marco数据生成
            print(f"\n📊 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 开始生成Marco数据...")
            success = generate_latest(quiet_mode=False)
            
            if success:
                print("✅ Marco数据生成完成")
            else:
                print("❌ Marco数据生成失败")
                logger.error("Marco数据生成失败")
    
    except KeyboardInterrupt:
        print("\n📡 接收到中断信号，正在退出...")
    except Exception as e:
        print(f"\n💥 守护进程异常: {e}")
        logger.error(f"守护进程异常: {e}", exc_info=True)
    finally:
        print("🛑 Marco守护进程已退出")
        logger.info("Marco守护进程已退出")


def setup_logging_for_cron(log_file=None):
    """为crontab任务设置特殊的日志配置"""
    # 设置日志
    setup_logger()
    
    # 如果指定了日志文件，添加文件处理器
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            
            # 添加到根日志器
            root_logger = logging.getLogger()
            root_logger.addHandler(file_handler)
            
            print(f"📝 日志将写入文件: {log_file}")
        except Exception as e:
            print(f"⚠️ 设置日志文件失败: {e}")


def parse_arguments():
    """解析命令行参数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Marco数据生成脚本', add_help=False)
    parser.add_argument('command', nargs='?', default='', help='命令')
    parser.add_argument('arg1', nargs='?', help='参数1（日期或结束日期）')
    parser.add_argument('arg2', nargs='?', help='参数2（结束日期）')
    parser.add_argument('--quiet', '-q', action='store_true', help='静默模式')
    parser.add_argument('--log-file', help='指定日志文件路径')
    parser.add_argument('--help', '-h', action='store_true', help='显示帮助')
    
    return parser.parse_args()


def test_connection():
    """测试数据库连接"""
    print("🔧 测试数据库连接...")
    
    try:
        from src.database.connection import db_manager
        
        if db_manager.test_connection():
            print("✅ 数据库连接正常")
            return True
        else:
            print("❌ 数据库连接失败")
            return False
            
    except Exception as e:
        print(f"❌ 连接测试异常: {e}")
        return False


def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 显示帮助
        if args.help:
            print_help()
            return
        
        # 设置日志
        if args.log_file:
            setup_logging_for_cron(args.log_file)
        else:
            setup_logger()
            logging.getLogger().setLevel(logging.INFO)
        
        # 获取命令
        command = args.command.lower() if args.command else ''
        quiet_mode = args.quiet
        
        # 处理不同命令
        if not command or command in ['', 'now']:
            success = generate_latest(quiet_mode=quiet_mode)
            
        elif command == 'daemon':
            # 守护进程模式
            run_daemon_mode()
            return
            
        elif command == 'help':
            print_help()
            return
            
        elif command == 'today':
            success = backfill_days(1)
            
        elif command == 'week':
            success = backfill_days(7)
            
        elif command == 'month':
            success = backfill_days(30)
            
        elif command == 'stats':
            success = show_stats()
            
        elif command == 'test':
            success = test_connection()
            
        elif command.startswith('2'):  # 日期格式 2024-01-01
            if not args.arg1:
                # 单个日期
                success = backfill_date_range(command)
            else:
                # 日期范围
                success = backfill_date_range(command, args.arg1)
                
        else:
            if not quiet_mode:
                print(f"❌ 未知命令: {command}")
                print_help()
            logging.getLogger(__name__).error(f"未知命令: {command}")
            sys.exit(1)
        
        # 根据执行结果设置退出码
        if success:
            if not quiet_mode:
                print("\n🎉 操作完成!")
            sys.exit(0)
        else:
            if not quiet_mode:
                print("\n💥 操作失败!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 程序异常: {e}")
        logging.getLogger(__name__).error(f"程序异常: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 程序异常: {e}")
        sys.exit(1)