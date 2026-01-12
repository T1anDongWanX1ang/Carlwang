#!/usr/bin/env python3
"""
成本数据回填脚本 v2 - 修正版
正确计算每日增量成本，而非累计值
"""
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import pymysql
from collections import defaultdict
import json


class CostDataBackfillerV2:
    """成本数据回填器 v2"""

    def __init__(self):
        self.db_config = {
            'host': '35.215.99.34',
            'port': 13215,
            'user': 'alarm_user',
            'password': 'fdf3rw3983nnfl1f4',
            'database': 'tp_alarm',
            'charset': 'utf8mb4'
        }
        self.project_root = Path(__file__).parent

    def parse_kol_tweet_log_incremental(self, log_file: Path) -> List[Dict[str, Any]]:
        """解析 KOL Tweet 日志 - 按增量计算"""
        print(f"\n📊 解析 KOL Tweet 日志（增量模式）: {log_file}")

        if not log_file.exists():
            print(f"  ⚠️  日志文件不存在")
            return []

        daily_max_cost = {}
        daily_max_tweets = {}
        daily_max_requests = {}

        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if '累计成本:' in line and '累计:' in line:
                    match = re.match(r'^(\d{4}-\d{2}-\d{2})', line)
                    if match:
                        date = match.group(1)

                        # 累计成本
                        cost_match = re.search(r'累计成本:\s*\$([0-9.]+)', line)
                        if cost_match:
                            cost = float(cost_match.group(1))
                            daily_max_cost[date] = max(daily_max_cost.get(date, 0), cost)

                        # 累计推文
                        tweet_match = re.search(r'累计:\s*(\d+)', line)
                        if tweet_match:
                            tweets = int(tweet_match.group(1))
                            daily_max_tweets[date] = max(daily_max_tweets.get(date, 0), tweets)

                        # 请求序号
                        req_match = re.search(r'\[API调用\] 请求 #(\d+)', line)
                        if req_match:
                            requests = int(req_match.group(1))
                            daily_max_requests[date] = max(daily_max_requests.get(date, 0), requests)

        # 计算增量
        records = []
        prev_cost = 0.0
        prev_tweets = 0
        prev_requests = 0

        for date in sorted(daily_max_cost.keys()):
            max_cost = daily_max_cost[date]
            max_tweets = daily_max_tweets.get(date, 0)
            max_requests = daily_max_requests.get(date, 0)

            delta_cost = max_cost - prev_cost
            delta_tweets = max_tweets - prev_tweets
            delta_requests = max_requests - prev_requests

            # 使用该日期的中午12点作为时间戳
            timestamp = datetime.strptime(f"{date} 12:00:00", '%Y-%m-%d %H:%M:%S')
            run_id = f"{date.replace('-', '')}_daily"

            records.append({
                'timestamp': timestamp,
                'run_id': run_id,
                'api_calls': delta_requests,
                'total_cost': delta_cost,
                'tweets': delta_tweets
            })

            prev_cost = max_cost
            prev_tweets = max_tweets
            prev_requests = max_requests

        print(f"  ✓ 提取了 {len(records)} 天的增量记录")
        for r in records:
            print(f"    {r['timestamp'].date()}: ${r['total_cost']:.6f}, {r['tweets']} 条推文, {r['api_calls']} 次请求")

        return records

    def parse_project_tweet_log_accumulated(self, log_file: Path) -> List[Dict[str, Any]]:
        """解析 Project Tweet 日志 - 累加每日所有运行"""
        print(f"\n📊 解析 Project Tweet 日志（累加模式）: {log_file}")

        if not log_file.exists():
            print(f"  ⚠️  日志文件不存在")
            return []

        daily_costs = defaultdict(list)
        daily_tweets = defaultdict(list)

        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.match(r'^(\d{4}-\d{2}-\d{2})', line)
                if match:
                    date = match.group(1)

                    # 本次总成本
                    if '本次总成本:' in line:
                        cost_match = re.search(r'本次总成本:\s*\$([0-9.]+)', line)
                        if cost_match:
                            daily_costs[date].append(float(cost_match.group(1)))

                    # 获取推文数
                    if '获取推文数:' in line:
                        tweet_match = re.search(r'获取推文数:\s*(\d+)', line)
                        if tweet_match:
                            daily_tweets[date].append(int(tweet_match.group(1)))

        # 汇总每日数据
        records = []
        for date in sorted(daily_costs.keys()):
            if daily_costs[date]:
                total_cost = sum(daily_costs[date])
                total_tweets = sum(daily_tweets.get(date, []))
                run_count = len(daily_costs[date])

                # 估算请求次数
                requests = (total_tweets + 99) // 100 if total_tweets > 0 else 0

                timestamp = datetime.strptime(f"{date} 12:00:00", '%Y-%m-%d %H:%M:%S')
                run_id = f"{date.replace('-', '')}_daily"

                records.append({
                    'timestamp': timestamp,
                    'run_id': run_id,
                    'api_calls': requests,
                    'total_cost': total_cost,
                    'tweets': total_tweets,
                    'run_count': run_count
                })

        print(f"  ✓ 提取了 {len(records)} 天的累加记录")
        for r in records:
            print(f"    {r['timestamp'].date()}: ${r['total_cost']:.6f}, {r['tweets']} 条推文, {r.get('run_count', 0)} 次运行")

        return records

    def parse_kol_following_log_v2(self, log_file: Path) -> List[Dict[str, Any]]:
        """解析 KOL Following 日志 v2"""
        print(f"\n📊 解析 KOL Following 日志: {log_file}")

        if not log_file.exists():
            print(f"  ⚠️  日志文件不存在")
            return []

        # 按日期汇总
        daily_data = defaultdict(lambda: {
            'api_calls': 0,
            'followings': 0,
            'success_kols': 0,
            'total_kols': 0,
            'cache_hits': 0
        })

        with open(log_file, 'r', encoding='utf-8') as f:
            current_date = None
            for line in f:
                match = re.match(r'^(\d{4}-\d{2}-\d{2})', line)
                if match:
                    current_date = match.group(1)

                    if 'API调用次数:' in line:
                        api_match = re.search(r'API调用次数:\s*(\d+)', line)
                        if api_match:
                            daily_data[current_date]['api_calls'] += int(api_match.group(1))

                    elif '缓存命中' in line:
                        daily_data[current_date]['cache_hits'] += 1

                    elif '新增入库:' in line:
                        following_match = re.search(r'新增入库:\s*(\d+)', line)
                        if following_match:
                            daily_data[current_date]['followings'] += int(following_match.group(1))

        # 转换为记录
        records = []
        COST_PER_REQUEST = 0.036

        for date in sorted(daily_data.keys()):
            data = daily_data[date]
            if data['api_calls'] > 0 or data['followings'] > 0:
                timestamp = datetime.strptime(f"{date} 12:00:00", '%Y-%m-%d %H:%M:%S')
                run_id = f"{date.replace('-', '')}_daily"

                records.append({
                    'timestamp': timestamp,
                    'run_id': run_id,
                    'api_calls': data['api_calls'],
                    'total_cost': data['api_calls'] * COST_PER_REQUEST,
                    'followings': data['followings'],
                    'cache_hits': data['cache_hits']
                })

        print(f"  ✓ 提取了 {len(records)} 天的记录")
        for r in records:
            print(f"    {r['timestamp'].date()}: ${r['total_cost']:.6f}, {r['followings']} 条Following, {r['api_calls']} 次API")

        return records

    def import_to_database(self, task_name: str, records: List[Dict[str, Any]]) -> int:
        """导入数据到数据库"""
        if not records:
            return 0

        print(f"\n💾 导入 {task_name} 数据到数据库...")

        conn = None
        imported = 0

        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()

            for record in records:
                try:
                    # 检查是否已存在
                    cursor.execute(
                        "SELECT id FROM api_cost_tracking WHERE task_name=%s AND run_id=%s",
                        (task_name, record['run_id'])
                    )

                    if cursor.fetchone():
                        print(f"  ⊘ 跳过已存在: {record['run_id']}")
                        continue

                    total_requests = record.get('api_calls', 0)
                    tweets_fetched = record.get('tweets', record.get('followings', 0))
                    total_cost = record['total_cost']

                    avg_cost_per_request = total_cost / total_requests if total_requests > 0 else 0
                    cost_per_tweet = total_cost / tweets_fetched if tweets_fetched > 0 else 0
                    success_rate = 100.0

                    metadata = {}
                    if 'run_count' in record:
                        metadata['run_count'] = record['run_count']
                    if 'cache_hits' in record:
                        metadata['cache_hits'] = record['cache_hits']

                    metadata_json = json.dumps(metadata) if metadata else None

                    sql = """
                        INSERT INTO api_cost_tracking (
                            timestamp, task_name, run_id,
                            total_requests, tweets_fetched,
                            total_cost_usd, avg_cost_per_request, cost_per_tweet,
                            server_host, success_rate, metadata
                        ) VALUES (
                            %s, %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s, %s, %s
                        )
                    """

                    cursor.execute(sql, (
                        record['timestamp'], task_name, record['run_id'],
                        total_requests, tweets_fetched,
                        total_cost, avg_cost_per_request, cost_per_tweet,
                        'backfill_v2', success_rate, metadata_json
                    ))

                    imported += 1
                    print(f"  ✓ 导入: {record['timestamp'].date()} - ${total_cost:.6f} - {tweets_fetched} 条数据")

                except Exception as e:
                    print(f"  ✗ 导入失败 {record['run_id']}: {e}")
                    continue

            conn.commit()
            cursor.close()

        except Exception as e:
            print(f"  ✗ 数据库错误: {e}")
            if conn:
                conn.rollback()

        finally:
            if conn:
                conn.close()

        return imported

    def backfill_all(self):
        """回填所有数据"""
        print("=" * 70)
        print("🔄 开始回填历史成本数据 (修正版)")
        print("=" * 70)

        total_imported = 0

        # 1. KOL Following
        kol_following_log = self.project_root / 'daily_kol_following_crawler' / 'service_kol_following.log'
        kol_following_records = self.parse_kol_following_log_v2(kol_following_log)
        imported = self.import_to_database('kol_following', kol_following_records)
        total_imported += imported

        # 2. KOL Tweet - 增量模式
        kol_tweet_log = self.project_root / 'daily_kol_tweet_crawler' / 'service_kol_tweet.log'
        kol_tweet_records = self.parse_kol_tweet_log_incremental(kol_tweet_log)
        imported = self.import_to_database('kol_tweet', kol_tweet_records)
        total_imported += imported

        # 3. Project Tweet - 累加模式
        project_tweet_log = self.project_root / 'daily_tweet_crawler' / 'service_project_twitterapi.log'
        project_tweet_records = self.parse_project_tweet_log_accumulated(project_tweet_log)
        imported = self.import_to_database('project_tweet', project_tweet_records)
        total_imported += imported

        print("\n" + "=" * 70)
        print(f"✅ 回填完成！总共导入 {total_imported} 条记录")
        print("=" * 70)

        self.show_statistics()

    def show_statistics(self):
        """显示统计信息"""
        print("\n📊 数据库统计:")

        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    DATE(timestamp) as date,
                    task_name,
                    total_cost_usd,
                    tweets_fetched
                FROM api_cost_tracking
                WHERE server_host LIKE 'backfill%'
                ORDER BY date, task_name
            """)

            print(f"\n{'日期':<15} {'任务':<18} {'成本':<15} {'数据量'}")
            print("-" * 70)

            for row in cursor.fetchall():
                print(f"{str(row[0]):<15} {row[1]:<18} ${row[2]:<14.6f} {row[3]}")

            # 每日总计
            cursor.execute("""
                SELECT
                    DATE(timestamp) as date,
                    SUM(total_cost_usd) as daily_cost
                FROM api_cost_tracking
                WHERE server_host LIKE 'backfill%'
                GROUP BY DATE(timestamp)
                ORDER BY date
            """)

            print(f"\n{'日期':<15} {'每日总成本'}")
            print("-" * 40)

            for row in cursor.fetchall():
                print(f"{str(row[0]):<15} ${row[1]:.6f}")

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"  ✗ 查询统计失败: {e}")


def main():
    backfiller = CostDataBackfillerV2()
    backfiller.backfill_all()


if __name__ == '__main__':
    main()
