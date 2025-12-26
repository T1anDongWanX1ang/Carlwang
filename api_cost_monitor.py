#!/usr/bin/env python3
"""
Twitter API 调用成本实时监控工具
用于精确追踪和计算 API 请求次数及成本
"""
import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger


class APICostMonitor:
    """API 成本监控器"""

    # 成本配置（根据你的实际 API 定价调整）
    COST_CONFIG = {
        'twitterapi': {
            'per_request': 0.001,  # 每次请求成本（美元）
            'per_100_tweets': 0.01,  # 每100条推文成本（美元）
            'daily_free_requests': 0,  # 每日免费请求数
            'monthly_quota': 10000,  # 月度配额（请求数）
        },
        # 可以添加其他 API 的成本配置
        'chatgpt': {
            'per_1k_tokens_input': 0.003,  # GPT-4 输入成本
            'per_1k_tokens_output': 0.006,  # GPT-4 输出成本
        }
    }

    def __init__(self, stats_file: str = None):
        self.logger = get_logger(__name__)

        # 统计文件路径
        if stats_file:
            self.stats_file = Path(stats_file)
        else:
            self.stats_file = project_root / 'logs' / 'api_stats.json'

        self.stats_file.parent.mkdir(parents=True, exist_ok=True)

        # 加载历史统计
        self.stats = self._load_stats()

    def _load_stats(self) -> Dict[str, Any]:
        """加载历史统计数据"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"加载统计文件失败: {e}")

        return {
            'twitter_api': {
                'total_requests': 0,
                'total_tweets': 0,
                'error_count': 0,
                'daily_stats': {},
                'monthly_stats': {},
            },
            'chatgpt_api': {
                'total_requests': 0,
                'total_input_tokens': 0,
                'total_output_tokens': 0,
                'daily_stats': {},
            },
            'last_updated': datetime.now().isoformat()
        }

    def _save_stats(self):
        """保存统计数据"""
        try:
            self.stats['last_updated'] = datetime.now().isoformat()
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存统计文件失败: {e}")

    def record_twitter_request(self, tweets_count: int = 0, success: bool = True):
        """记录 Twitter API 请求"""
        today = datetime.now().strftime('%Y-%m-%d')
        month = datetime.now().strftime('%Y-%m')

        twitter_stats = self.stats['twitter_api']

        # 更新总计
        twitter_stats['total_requests'] += 1
        if success:
            twitter_stats['total_tweets'] += tweets_count
        else:
            twitter_stats['error_count'] += 1

        # 更新日统计
        if today not in twitter_stats['daily_stats']:
            twitter_stats['daily_stats'][today] = {
                'requests': 0,
                'tweets': 0,
                'errors': 0
            }

        twitter_stats['daily_stats'][today]['requests'] += 1
        if success:
            twitter_stats['daily_stats'][today]['tweets'] += tweets_count
        else:
            twitter_stats['daily_stats'][today]['errors'] += 1

        # 更新月统计
        if month not in twitter_stats['monthly_stats']:
            twitter_stats['monthly_stats'][month] = {
                'requests': 0,
                'tweets': 0,
                'errors': 0
            }

        twitter_stats['monthly_stats'][month]['requests'] += 1
        if success:
            twitter_stats['monthly_stats'][month]['tweets'] += tweets_count
        else:
            twitter_stats['monthly_stats'][month]['errors'] += 1

        self._save_stats()

    def record_chatgpt_request(self, input_tokens: int = 0, output_tokens: int = 0):
        """记录 ChatGPT API 请求"""
        today = datetime.now().strftime('%Y-%m-%d')

        chatgpt_stats = self.stats['chatgpt_api']

        # 更新总计
        chatgpt_stats['total_requests'] += 1
        chatgpt_stats['total_input_tokens'] += input_tokens
        chatgpt_stats['total_output_tokens'] += output_tokens

        # 更新日统计
        if today not in chatgpt_stats['daily_stats']:
            chatgpt_stats['daily_stats'][today] = {
                'requests': 0,
                'input_tokens': 0,
                'output_tokens': 0
            }

        chatgpt_stats['daily_stats'][today]['requests'] += 1
        chatgpt_stats['daily_stats'][today]['input_tokens'] += input_tokens
        chatgpt_stats['daily_stats'][today]['output_tokens'] += output_tokens

        self._save_stats()

    def calculate_costs(self) -> Dict[str, Any]:
        """计算成本"""
        twitter_stats = self.stats['twitter_api']
        chatgpt_stats = self.stats['chatgpt_api']

        # Twitter API 成本
        twitter_cost = (
            twitter_stats['total_requests'] * self.COST_CONFIG['twitterapi']['per_request'] +
            (twitter_stats['total_tweets'] / 100) * self.COST_CONFIG['twitterapi']['per_100_tweets']
        )

        # ChatGPT API 成本
        chatgpt_cost = (
            (chatgpt_stats['total_input_tokens'] / 1000) * self.COST_CONFIG['chatgpt']['per_1k_tokens_input'] +
            (chatgpt_stats['total_output_tokens'] / 1000) * self.COST_CONFIG['chatgpt']['per_1k_tokens_output']
        )

        return {
            'twitter_api': {
                'total_cost': twitter_cost,
                'requests': twitter_stats['total_requests'],
                'tweets': twitter_stats['total_tweets'],
                'errors': twitter_stats['error_count'],
                'avg_cost_per_request': twitter_cost / max(twitter_stats['total_requests'], 1)
            },
            'chatgpt_api': {
                'total_cost': chatgpt_cost,
                'requests': chatgpt_stats['total_requests'],
                'input_tokens': chatgpt_stats['total_input_tokens'],
                'output_tokens': chatgpt_stats['total_output_tokens'],
                'avg_cost_per_request': chatgpt_cost / max(chatgpt_stats['total_requests'], 1)
            },
            'total_cost': twitter_cost + chatgpt_cost
        }

    def get_today_stats(self) -> Dict[str, Any]:
        """获取今日统计"""
        today = datetime.now().strftime('%Y-%m-%d')

        twitter_today = self.stats['twitter_api']['daily_stats'].get(today, {
            'requests': 0, 'tweets': 0, 'errors': 0
        })

        chatgpt_today = self.stats['chatgpt_api']['daily_stats'].get(today, {
            'requests': 0, 'input_tokens': 0, 'output_tokens': 0
        })

        # 计算今日成本
        twitter_cost_today = (
            twitter_today['requests'] * self.COST_CONFIG['twitterapi']['per_request'] +
            (twitter_today['tweets'] / 100) * self.COST_CONFIG['twitterapi']['per_100_tweets']
        )

        chatgpt_cost_today = (
            (chatgpt_today['input_tokens'] / 1000) * self.COST_CONFIG['chatgpt']['per_1k_tokens_input'] +
            (chatgpt_today['output_tokens'] / 1000) * self.COST_CONFIG['chatgpt']['per_1k_tokens_output']
        )

        return {
            'date': today,
            'twitter_api': {
                **twitter_today,
                'cost': twitter_cost_today
            },
            'chatgpt_api': {
                **chatgpt_today,
                'cost': chatgpt_cost_today
            },
            'total_cost': twitter_cost_today + chatgpt_cost_today
        }

    def get_monthly_stats(self) -> Dict[str, Any]:
        """获取本月统计"""
        month = datetime.now().strftime('%Y-%m')

        twitter_month = self.stats['twitter_api']['monthly_stats'].get(month, {
            'requests': 0, 'tweets': 0, 'errors': 0
        })

        # 计算本月成本
        twitter_cost_month = (
            twitter_month['requests'] * self.COST_CONFIG['twitterapi']['per_request'] +
            (twitter_month['tweets'] / 100) * self.COST_CONFIG['twitterapi']['per_100_tweets']
        )

        # ChatGPT 本月统计（汇总所有当月的日统计）
        chatgpt_month_total = {'requests': 0, 'input_tokens': 0, 'output_tokens': 0}
        for date, stats in self.stats['chatgpt_api']['daily_stats'].items():
            if date.startswith(month):
                chatgpt_month_total['requests'] += stats['requests']
                chatgpt_month_total['input_tokens'] += stats['input_tokens']
                chatgpt_month_total['output_tokens'] += stats['output_tokens']

        chatgpt_cost_month = (
            (chatgpt_month_total['input_tokens'] / 1000) * self.COST_CONFIG['chatgpt']['per_1k_tokens_input'] +
            (chatgpt_month_total['output_tokens'] / 1000) * self.COST_CONFIG['chatgpt']['per_1k_tokens_output']
        )

        # 计算配额使用率
        quota_usage = (twitter_month['requests'] / self.COST_CONFIG['twitterapi']['monthly_quota']) * 100

        return {
            'month': month,
            'twitter_api': {
                **twitter_month,
                'cost': twitter_cost_month,
                'quota_usage_percent': quota_usage
            },
            'chatgpt_api': {
                **chatgpt_month_total,
                'cost': chatgpt_cost_month
            },
            'total_cost': twitter_cost_month + chatgpt_cost_month
        }

    def print_report(self, mode: str = 'all'):
        """打印报告"""
        print("\n" + "=" * 70)
        print("Twitter API 成本监控报告")
        print("=" * 70)

        if mode in ['all', 'today']:
            today_stats = self.get_today_stats()
            print(f"\n📅 今日统计 ({today_stats['date']})")
            print("-" * 70)
            print(f"Twitter API:")
            print(f"  请求次数: {today_stats['twitter_api']['requests']}")
            print(f"  推文数量: {today_stats['twitter_api']['tweets']}")
            print(f"  错误次数: {today_stats['twitter_api']['errors']}")
            print(f"  成本: ${today_stats['twitter_api']['cost']:.4f}")
            print(f"\nChatGPT API:")
            print(f"  请求次数: {today_stats['chatgpt_api']['requests']}")
            print(f"  输入 tokens: {today_stats['chatgpt_api']['input_tokens']:,}")
            print(f"  输出 tokens: {today_stats['chatgpt_api']['output_tokens']:,}")
            print(f"  成本: ${today_stats['chatgpt_api']['cost']:.4f}")
            print(f"\n💰 今日总成本: ${today_stats['total_cost']:.4f}")

        if mode in ['all', 'month']:
            month_stats = self.get_monthly_stats()
            print(f"\n📊 本月统计 ({month_stats['month']})")
            print("-" * 70)
            print(f"Twitter API:")
            print(f"  请求次数: {month_stats['twitter_api']['requests']}")
            print(f"  推文数量: {month_stats['twitter_api']['tweets']}")
            print(f"  错误次数: {month_stats['twitter_api']['errors']}")
            print(f"  配额使用: {month_stats['twitter_api']['quota_usage_percent']:.2f}%")
            print(f"  成本: ${month_stats['twitter_api']['cost']:.4f}")
            print(f"\nChatGPT API:")
            print(f"  请求次数: {month_stats['chatgpt_api']['requests']}")
            print(f"  输入 tokens: {month_stats['chatgpt_api']['input_tokens']:,}")
            print(f"  输出 tokens: {month_stats['chatgpt_api']['output_tokens']:,}")
            print(f"  成本: ${month_stats['chatgpt_api']['cost']:.4f}")
            print(f"\n💰 本月总成本: ${month_stats['total_cost']:.4f}")

        if mode in ['all', 'total']:
            total_costs = self.calculate_costs()
            print(f"\n📈 累计统计")
            print("-" * 70)
            print(f"Twitter API:")
            print(f"  请求次数: {total_costs['twitter_api']['requests']}")
            print(f"  推文数量: {total_costs['twitter_api']['tweets']}")
            print(f"  错误次数: {total_costs['twitter_api']['errors']}")
            print(f"  累计成本: ${total_costs['twitter_api']['total_cost']:.4f}")
            print(f"  平均每次请求: ${total_costs['twitter_api']['avg_cost_per_request']:.6f}")
            print(f"\nChatGPT API:")
            print(f"  请求次数: {total_costs['chatgpt_api']['requests']}")
            print(f"  输入 tokens: {total_costs['chatgpt_api']['input_tokens']:,}")
            print(f"  输出 tokens: {total_costs['chatgpt_api']['output_tokens']:,}")
            print(f"  累计成本: ${total_costs['chatgpt_api']['total_cost']:.4f}")
            print(f"  平均每次请求: ${total_costs['chatgpt_api']['avg_cost_per_request']:.6f}")
            print(f"\n💰 总累计成本: ${total_costs['total_cost']:.4f}")

        print("\n" + "=" * 70)
        print(f"更新时间: {self.stats['last_updated']}")
        print("=" * 70 + "\n")

    def watch_mode(self, interval: int = 5):
        """实时监控模式"""
        print("进入实时监控模式，按 Ctrl+C 退出...")
        print(f"刷新间隔: {interval} 秒\n")

        try:
            last_requests = self.stats['twitter_api']['total_requests']

            while True:
                # 清屏
                os.system('clear' if os.name != 'nt' else 'cls')

                # 重新加载统计
                self.stats = self._load_stats()

                # 显示报告
                self.print_report('today')

                # 显示增量
                current_requests = self.stats['twitter_api']['total_requests']
                if current_requests > last_requests:
                    print(f"⚡ 新增 {current_requests - last_requests} 次请求")
                    last_requests = current_requests

                print(f"\n下次刷新: {interval} 秒后 (按 Ctrl+C 退出)")

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n退出实时监控模式")


def main():
    parser = argparse.ArgumentParser(description='Twitter API 成本监控工具')
    parser.add_argument('--mode', choices=['report', 'watch', 'reset'], default='report',
                       help='运行模式: report=显示报告, watch=实时监控, reset=重置统计')
    parser.add_argument('--report-type', choices=['all', 'today', 'month', 'total'], default='all',
                       help='报告类型')
    parser.add_argument('--interval', type=int, default=5,
                       help='实时监控刷新间隔（秒）')
    parser.add_argument('--stats-file', type=str,
                       help='统计文件路径')

    args = parser.parse_args()

    monitor = APICostMonitor(stats_file=args.stats_file)

    if args.mode == 'report':
        monitor.print_report(mode=args.report_type)
    elif args.mode == 'watch':
        monitor.watch_mode(interval=args.interval)
    elif args.mode == 'reset':
        confirm = input("确认要重置所有统计数据吗？ (yes/no): ")
        if confirm.lower() == 'yes':
            monitor.stats = monitor._load_stats()
            # 清空统计
            monitor.stats['twitter_api'] = {
                'total_requests': 0,
                'total_tweets': 0,
                'error_count': 0,
                'daily_stats': {},
                'monthly_stats': {},
            }
            monitor.stats['chatgpt_api'] = {
                'total_requests': 0,
                'total_input_tokens': 0,
                'total_output_tokens': 0,
                'daily_stats': {},
            }
            monitor._save_stats()
            print("✓ 统计数据已重置")
        else:
            print("取消重置")


if __name__ == '__main__':
    main()
