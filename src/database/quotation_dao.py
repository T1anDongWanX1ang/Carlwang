"""
推文引用关系数据访问对象 (Data Access Object)
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from .connection import db_manager


class QuotationDAO:
    """推文引用关系数据访问对象"""
    
    def __init__(self):
        """初始化DAO"""
        self.db_manager = db_manager
        self.table_name = 'twitter_quotations'  # 引用关系表
        self.logger = logging.getLogger(__name__)
    
    def create_table_if_not_exists(self) -> bool:
        """
        创建twitter_quotations表（如果不存在）
        
        Returns:
            是否创建成功
        """
        try:
            sql = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id BIGINT AUTO_INCREMENT,
                twitter_id VARCHAR(50) NOT NULL COMMENT '引用推文的ID',
                user_id VARCHAR(50) NOT NULL COMMENT '引用推文的用户ID', 
                user_name VARCHAR(100) NOT NULL COMMENT '引用推文的用户名',
                twitter_quotation_id VARCHAR(50) NOT NULL COMMENT '被引用推文的ID',
                user_quotation_id VARCHAR(50) NOT NULL COMMENT '被引用推文的用户ID',
                quotations_user_name VARCHAR(100) NOT NULL COMMENT '被引用推文的用户名',
                created_at DATETIME NOT NULL COMMENT '引用推文的创建时间',
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录更新时间'
            ) ENGINE=OLAP
            DISTRIBUTED BY HASH(twitter_id) BUCKETS 10
            PROPERTIES (
                "replication_allocation" = "tag.location.default: 1"
            )
            """
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    conn.commit()
            
            self.logger.info(f"成功创建或确认存在表: {self.table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建表失败 {self.table_name}: {e}")
            return False
    
    def insert_quotation(self, quotation_data: Dict[str, Any]) -> bool:
        """
        插入单条引用关系数据
        
        Args:
            quotation_data: 引用关系数据字典
            
        Returns:
            是否插入成功
        """
        try:
            # 验证必需的字段
            required_fields = [
                'twitter_id', 'user_id', 'user_name', 
                'twitter_quotation_id', 'user_quotation_id', 
                'quotations_user_name'
            ]
            
            for field in required_fields:
                if field not in quotation_data or not quotation_data[field]:
                    self.logger.error(f"引用关系数据缺少必需字段: {field}")
                    return False
            
            sql = f"""
            INSERT INTO {self.table_name} (
                twitter_id, user_id, user_name,
                twitter_quotation_id, user_quotation_id, quotations_user_name,
                quotation_name
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            values = (
                quotation_data['twitter_id'],
                quotation_data['user_id'],
                quotation_data['user_name'],
                quotation_data['twitter_quotation_id'],
                quotation_data['user_quotation_id'],
                quotation_data['quotations_user_name'],
                quotation_data['quotations_user_name']  # 使用quotations_user_name作为quotation_name
            )
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, values)
                    conn.commit()
            
            self.logger.debug(f"成功插入引用关系: {quotation_data['twitter_id']} -> {quotation_data['twitter_quotation_id']}")
            return True
            
        except Exception as e:
            self.logger.error(f"插入引用关系数据失败: {e}")
            return False
    
    def batch_insert_quotations(self, quotations: List[Dict[str, Any]]) -> int:
        """
        批量插入引用关系数据
        
        Args:
            quotations: 引用关系数据列表
            
        Returns:
            成功插入的数量
        """
        if not quotations:
            return 0
        
        success_count = 0
        
        try:
            # 验证并过滤有效数据
            valid_quotations = []
            required_fields = [
                'twitter_id', 'user_id', 'user_name', 
                'twitter_quotation_id', 'user_quotation_id', 
                'quotations_user_name'
            ]
            
            for quotation in quotations:
                if all(field in quotation and quotation[field] for field in required_fields):
                    valid_quotations.append(quotation)
                else:
                    self.logger.warning(f"跳过无效的引用关系数据: {quotation}")
            
            if not valid_quotations:
                self.logger.warning("没有有效的引用关系数据")
                return 0
            
            sql = f"""
            INSERT INTO {self.table_name} (
                twitter_id, user_id, user_name,
                twitter_quotation_id, user_quotation_id, quotations_user_name,
                quotation_name
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            # 准备批量插入的数据
            values_list = []
            for quotation in valid_quotations:
                values = (
                    quotation['twitter_id'],
                    quotation['user_id'],
                    quotation['user_name'],
                    quotation['twitter_quotation_id'],
                    quotation['user_quotation_id'],
                    quotation['quotations_user_name'],
                    quotation['quotations_user_name']  # 使用quotations_user_name作为quotation_name
                )
                values_list.append(values)
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(sql, values_list)
                    success_count = cursor.rowcount
                    conn.commit()
            
            self.logger.info(f"批量插入引用关系数据完成: {success_count}/{len(quotations)} 条成功")
            
        except Exception as e:
            self.logger.error(f"批量插入引用关系数据失败: {e}")
            
        return success_count
    
    def get_quotations_by_twitter_id(self, twitter_id: str) -> List[Dict[str, Any]]:
        """
        根据推文ID获取其引用关系
        
        Args:
            twitter_id: 推文ID
            
        Returns:
            引用关系列表
        """
        try:
            sql = f"""
            SELECT twitter_id, user_id, user_name,
                   twitter_quotation_id, user_quotation_id, quotations_user_name,
                   update_time
            FROM {self.table_name}
            WHERE twitter_id = %s
            ORDER BY update_time DESC
            """
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (twitter_id,))
                    columns = [desc[0] for desc in cursor.description]
                    results = []
                    
                    for row in cursor.fetchall():
                        quotation = dict(zip(columns, row))
                        results.append(quotation)
            
            return results
            
        except Exception as e:
            self.logger.error(f"查询引用关系失败 (twitter_id: {twitter_id}): {e}")
            return []
    
    def get_quotations_by_user(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        根据用户ID获取其发起的引用关系
        
        Args:
            user_id: 用户ID
            limit: 限制返回数量
            
        Returns:
            引用关系列表
        """
        try:
            sql = f"""
            SELECT twitter_id, user_id, user_name,
                   twitter_quotation_id, user_quotation_id, quotations_user_name,
                   update_time
            FROM {self.table_name}
            WHERE user_id = %s
            ORDER BY update_time DESC
            LIMIT %s
            """
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (user_id, limit))
                    columns = [desc[0] for desc in cursor.description]
                    results = []
                    
                    for row in cursor.fetchall():
                        quotation = dict(zip(columns, row))
                        results.append(quotation)
            
            return results
            
        except Exception as e:
            self.logger.error(f"查询用户引用关系失败 (user_id: {user_id}): {e}")
            return []
    
    def get_most_quoted_tweets(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取最常被引用的推文
        
        Args:
            limit: 限制返回数量
            
        Returns:
            被引用次数统计列表
        """
        try:
            sql = f"""
            SELECT twitter_quotation_id, user_quotation_id, quotations_user_name,
                   COUNT(*) as quote_count,
                   MIN(update_time) as first_quoted_at,
                   MAX(update_time) as last_quoted_at
            FROM {self.table_name}
            GROUP BY twitter_quotation_id, user_quotation_id, quotations_user_name
            ORDER BY quote_count DESC, last_quoted_at DESC
            LIMIT %s
            """
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (limit,))
                    columns = [desc[0] for desc in cursor.description]
                    results = []
                    
                    for row in cursor.fetchall():
                        quote_stat = dict(zip(columns, row))
                        results.append(quote_stat)
            
            return results
            
        except Exception as e:
            self.logger.error(f"查询最常被引用推文失败: {e}")
            return []
    
    def get_quotation_count(self) -> int:
        """
        获取引用关系总数
        
        Returns:
            引用关系总数
        """
        try:
            sql = f"SELECT COUNT(*) FROM {self.table_name}"
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    result = cursor.fetchone()
                    return result[0] if result else 0
            
        except Exception as e:
            self.logger.error(f"查询引用关系总数失败: {e}")
            return 0


# 全局实例
quotation_dao = QuotationDAO()