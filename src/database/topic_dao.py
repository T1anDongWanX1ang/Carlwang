"""
话题数据访问对象 (Data Access Object)
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta
import json

from .connection import db_manager
from ..models.topic import Topic


class TopicDAO:
    """话题数据访问对象"""
    
    def __init__(self):
        """初始化DAO"""
        self.db_manager = db_manager
        self.table_name = self.db_manager.db_config.get('tables', {}).get('topic', 'topics')
        self.logger = logging.getLogger(__name__)
    
    def insert_topic(self, topic: Topic) -> bool:
        """
        插入话题数据
        
        Args:
            topic: 话题对象
            
        Returns:
            是否插入成功
        """
        if not topic.validate():
            self.logger.error(f"话题数据验证失败: {topic}")
            return False
        
        try:
            sql = f"""
            INSERT INTO {self.table_name} (
                topic_id, topic_name, created_at, brief, key_entities, popularity,
                propagation_speed_5m, propagation_speed_1h, propagation_speed_4h,
                kol_opinions, mob_opinion_direction, summary,
                popularity_history, update_time
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            topic_data = topic.to_dict()
            params = (
                topic_data['topic_id'],  # 直接使用设置的topic_id
                topic_data['topic_name'],
                topic_data['created_at'],
                topic_data['brief'],
                topic_data['key_entities'],  # 新增字段
                topic_data['popularity'],
                topic_data['propagation_speed_5m'],
                topic_data['propagation_speed_1h'],
                topic_data['propagation_speed_4h'],
                topic_data['kol_opinions'],
                topic_data['mob_opinion_direction'],
                topic_data['summary'],
                topic_data['popularity_history'],
                topic_data['update_time']
            )
            
            affected_rows = self.db_manager.execute_update(sql, params)
            success = affected_rows > 0
            
            if success:
                self.logger.info(f"话题插入成功: {topic.topic_name} (ID: {topic.topic_id})")
            else:
                self.logger.warning(f"话题插入失败: {topic.topic_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"插入话题数据失败: {topic.topic_name}, 错误: {e}")
            return False
    
    def upsert_topic(self, topic: Topic) -> bool:
        """
        插入或更新话题数据
        
        Args:
            topic: 话题对象
            
        Returns:
            是否操作成功
        """
        if not topic.validate():
            self.logger.error(f"话题数据验证失败: {topic}")
            return False
        
        try:
            # 先尝试查找现有话题
            existing_topic = self.get_topic_by_name(topic.topic_name)
            
            if existing_topic:
                # Doris不允许更新主键，所以删除旧记录再插入新记录
                self.logger.info(f"话题已存在，删除旧记录: {existing_topic.topic_name} (旧ID: {existing_topic.topic_id})")
                
                # 删除旧记录
                delete_sql = f"DELETE FROM {self.table_name} WHERE topic_id = %s"
                delete_result = self.db_manager.execute_update(delete_sql, (existing_topic.topic_id,))
                
                if delete_result > 0:
                    self.logger.info(f"成功删除旧话题记录: {existing_topic.topic_name}")
                    # 插入新记录
                    success = self.insert_topic(topic)
                    if success:
                        self.logger.info(f"话题替换成功: {topic.topic_name} (新ID: {topic.topic_id})")
                else:
                    self.logger.error(f"删除旧话题记录失败: {existing_topic.topic_name}")
                    success = False
            else:
                # 插入新话题
                success = self.insert_topic(topic)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Upsert话题数据失败: {topic.topic_name}, 错误: {e}")
            return False
    
    def batch_upsert_topics(self, topics: List[Topic]) -> int:
        """
        批量插入或更新话题数据
        
        Args:
            topics: 话题对象列表
            
        Returns:
            成功操作的数量
        """
        if not topics:
            return 0
        
        # 过滤有效的话题
        valid_topics = [topic for topic in topics if topic.validate()]
        if len(valid_topics) != len(topics):
            self.logger.warning(f"过滤掉 {len(topics) - len(valid_topics)} 条无效话题")
        
        if not valid_topics:
            return 0
        
        success_count = 0
        for topic in valid_topics:
            try:
                if self.upsert_topic(topic):
                    success_count += 1
            except Exception as e:
                self.logger.error(f"批量upsert话题失败: {topic.topic_name}, 错误: {e}")
                continue
        
        self.logger.info(f"批量upsert话题成功: {success_count}/{len(valid_topics)} 条数据")
        return success_count
    
    def get_topic_by_id(self, topic_id: str) -> Optional[Topic]:
        """
        根据ID获取话题
        
        Args:
            topic_id: 话题ID
            
        Returns:
            话题对象或None
        """
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE topic_id = %s"
            results = self.db_manager.execute_query(sql, (topic_id,))
            
            if results:
                return Topic.from_dict(results[0])
            return None
            
        except Exception as e:
            self.logger.error(f"查询话题失败: {topic_id}, 错误: {e}")
            return None
    
    def get_topic_by_name(self, topic_name: str) -> Optional[Topic]:
        """
        根据话题名称查询话题
        
        Args:
            topic_name: 话题名称
            
        Returns:
            话题对象或None
        """
        try:
            sql = f"""
            SELECT topic_id, topic_name, created_at, brief, key_entities, popularity,
                   propagation_speed_5m, propagation_speed_1h, propagation_speed_4h,
                   kol_opinions, mob_opinion_direction, summary,
                   popularity_history, update_time
            FROM {self.table_name}
            WHERE topic_name = %s
            LIMIT 1
            """
            
            results = self.db_manager.execute_query(sql, (topic_name,))
            
            if results:
                row = results[0]
                topic = Topic(
                    topic_id=row['topic_id'],
                    topic_name=row['topic_name'],
                    created_at=row['created_at'],
                    brief=row['brief'],
                    key_entities=row['key_entities'],  # 新增字段
                    popularity=row['popularity'],
                    propagation_speed_5m=row['propagation_speed_5m'],
                    propagation_speed_1h=row['propagation_speed_1h'],
                    propagation_speed_4h=row['propagation_speed_4h'],
                    kol_opinions=json.loads(row['kol_opinions']) if row['kol_opinions'] else [],
                    mob_opinion_direction=row['mob_opinion_direction'],
                    summary=row['summary'],
                    popularity_history=json.loads(row['popularity_history']) if row['popularity_history'] else [],
                    update_time=row['update_time']
                )
                return topic
            
            return None
            
        except Exception as e:
            self.logger.error(f"根据名称查询话题失败: {topic_name}, 错误: {e}")
            return None
    
    def get_topics_by_date_range(self, start_date: datetime, end_date: datetime, 
                                limit: int = 100) -> List[Topic]:
        """
        根据日期范围获取话题
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制数量
            
        Returns:
            话题对象列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE created_at BETWEEN %s AND %s 
            ORDER BY created_at DESC 
            LIMIT %s
            """
            results = self.db_manager.execute_query(sql, (start_date, end_date, limit))
            
            return [Topic.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"按日期范围查询话题失败: {e}")
            return []
    
    def get_hot_topics(self, limit: int = 10, timeframe: str = "24h") -> List[Topic]:
        """
        获取热门话题
        
        Args:
            limit: 限制数量
            timeframe: 时间范围 (24h, 7d, 30d)
            
        Returns:
            热门话题列表
        """
        try:
            # 计算时间范围
            if timeframe == "24h":
                hours = 24
            elif timeframe == "7d":
                hours = 24 * 7
            elif timeframe == "30d":
                hours = 24 * 30
            else:
                hours = 24
            
            start_time = datetime.now() - timedelta(hours=hours)
            
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE created_at >= %s 
            ORDER BY popularity DESC 
            LIMIT %s
            """
            results = self.db_manager.execute_query(sql, (start_time, limit))
            
            return [Topic.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"查询热门话题失败: {e}")
            return []
    
    def get_trending_topics(self, limit: int = 10) -> List[Topic]:
        """
        获取趋势话题（基于传播速度）
        
        Args:
            limit: 限制数量
            
        Returns:
            趋势话题列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE propagation_speed_1h > 0 
            ORDER BY propagation_speed_1h DESC 
            LIMIT %s
            """
            results = self.db_manager.execute_query(sql, (limit,))
            
            return [Topic.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"查询趋势话题失败: {e}")
            return []
    
    def get_topics_by_sentiment(self, sentiment: str, limit: int = 10) -> List[Topic]:
        """
        根据情感方向获取话题
        
        Args:
            sentiment: 情感方向 (positive/negative/neutral)
            limit: 限制数量
            
        Returns:
            话题列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE mob_opinion_direction = %s 
            ORDER BY popularity DESC 
            LIMIT %s
            """
            results = self.db_manager.execute_query(sql, (sentiment, limit))
            
            return [Topic.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"按情感查询话题失败: {sentiment}, 错误: {e}")
            return []
    
    def get_topic_count(self) -> int:
        """
        获取话题总数
        
        Returns:
            话题总数
        """
        try:
            sql = f"SELECT COUNT(*) as count FROM {self.table_name}"
            results = self.db_manager.execute_query(sql)
            
            if results:
                return results[0]['count']
            return 0
            
        except Exception as e:
            self.logger.error(f"查询话题总数失败: {e}")
            return 0
    
    def delete_topic(self, topic_id: str) -> bool:
        """
        删除话题
        
        Args:
            topic_id: 话题ID
            
        Returns:
            是否删除成功
        """
        try:
            sql = f"DELETE FROM {self.table_name} WHERE topic_id = %s"
            affected_rows = self.db_manager.execute_update(sql, (topic_id,))
            
            success = affected_rows > 0
            if success:
                self.logger.info(f"话题删除成功: {topic_id}")
            else:
                self.logger.warning(f"话题删除失败，可能不存在: {topic_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"删除话题失败: {topic_id}, 错误: {e}")
            return False
    
    def search_topics(self, keyword: str, limit: int = 20) -> List[Topic]:
        """
        搜索话题
        
        Args:
            keyword: 搜索关键词
            limit: 限制数量
            
        Returns:
            话题列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE topic_name LIKE %s OR brief LIKE %s OR summary LIKE %s OR key_entities LIKE %s
            ORDER BY popularity DESC 
            LIMIT %s
            """
            search_pattern = f"%{keyword}%"
            results = self.db_manager.execute_query(
                sql, 
                (search_pattern, search_pattern, search_pattern, search_pattern, limit)
            )
            
            return [Topic.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"搜索话题失败: {keyword}, 错误: {e}")
            return []
    
    def get_topics_since(self, since_time: datetime, limit: int = 100) -> List[Topic]:
        """
        获取指定时间以来的topics（用于去重比较）
        
        Args:
            since_time: 起始时间
            limit: 限制数量
            
        Returns:
            话题列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE created_at >= %s 
            ORDER BY created_at DESC 
            LIMIT %s
            """
            results = self.db_manager.execute_query(sql, (since_time, limit))
            
            return [Topic.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"查询指定时间以来的话题失败: {e}")
            return []
    
    def insert(self, topic: Topic) -> bool:
        """
        插入话题数据（新的简化接口）
        
        Args:
            topic: 话题对象
            
        Returns:
            是否插入成功
        """
        return self.insert_topic(topic)
    
    def update(self, topic: Topic) -> bool:
        """
        更新话题数据
        
        Args:
            topic: 话题对象
            
        Returns:
            是否更新成功
        """
        if not topic.topic_id:
            self.logger.error("更新话题时topic_id不能为空")
            return False
            
        try:
            sql = f"""
            UPDATE {self.table_name} SET
                topic_name = %s,
                brief = %s,
                key_entities = %s,
                popularity = %s,
                propagation_speed_5m = %s,
                propagation_speed_1h = %s,
                propagation_speed_4h = %s,
                kol_opinions = %s,
                mob_opinion_direction = %s,
                summary = %s,
                popularity_history = %s,
                update_time = %s
            WHERE topic_id = %s
            """
            
            topic_data = topic.to_dict()
            params = (
                topic_data['topic_name'],
                topic_data['brief'],
                topic_data['key_entities'],
                topic_data['popularity'],
                topic_data['propagation_speed_5m'],
                topic_data['propagation_speed_1h'],
                topic_data['propagation_speed_4h'],
                topic_data['kol_opinions'],
                topic_data['mob_opinion_direction'],
                topic_data['summary'],
                topic_data['popularity_history'],
                topic_data['update_time'],
                topic_data['topic_id']
            )
            
            affected_rows = self.db_manager.execute_update(sql, params)
            success = affected_rows > 0
            
            if success:
                self.logger.info(f"话题更新成功: {topic.topic_name} (ID: {topic.topic_id})")
            else:
                self.logger.warning(f"话题更新失败: {topic.topic_name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"更新话题数据失败: {topic.topic_name}, 错误: {e}")
            return False
    
    def update_topic_popularity(self, topic_id: str, new_popularity: int) -> bool:
        """
        更新话题的热度值
        
        Args:
            topic_id: 话题ID
            new_popularity: 新的热度值
            
        Returns:
            是否更新成功
        """
        if not topic_id:
            self.logger.error("更新话题热度时topic_id不能为空")
            return False
            
        try:
            sql = f"""
            UPDATE {self.table_name} SET
                popularity = %s,
                update_time = %s
            WHERE topic_id = %s
            """
            
            from datetime import datetime
            params = (new_popularity, datetime.now(), topic_id)
            
            affected_rows = self.db_manager.execute_update(sql, params)
            success = affected_rows > 0
            
            if success:
                self.logger.debug(f"话题热度更新成功: {topic_id} -> {new_popularity}")
            else:
                self.logger.warning(f"话题热度更新失败: {topic_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"更新话题热度失败: {topic_id}, 错误: {e}")
            return False
    
    def get_by_id(self, topic_id: str) -> Optional[Topic]:
        """
        根据ID获取话题（简化接口）
        
        Args:
            topic_id: 话题ID
            
        Returns:
            话题对象或None
        """
        return self.get_topic_by_id(topic_id)


# 全局DAO实例
topic_dao = TopicDAO() 