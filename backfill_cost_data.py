#!/usr/bin/env python3
"""
成本数据回填脚本
从日志文件中提取历史成本数据并导入到数据库
"""
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import pymysql
from collections import defaultdict


class CostDataBackfiller:
    """成本数据回填器"""

    def __init__(self):
        """初始化"""
        self.db_config = {
            'host': '35.215.99.34',
            'port': 13215,
            'user': 'alarm_user',
            'password': 'fdf3rw3983nnfl1f4',
            'database': 'tp_alarm',
            'charset': 'utf8mb4'
        }
        self.project_root = Path(__file__).parent
        self.records = []

    def parse_kol_following_log(self, log_file: Path) -> List[Dict[str, Any]]:
        """解析 KOL Following 日志"""
        print(f"\n📊 解析 KOL Following 日志: {log_file}")

        if not log_file.exists():
            print(f"  ⚠️  日志文件不存在")
            return []

        records = []
        current_run = None

        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # 匹配运行开始
                if '开始执行 KOL Following 爬取' in line:
                    if current_run:
                        records.append(current_run)

                    # 提取时间戳
                    match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if match:
                        timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                        run_id = timestamp.strftime('%Y%m%d_%H%M%S')
                        current_run = {
                            'timestamp': timestamp,
                            'run_id': run_id,
                            'api_calls': 0,
                            'cache_hits': 0,
                            'total_cost': 0.0,
                            'followings': 0,
                            'success_kols': 0,
                            'total_kols': 0
                        }

                if current_run:
                    # 提取统计数据
                    if 'API调用次数:' in line:
                        match = re.search(r'API调用次数:\s*(\d+)', line)
                        if match:
                            current_run['api_calls'] = int(match.group(1))

                    elif '缓存命中' in line:
                        current_run['cache_hits'] += 1

                    elif '新增入库:' in line:
                        match = re.search(r'新增入库:\s*(\d+)', line)
                        if match:
                            current_run['followings'] += int(match.group(1))

                    elif '成功:' in line and '跳过' not in line:
                        match = re.search(r'成功:\s*(\d+)', line)
                        if match:
                            current_run['success_kols'] = int(match.group(1))

                    elif '已处理:' in line:
                        match = re.search(r'已处理:\s*(\d+)', line)
                        if match:
                            current_run['total_kols'] = int(match.group(1))

        # 添加最后一次运行
        if current_run:
            records.append(current_run)

        # 计算成本（TwitterAPI following 端点：$0.036 per request）
        COST_PER_REQUEST = 0.036
        for record in records:
            record['total_cost'] = record['api_calls'] * COST_PER_REQUEST

        print(f"  ✓ 提取了 {len(records)} 条运行记录")
        return records

    def parse_kol_tweet_log(self, log_file: Path) -> List[Dict[str, Any]]:
        """解析 KOL Tweet 日志"""
        print(f"\n📊 解析 KOL Tweet 日志: {log_file}")

        if not log_file.exists():
            print(f"  ⚠️  日志文件不存在")
            return []

        # 按日期聚合数据
        daily_data = defaultdict(lambda: {
            'timestamps': [],
            'max_requests': 0,
            'max_cost': 0.0,
            'max_tweets': 0
        })

        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # 提取累计成本和累计推文数
                if '累计成本:' in line and '累计:' in line:
                    # 2025-12-31 16:37:32 - ... - 获取 20 条推文 (累计: 39623) | 本次成本: $0.003000 | 累计成本: $5.943450
                    match = re.match(r'^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})', line)
                    if match:
                        date_str = match.group(1)
                        time_str = match.group(2)
                        timestamp = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M:%S')

                        # 提取累计推文数
                        tweet_match = re.search(r'累计:\s*(\d+)', line)
                        if tweet_match:
                            tweets = int(tweet_match.group(1))

                        # 提取累计成本
                        cost_match = re.search(r'累计成本:\s*\$([0-9.]+)', line)
                        if cost_match:
                            cost = float(cost_match.group(1))

                        # 提取请求序号
                        req_match = re.search(r'\[API调用\] 请求 #(\d+)', line)
                        if req_match:
                            requests = int(req_match.group(1))
                        else:
                            # 估算请求次数（每次$0.003）
                            requests = int(cost / 0.003) if cost > 0 else 0

                        daily_data[date_str]['timestamps'].append(timestamp)
                        daily_data[date_str]['max_requests'] = max(daily_data[date_str]['max_requests'], requests)
                        daily_data[date_str]['max_cost'] = max(daily_data[date_str]['max_cost'], cost)
                        daily_data[date_str]['max_tweets'] = max(daily_data[date_str]['max_tweets'], tweets)

        # 转换为记录列表
        records = []
        for date_str, data in sorted(daily_data.items()):
            if data['timestamps']:
                # 使用该日期的第一个时间戳
                timestamp = min(data['timestamps'])
                run_id = f"{date_str.replace('-', '')}_daily"

                records.append({
                    'timestamp': timestamp,
                    'run_id': run_id,
                    'api_calls': data['max_requests'],
                    'total_cost': data['max_cost'],
                    'tweets': data['max_tweets']
                })

        print(f"  ✓ 提取了 {len(records)} 条每日记录")
        return records

    def parse_project_tweet_log(self, log_file: Path) -> List[Dict[str, Any]]:
        """解析 Project Tweet 日志"""
        print(f"\n📊 解析 Project Tweet 日志: {log_file}")

        if not log_file.exists():
            print(f"  ⚠️  日志文件不存在")
            return []

        # 按日期聚合数据
        daily_data = defaultdict(lambda: {
            'timestamps': [],
            'max_cost': 0.0,
            'max_tweets': 0
        })

        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # 提取成本信息
                if '本次总成本:' in line:
                    # 2025-12-31 00:00:00 - ... - 本次总成本: $1.234567
                    match = re.match(r'^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})', line)
                    if match:
                        date_str = match.group(1)
                        time_str = match.group(2)
                        timestamp = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M:%S')

                        # 提取成本
                        cost_match = re.search(r'本次总成本:\s*\$([0-9.]+)', line)
                        if cost_match:
                            cost = float(cost_match.group(1))
                            daily_data[date_str]['timestamps'].append(timestamp)
                            daily_data[date_str]['max_cost'] = max(daily_data[date_str]['max_cost'], cost)

                # 提取推文数
                elif '获取推文数:' in line:
                    match = re.match(r'^(\d{4}-\d{2}-\d{2})', line)
                    if match:
                        date_str = match.group(1)
                        tweet_match = re.search(r'获取推文数:\s*(\d+)', line)
                        if tweet_match:
                            tweets = int(tweet_match.group(1))
                            daily_data[date_str]['max_tweets'] = max(daily_data[date_str]['max_tweets'], tweets)

        # 转换为记录列表
        records = []
        for date_str, data in sorted(daily_data.items()):
            if data['timestamps'] and data['max_cost'] > 0:
                timestamp = min(data['timestamps'])
                run_id = f"{date_str.replace('-', '')}_daily"

                # 估算请求次数（假设每页100条推文，每次请求一页）
                requests = (data['max_tweets'] + 99) // 100 if data['max_tweets'] > 0 else 0

                records.append({
                    'timestamp': timestamp,
                    'run_id': run_id,
                    'api_calls': requests,
                    'total_cost': data['max_cost'],
                    'tweets': data['max_tweets']
                })

        print(f"  ✓ 提取了 {len(records)} 条每日记录")
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

                    # 计算衍生指标
                    total_requests = record.get('api_calls', 0)
                    tweets_fetched = record.get('tweets', record.get('followings', 0))
                    total_cost = record['total_cost']

                    avg_cost_per_request = total_cost / total_requests if total_requests > 0 else 0
                    cost_per_tweet = total_cost / tweets_fetched if tweets_fetched > 0 else 0
                    success_rate = 100.0  # 默认100%

                    # 构建元数据
                    metadata = {}
                    if 'success_kols' in record:
                        metadata['success_kols'] = record['success_kols']
                    if 'total_kols' in record:
                        metadata['total_kols'] = record['total_kols']
                    if 'cache_hits' in record:
                        metadata['cache_hits'] = record['cache_hits']

                    import json
                    metadata_json = json.dumps(metadata) if metadata else None

                    # 插入数据
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
                        'backfill', success_rate, metadata_json
                    ))

                    imported += 1
                    print(f"  ✓ 导入: {record['timestamp']} - ${total_cost:.6f} - {tweets_fetched} 条数据")

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
        print("🔄 开始回填历史成本数据")
        print("=" * 70)

        total_imported = 0

        # 1. KOL Following
        kol_following_log = self.project_root / 'daily_kol_following_crawler' / 'service_kol_following.log'
        kol_following_records = self.parse_kol_following_log(kol_following_log)
        imported = self.import_to_database('kol_following', kol_following_records)
        total_imported += imported

        # 2. KOL Tweet
        kol_tweet_log = self.project_root / 'daily_kol_tweet_crawler' / 'service_kol_tweet.log'
        kol_tweet_records = self.parse_kol_tweet_log(kol_tweet_log)
        imported = self.import_to_database('kol_tweet', kol_tweet_records)
        total_imported += imported

        # 3. Project Tweet
        project_tweet_log = self.project_root / 'daily_tweet_crawler' / 'service_project_twitterapi.log'
        project_tweet_records = self.parse_project_tweet_log(project_tweet_log)
        imported = self.import_to_database('project_tweet', project_tweet_records)
        total_imported += imported

        print("\n" + "=" * 70)
        print(f"✅ 回填完成！总共导入 {total_imported} 条记录")
        print("=" * 70)

        # 显示统计
        self.show_statistics()

    def show_statistics(self):
        """显示统计信息"""
        print("\n📊 数据库统计:")

        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    task_name,
                    COUNT(*) as record_count,
                    MIN(timestamp) as earliest,
                    MAX(timestamp) as latest,
                    SUM(total_cost_usd) as total_cost
                FROM api_cost_tracking
                GROUP BY task_name
                ORDER BY task_name
            """)

            print(f"\n{'任务名称':<20} {'记录数':<10} {'最早时间':<20} {'最晚时间':<20} {'总成本'}")
            print("-" * 100)

            for row in cursor.fetchall():
                print(f"{row[0]:<20} {row[1]:<10} {str(row[2]):<20} {str(row[3]):<20} ${row[4]:.6f}")

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"  ✗ 查询统计失败: {e}")


def main():
    """主函数"""
    backfiller = CostDataBackfiller()
    backfiller.backfill_all()


if __name__ == '__main__':
    main()
