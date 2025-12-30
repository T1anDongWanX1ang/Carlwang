#!/usr/bin/env python3
"""
实时监控数据库入库进度
"""
import time
import sys
from pathlib import Path

# 添加父目录到路径
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from src.database.connection import db_manager
from datetime import datetime

def get_save_progress():
    """从日志文件中获取保存进度"""
    log_file = Path(__file__).parent / 'logs' / 'twitter_crawler.log'

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 倒序查找最近的保存进度
        for line in reversed(lines[-200:]):  # 只看最后200行
            if '开始保存' in line and '推文到数据库' in line:
                # 提取推文数量
                import re
                match = re.search(r'开始保存 (\d+) 条推文', line)
                if match:
                    total = int(match.group(1))
                    timestamp = line.split(' - ')[0]
                    return {
                        'status': 'saving_tweets',
                        'total': total,
                        'timestamp': timestamp
                    }

            if '批量upsert推文成功' in line:
                import re
                match = re.search(r'批量upsert推文成功: (\d+)/(\d+)', line)
                if match:
                    saved = int(match.group(1))
                    total = int(match.group(2))
                    timestamp = line.split(' - ')[0]
                    return {
                        'status': 'tweet_saved',
                        'saved': saved,
                        'total': total,
                        'timestamp': timestamp
                    }

            if '开始保存' in line and '用户到数据库' in line:
                import re
                match = re.search(r'开始保存 (\d+) 条用户', line)
                if match:
                    total = int(match.group(1))
                    timestamp = line.split(' - ')[0]
                    return {
                        'status': 'saving_users',
                        'total': total,
                        'timestamp': timestamp
                    }

        return {'status': 'unknown'}

    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def get_db_stats(target_date='2025-12-22'):
    """获取数据库中的统计信息"""
    try:
        with db_manager.get_cursor() as (conn, cursor):
            # 查询指定日期之后的推文数量
            query = """
            SELECT
                COUNT(*) as total_tweets,
                COUNT(DISTINCT author_id) as unique_users,
                MIN(created_at) as earliest_tweet,
                MAX(created_at) as latest_tweet
            FROM twitter_tweet_back_test_cmc300
            WHERE created_at >= %s
            """

            cursor.execute(query, (target_date,))
            result = cursor.fetchone()

            return {
                'total_tweets': result[0] if result else 0,
                'unique_users': result[1] if result else 0,
                'earliest_tweet': result[2] if result else None,
                'latest_tweet': result[3] if result else None
            }

    except Exception as e:
        return {'error': str(e)}

def monitor_loop():
    """监控循环"""
    print("\n" + "="*60)
    print("  📊 数据库入库进度监控")
    print("="*60)
    print("\n按 Ctrl+C 停止监控\n")

    try:
        while True:
            # 清屏
            print("\033[2J\033[H", end='')

            print("="*60)
            print(f"  ⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*60)

            # 获取日志进度
            progress = get_save_progress()

            print("\n📝 日志状态:")
            if progress['status'] == 'saving_tweets':
                print(f"   🔄 正在保存推文: {progress['total']} 条")
                print(f"   🕐 开始时间: {progress['timestamp']}")
            elif progress['status'] == 'tweet_saved':
                print(f"   ✅ 推文保存完成: {progress['saved']}/{progress['total']}")
                print(f"   🕐 完成时间: {progress['timestamp']}")
            elif progress['status'] == 'saving_users':
                print(f"   🔄 正在保存用户: {progress['total']} 条")
                print(f"   🕐 开始时间: {progress['timestamp']}")
            else:
                print(f"   ❓ 状态未知")

            # 获取数据库统计
            print("\n💾 数据库统计 (2025-12-22之后):")
            stats = get_db_stats()

            if 'error' in stats:
                print(f"   ❌ 查询失败: {stats['error']}")
            else:
                print(f"   📝 总推文数: {stats['total_tweets']:,}")
                print(f"   👥 唯一用户: {stats['unique_users']:,}")
                if stats['earliest_tweet']:
                    print(f"   📅 最早推文: {stats['earliest_tweet']}")
                if stats['latest_tweet']:
                    print(f"   📅 最新推文: {stats['latest_tweet']}")

            print("\n" + "="*60)
            print("  下次更新: 10秒后...")
            print("="*60)

            time.sleep(10)

    except KeyboardInterrupt:
        print("\n\n✅ 监控已停止\n")

if __name__ == '__main__':
    monitor_loop()
