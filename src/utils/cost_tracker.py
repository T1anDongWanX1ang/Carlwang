"""
API成本追踪工具
用于将API调用成本实时写入数据库
"""
import uuid
import socket
from datetime import datetime
from typing import Dict, Any, Optional
import pymysql
from .logger import get_logger


class CostTracker:
    """API成本追踪器"""

    def __init__(self, db_config: Dict[str, Any]):
        """
        初始化成本追踪器

        Args:
            db_config: 数据库配置字典
        """
        self.logger = get_logger(__name__)
        self.db_config = db_config
        self.run_id = str(uuid.uuid4())[:8]  # 生成本次运行的唯一ID
        self.server_host = socket.gethostname()  # 获取服务器主机名

        self.logger.info(f"成本追踪器初始化完成 (run_id: {self.run_id}, host: {self.server_host})")

    def record_cost(self,
                   task_name: str,
                   api_stats: Dict[str, Any],
                   list_ids: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        记录API成本到数据库

        Args:
            task_name: 任务名称（如 'daily_tweet_crawler'）
            api_stats: API统计信息字典，包含：
                - total_cost_usd: 总成本
                - total_requests: 总请求次数
                - tweets_fetched: 获取的推文数
                - error_count: 错误次数
                - success_rate: 成功率
                - avg_cost_per_request: 平均每次请求成本
            list_ids: 爬取的list ID列表，逗号分隔（可选）
            metadata: 额外的元数据（可选）

        Returns:
            是否成功写入数据库
        """
        try:
            # 提取统计数据
            total_cost_usd = api_stats.get('total_cost_usd', 0)
            total_requests = api_stats.get('total_requests', 0)
            tweets_fetched = api_stats.get('tweets_fetched', 0)
            error_count = api_stats.get('error_count', 0)
            success_rate = api_stats.get('success_rate', 0)
            avg_cost_per_request = api_stats.get('avg_cost_per_request', 0)

            # 计算每条推文成本
            cost_per_tweet = total_cost_usd / max(tweets_fetched, 1) if tweets_fetched > 0 else 0

            # 连接数据库
            conn = pymysql.connect(
                host=self.db_config.get('host'),
                port=self.db_config.get('port', 3306),
                user=self.db_config.get('user'),
                password=self.db_config.get('password'),
                database='tp_alarm',  # 使用 tp_alarm 数据库
                charset='utf8mb4'
            )

            cursor = conn.cursor()

            # 准备SQL
            sql = """
            INSERT INTO api_cost_tracking
            (timestamp, task_name, run_id, list_ids, total_requests, tweets_fetched, error_count,
             total_cost_usd, avg_cost_per_request, cost_per_tweet, server_host,
             success_rate, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # 准备元数据JSON
            import json
            metadata_json = json.dumps(metadata) if metadata else None

            # 执行插入
            cursor.execute(sql, (
                datetime.now(),
                task_name,
                self.run_id,
                list_ids,
                total_requests,
                tweets_fetched,
                error_count,
                total_cost_usd,
                avg_cost_per_request,
                cost_per_tweet,
                self.server_host,
                success_rate,
                metadata_json
            ))

            conn.commit()
            cursor.close()
            conn.close()

            self.logger.info(f"✅ 成本数据已写入数据库: ${total_cost_usd:.6f} USD (任务: {task_name})")
            return True

        except Exception as e:
            self.logger.error(f"❌ 写入成本数据到数据库失败: {e}")
            # 写入失败不影响主流程，只是记录日志
            return False

    def get_run_id(self) -> str:
        """获取本次运行ID"""
        return self.run_id
