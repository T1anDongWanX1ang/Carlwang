#!/usr/bin/env python3
"""
TwitterAPI.io 成本统计脚本
用于分析日志文件中的API调用成本

使用方法:
    python api_cost_stats.py                    # 分析今天的日志
    python api_cost_stats.py --days 7           # 分析最近7天的日志
    python api_cost_stats.py --log-file custom.log  # 分析指定日志文件
"""

import re
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


class APICostAnalyzer:
    """API成本分析器"""

    def __init__(self):
        self.cost_per_1000_tweets = 0.15  # $0.15 per 1,000 tweets

    def parse_log_file(self, log_file: Path) -> dict:
        """解析日志文件，提取成本信息"""
        stats = {
            'total_requests': 0,
            'total_tweets': 0,
            'total_cost': 0.0,
            'sessions': [],  # 每次运行的统计
            'hourly_cost': defaultdict(float),  # 每小时的成本
            'daily_cost': defaultdict(float),   # 每天的成本
        }

        if not log_file.exists():
            print(f"⚠️  日志文件不存在: {log_file}")
            return stats

        # 正则表达式匹配成本日志
        # 格式: 本次成本: $0.000120 | 累计成本: $0.013500
        cost_pattern = re.compile(r'本次成本: \$([0-9.]+).*累计成本: \$([0-9.]+)')

        # 匹配最终统计
        # 格式: 本次总成本: $0.013500 USD
        total_cost_pattern = re.compile(r'本次总成本: \$([0-9.]+) USD')
        requests_pattern = re.compile(r'总请求次数: (\d+)')
        tweets_pattern = re.compile(r'获取推文数: (\d+)')

        current_session = None

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    # 提取时间戳
                    timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if timestamp_match:
                        timestamp_str = timestamp_match.group(1)
                        try:
                            dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            hour_key = dt.strftime('%Y-%m-%d %H:00')
                            day_key = dt.strftime('%Y-%m-%d')
                        except:
                            continue

                    # 检测新的爬取会话开始
                    if '开始爬取项目推文数据' in line or '开始单次项目推文数据爬取' in line:
                        if current_session:
                            stats['sessions'].append(current_session)
                        current_session = {
                            'start_time': timestamp_str if timestamp_match else 'Unknown',
                            'requests': 0,
                            'tweets': 0,
                            'cost': 0.0,
                        }

                    # 提取成本信息
                    cost_match = cost_pattern.search(line)
                    if cost_match:
                        request_cost = float(cost_match.group(1))
                        cumulative_cost = float(cost_match.group(2))

                        if timestamp_match:
                            stats['hourly_cost'][hour_key] += request_cost
                            stats['daily_cost'][day_key] += request_cost

                    # 提取会话统计
                    if current_session:
                        total_match = total_cost_pattern.search(line)
                        if total_match:
                            current_session['cost'] = float(total_match.group(1))

                        req_match = requests_pattern.search(line)
                        if req_match:
                            current_session['requests'] = int(req_match.group(1))

                        tweet_match = tweets_pattern.search(line)
                        if tweet_match:
                            current_session['tweets'] = int(tweet_match.group(1))

                # 保存最后一个会话
                if current_session:
                    stats['sessions'].append(current_session)

        except Exception as e:
            print(f"⚠️  解析日志文件时出错: {e}")

        # 汇总统计
        for session in stats['sessions']:
            stats['total_requests'] += session['requests']
            stats['total_tweets'] += session['tweets']
            stats['total_cost'] += session['cost']

        return stats

    def print_stats(self, stats: dict, log_file: Path):
        """打印统计信息"""
        print("=" * 60)
        print("💰 TwitterAPI.io 成本统计报告")
        print("=" * 60)
        print(f"📄 日志文件: {log_file}")
        print(f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        if stats['total_cost'] == 0:
            print("⚠️  未找到成本记录，可能日志文件为空或格式不匹配")
            return

        # 总体统计
        print("📊 总体统计")
        print("-" * 60)
        print(f"  总爬取次数: {len(stats['sessions'])} 次")
        print(f"  总请求次数: {stats['total_requests']} 次")
        print(f"  总推文数: {stats['total_tweets']} 条")
        print(f"  总成本: ${stats['total_cost']:.6f} USD")
        if stats['total_requests'] > 0:
            print(f"  平均每次请求成本: ${stats['total_cost'] / stats['total_requests']:.6f} USD")
        if stats['total_tweets'] > 0:
            print(f"  平均每条推文成本: ${stats['total_cost'] / stats['total_tweets']:.6f} USD")
        print()

        # 每日成本
        if stats['daily_cost']:
            print("📅 每日成本")
            print("-" * 60)
            for day in sorted(stats['daily_cost'].keys(), reverse=True):
                print(f"  {day}: ${stats['daily_cost'][day]:.6f} USD")
            print()

        # 最近的爬取会话
        if stats['sessions']:
            print("🕒 最近的爬取会话 (最多显示10次)")
            print("-" * 60)
            for i, session in enumerate(reversed(stats['sessions'][-10:]), 1):
                print(f"  {i}. {session['start_time']}")
                print(f"     请求: {session['requests']} 次 | 推文: {session['tweets']} 条 | 成本: ${session['cost']:.6f} USD")
            print()

        # 成本预估
        print("💡 成本预估")
        print("-" * 60)
        if len(stats['sessions']) > 0:
            avg_cost_per_session = stats['total_cost'] / len(stats['sessions'])
            print(f"  平均每次爬取成本: ${avg_cost_per_session:.6f} USD")

            # 如果是定时任务，预估每月成本
            # 假设每15分钟运行一次（默认配置）
            sessions_per_day = 24 * 60 / 15  # 96次/天
            daily_cost_estimate = avg_cost_per_session * sessions_per_day
            monthly_cost_estimate = daily_cost_estimate * 30

            print(f"  预估每日成本 (每15分钟运行): ${daily_cost_estimate:.4f} USD")
            print(f"  预估每月成本 (每15分钟运行): ${monthly_cost_estimate:.4f} USD")
        print()

        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='TwitterAPI.io 成本统计分析工具')
    parser.add_argument('--log-file', type=str,
                       help='指定日志文件路径（默认使用最新的service_project_twitterapi.log）')
    parser.add_argument('--days', type=int, default=1,
                       help='分析最近N天的日志（默认1天，仅当日志文件使用日期后缀时有效）')

    args = parser.parse_args()

    analyzer = APICostAnalyzer()

    # 确定日志文件
    if args.log_file:
        log_file = Path(args.log_file)
    else:
        # 默认使用服务脚本的日志文件
        script_dir = Path(__file__).parent / 'service_scripts'
        log_file = script_dir / 'service_project_twitterapi.log'

        # 如果服务脚本日志不存在，尝试主日志
        if not log_file.exists():
            log_file = Path(__file__).parent / 'logs' / 'twitter_crawler.log'

    # 解析并打印统计
    stats = analyzer.parse_log_file(log_file)
    analyzer.print_stats(stats, log_file)

    # 如果指定了天数且大于1，尝试合并多个日志文件
    if args.days > 1 and not args.log_file:
        print(f"\n💡 提示: 合并多日志分析功能开发中...")


if __name__ == '__main__':
    main()
