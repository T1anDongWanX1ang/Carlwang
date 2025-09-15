"""
Marco数据访问对象
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .connection import db_manager
from ..models.marco import MarcoData


class MarcoDAO:
    """Marco数据访问对象"""
    
    def __init__(self):
        """初始化MarcoDAO"""
        self.table_name = 'twitter_marco'
        self.logger = logging.getLogger(__name__)
    
    def insert(self, marco_data: MarcoData) -> bool:
        """
        插入Marco数据
        
        Args:
            marco_data: Marco数据对象
            
        Returns:
            是否插入成功
        """
        try:
            if not marco_data.validate():
                self.logger.error(f"Marco数据验证失败: {marco_data}")
                return False
            
            sql = f"""
            INSERT INTO {self.table_name} 
            (id, timestamp, sentiment_index, summary)
            VALUES (%s, %s, %s, %s)
            """
            
            data = marco_data.to_dict()
            params = (
                data['id'],
                data['timestamp'],
                data['sentiment_index'],
                data['summary']
            )
            
            affected_rows = db_manager.execute_update(sql, params)
            
            if affected_rows > 0:
                self.logger.info(f"插入Marco数据成功: {marco_data.id}")
                return True
            else:
                self.logger.warning(f"插入Marco数据失败: {marco_data.id}")
                return False
                
        except Exception as e:
            self.logger.error(f"插入Marco数据异常: {e}")
            return False
    
    def batch_insert(self, marco_data_list: List[MarcoData]) -> int:
        """
        批量插入Marco数据
        
        Args:
            marco_data_list: Marco数据列表
            
        Returns:
            成功插入的数量
        """
        if not marco_data_list:
            return 0
        
        success_count = 0
        sql = f"""
        INSERT INTO {self.table_name} 
        (id, timestamp, sentiment_index, summary)
        VALUES (%s, %s, %s, %s)
        """
        
        params_list = []
        for marco_data in marco_data_list:
            if marco_data.validate():
                data = marco_data.to_dict()
                params = (
                    data['id'],
                    data['timestamp'],
                    data['sentiment_index'],
                    data['summary']
                )
                params_list.append(params)
            else:
                self.logger.warning(f"跳过无效的Marco数据: {marco_data}")
        
        try:
            affected_rows = db_manager.execute_batch_update(sql, params_list)
            success_count = affected_rows
            self.logger.info(f"批量插入Marco数据完成，成功插入: {success_count}")
            
        except Exception as e:
            self.logger.error(f"批量插入Marco数据异常: {e}")
            # 尝试逐个插入
            for marco_data in marco_data_list:
                if self.insert(marco_data):
                    success_count += 1
        
        return success_count
    
    def get_by_timestamp_range(self, start_time: datetime, 
                              end_time: datetime) -> List[MarcoData]:
        """
        根据时间范围查询Marco数据
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            Marco数据列表
        """
        try:
            sql = f"""
            SELECT id, timestamp, sentiment_index, summary
            FROM {self.table_name}
            WHERE timestamp >= %s AND timestamp <= %s
            ORDER BY timestamp DESC
            """
            
            results = db_manager.execute_query(sql, (start_time, end_time))
            
            marco_data_list = []
            for row in results:
                marco_data = MarcoData(
                    id=row['id'],
                    timestamp=row['timestamp'],
                    sentiment_index=row['sentiment_index'],
                    summary=row['summary']
                )
                marco_data_list.append(marco_data)
            
            return marco_data_list
            
        except Exception as e:
            self.logger.error(f"查询Marco数据异常: {e}")
            return []
    
    def get_latest(self, limit: int = 10) -> List[MarcoData]:
        """
        获取最新的Marco数据
        
        Args:
            limit: 限制数量
            
        Returns:
            Marco数据列表
        """
        try:
            sql = f"""
            SELECT id, timestamp, sentiment_index, summary
            FROM {self.table_name}
            ORDER BY timestamp DESC
            LIMIT %s
            """
            
            results = db_manager.execute_query(sql, (limit,))
            
            marco_data_list = []
            for row in results:
                marco_data = MarcoData(
                    id=row['id'],
                    timestamp=row['timestamp'],
                    sentiment_index=row['sentiment_index'],
                    summary=row['summary']
                )
                marco_data_list.append(marco_data)
            
            return marco_data_list
            
        except Exception as e:
            self.logger.error(f"查询最新Marco数据异常: {e}")
            return []
    
    def exists_for_timestamp(self, timestamp: datetime) -> bool:
        """
        检查指定时间戳是否已存在数据
        
        Args:
            timestamp: 时间戳
            
        Returns:
            是否存在
        """
        try:
            sql = f"""
            SELECT COUNT(*) as count
            FROM {self.table_name}
            WHERE timestamp = %s
            """
            
            results = db_manager.execute_query(sql, (timestamp,))
            
            if results:
                return results[0]['count'] > 0
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查Marco数据存在性异常: {e}")
            return False
    
    def update_by_timestamp(self, timestamp: datetime, 
                           sentiment_index: Optional[float] = None,
                           summary: Optional[str] = None) -> bool:
        """
        根据时间戳更新Marco数据
        
        Args:
            timestamp: 时间戳
            sentiment_index: 情感指数
            summary: AI总结
            
        Returns:
            是否更新成功
        """
        try:
            updates = []
            params = []
            
            if sentiment_index is not None:
                updates.append("sentiment_index = %s")
                params.append(sentiment_index)
            
            if summary is not None:
                updates.append("summary = %s")
                params.append(summary)
            
            if not updates:
                return False
            
            updates.append("update_time = %s")
            params.append(datetime.now())
            params.append(timestamp)
            
            sql = f"""
            UPDATE {self.table_name}
            SET {', '.join(updates)}
            WHERE timestamp = %s
            """
            
            affected_rows = db_manager.execute_update(sql, params)
            
            if affected_rows > 0:
                self.logger.info(f"更新Marco数据成功: {timestamp}")
                return True
            else:
                self.logger.warning(f"更新Marco数据失败，未找到记录: {timestamp}")
                return False
                
        except Exception as e:
            self.logger.error(f"更新Marco数据异常: {e}")
            return False
    
    def delete_old_data(self, days: int = 30) -> int:
        """
        删除旧数据
        
        Args:
            days: 保留天数
            
        Returns:
            删除的记录数
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            sql = f"""
            DELETE FROM {self.table_name}
            WHERE timestamp < %s
            """
            
            affected_rows = db_manager.execute_update(sql, (cutoff_date,))
            self.logger.info(f"删除{days}天前的Marco数据，共删除: {affected_rows}条记录")
            
            return affected_rows
            
        except Exception as e:
            self.logger.error(f"删除旧Marco数据异常: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        try:
            sql = f"""
            SELECT 
                COUNT(*) as total_count,
                AVG(sentiment_index) as avg_sentiment,
                MIN(timestamp) as earliest_time,
                MAX(timestamp) as latest_time
            FROM {self.table_name}
            WHERE sentiment_index IS NOT NULL
            """
            
            results = db_manager.execute_query(sql)
            
            if results:
                stats = results[0]
                return {
                    'total_records': stats['total_count'] or 0,
                    'average_sentiment': round(stats['avg_sentiment'] or 0, 2),
                    'earliest_timestamp': stats['earliest_time'],
                    'latest_timestamp': stats['latest_time']
                }
            
            return {
                'total_records': 0,
                'average_sentiment': 0,
                'earliest_timestamp': None,
                'latest_timestamp': None
            }
            
        except Exception as e:
            self.logger.error(f"获取Marco数据统计信息异常: {e}")
            return {}


# 全局Marco DAO实例
marco_dao = MarcoDAO() 