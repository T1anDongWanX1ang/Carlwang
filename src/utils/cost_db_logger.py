#!/usr/bin/env python3
"""
成本数据库记录器
用于将 API 成本统计数据写入 tp_alarm.api_cost_tracking 表
"""
import sys
import os
import pymysql
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import socket


class CostDBLogger:
    """成本数据库记录器"""

    def __init__(self):
        """初始化数据库连接配置"""
        # 从配置文件读取数据库配置
        config = self._load_config()

        # 优先使用 cost_db 配置，如果没有则使用默认值
        cost_db_config = config.get('cost_db', {})

        self.db_config = {
            'host': cost_db_config.get('host', '35.215.99.34'),
            'port': cost_db_config.get('port', 13215),
            'user': cost_db_config.get('username', 'alarm_user'),
            'password': cost_db_config.get('password', 'YOUR_PASSWORD_HERE'),
            'database': cost_db_config.get('database', 'tp_alarm'),
            'charset': 'utf8mb4'
        }
        self.server_host = socket.gethostname()

    def _load_config(self) -> dict:
        """加载配置文件"""
        try:
            # 获取项目根目录
            current_dir = Path(__file__).parent.parent.parent
            config_path = current_dir / 'config' / 'config.json'

            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"警告: 配置文件不存在: {config_path}", file=sys.stderr)
                return {}
        except Exception as e:
            print(f"警告: 读取配置文件失败: {e}", file=sys.stderr)
            return {}

    def log_cost(self,
                 task_name: str,
                 run_id: str,
                 total_requests: int,
                 total_cost_usd: float,
                 tweets_fetched: int = 0,
                 error_count: int = 0,
                 list_ids: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        记录成本数据到数据库

        Args:
            task_name: 任务名称 (如 'kol_following', 'kol_tweet', 'project_tweet')
            run_id: 运行ID (如 '20251231_120000')
            total_requests: 总API调用次数
            total_cost_usd: 总成本USD
            tweets_fetched: 获取的推文/数据数量
            error_count: 错误次数
            list_ids: 列表ID（可选）
            metadata: 其他元数据（可选）

        Returns:
            bool: 是否成功记录
        """
        conn = None
        try:
            # 连接数据库
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()

            # 计算衍生指标
            avg_cost_per_request = total_cost_usd / total_requests if total_requests > 0 else 0
            cost_per_tweet = total_cost_usd / tweets_fetched if tweets_fetched > 0 else 0
            success_rate = ((total_requests - error_count) / total_requests * 100) if total_requests > 0 else 0

            # 当前时间
            timestamp = datetime.now()

            # 元数据转JSON
            metadata_json = json.dumps(metadata) if metadata else None

            # 插入数据
            sql = """
                INSERT INTO api_cost_tracking (
                    timestamp, task_name, run_id, list_ids,
                    total_requests, tweets_fetched, error_count,
                    total_cost_usd, avg_cost_per_request, cost_per_tweet,
                    server_host, success_rate, metadata
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s
                )
            """

            cursor.execute(sql, (
                timestamp, task_name, run_id, list_ids,
                total_requests, tweets_fetched, error_count,
                total_cost_usd, avg_cost_per_request, cost_per_tweet,
                self.server_host, success_rate, metadata_json
            ))

            conn.commit()
            cursor.close()

            return True

        except Exception as e:
            print(f"错误: 记录成本数据失败: {e}", file=sys.stderr)
            if conn:
                conn.rollback()
            return False

        finally:
            if conn:
                conn.close()


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='记录API成本数据到数据库')
    parser.add_argument('--task-name', required=True, help='任务名称')
    parser.add_argument('--run-id', required=True, help='运行ID')
    parser.add_argument('--total-requests', type=int, required=True, help='总API调用次数')
    parser.add_argument('--total-cost', type=float, required=True, help='总成本USD')
    parser.add_argument('--tweets-fetched', type=int, default=0, help='获取的推文/数据数量')
    parser.add_argument('--error-count', type=int, default=0, help='错误次数')
    parser.add_argument('--list-ids', help='列表ID')
    parser.add_argument('--success-kols', type=int, help='成功处理的KOL数量（用于metadata）')
    parser.add_argument('--total-kols', type=int, help='总KOL数量（用于metadata）')
    parser.add_argument('--cache-hits', type=int, help='缓存命中次数（用于metadata）')

    args = parser.parse_args()

    # 构建元数据
    metadata = {}
    if args.success_kols is not None:
        metadata['success_kols'] = args.success_kols
    if args.total_kols is not None:
        metadata['total_kols'] = args.total_kols
    if args.cache_hits is not None:
        metadata['cache_hits'] = args.cache_hits

    # 记录到数据库
    logger = CostDBLogger()
    success = logger.log_cost(
        task_name=args.task_name,
        run_id=args.run_id,
        total_requests=args.total_requests,
        total_cost_usd=args.total_cost,
        tweets_fetched=args.tweets_fetched,
        error_count=args.error_count,
        list_ids=args.list_ids,
        metadata=metadata if metadata else None
    )

    if success:
        print("✓ 成本数据已记录到数据库")
        sys.exit(0)
    else:
        print("✗ 记录成本数据失败", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
