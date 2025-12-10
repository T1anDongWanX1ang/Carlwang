"""
推文数据访问对象 (Data Access Object)
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from .connection import db_manager
from ..models.tweet import Tweet


class TweetDAO:
    """推文数据访问对象"""
    
    def __init__(self):
        """初始化DAO"""
        self.db_manager = db_manager
        self.table_name = self.db_manager.db_config.get('tables', {}).get('tweet', 'twitter_tweet')
        self.logger = logging.getLogger(__name__)
    
    def insert_tweet(self, tweet: Tweet) -> bool:
        """
        插入单条推文数据

        Args:
            tweet: 推文对象

        Returns:
            是否插入成功
        """
        if not tweet.validate():
            self.logger.error(f"推文数据验证失败: {tweet}")
            return False

        # 跳过 is_valid=0 的推文
        if tweet.is_valid == 0:
            self.logger.info(f"跳过存储 is_valid=0 的推文: {tweet.id_str}")
            return False

        try:
            # 包含所有字段（包括新增的project_id、topic_id等）
            sql = f"""
            INSERT INTO {self.table_name} (
                id_str, conversation_id_str, in_reply_to_status_id_str,
                full_text, created_at, created_at_datetime,
                bookmark_count, favorite_count, quote_count, reply_count,
                retweet_count, view_count, engagement_total, update_time,
                kol_id, entity_id, project_id, topic_id, is_valid, sentiment, tweet_url, link_url, token_tag, project_tag, isAnnounce, summary, is_real_project_tweet
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """

            tweet_data = tweet.to_dict()
            params = (
                tweet_data['id_str'],
                tweet_data['conversation_id_str'],
                tweet_data['in_reply_to_status_id_str'],
                tweet_data['full_text'],
                tweet_data['created_at'],
                tweet_data['created_at_datetime'],
                tweet_data['bookmark_count'],
                tweet_data['favorite_count'],
                tweet_data['quote_count'],
                tweet_data['reply_count'],
                tweet_data['retweet_count'],
                tweet_data['view_count'],
                tweet_data['engagement_total'],
                tweet_data['update_time'],
                tweet_data['kol_id'],
                tweet_data['entity_id'],
                tweet_data['project_id'],
                tweet_data['topic_id'],
                tweet_data['is_valid'],
                tweet_data['sentiment'],
                tweet_data['tweet_url'],
                tweet_data.get('link_url'),  # 使用get方法以防字段不存在
                tweet_data.get('token_tag'),
                tweet_data.get('project_tag'),
                tweet_data.get('is_announce', 0),  # 默认为0
                tweet_data.get('summary'),  # 公告总结
                tweet_data.get('is_real_project_tweet', 0)  # 是否为项目官方推文
            )
            
            affected_rows = self.db_manager.execute_update(sql, params)
            success = affected_rows > 0
            
            if success:
                self.logger.info(f"推文插入成功: {tweet.id_str}")
            else:
                self.logger.warning(f"推文插入失败: {tweet.id_str}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"插入推文数据失败: {tweet.id_str}, 错误: {e}")
            return False
    
    def upsert_tweet(self, tweet: Tweet) -> bool:
        """
        插入或更新推文数据（Doris Unique Key模型自动处理重复数据）

        Args:
            tweet: 推文对象

        Returns:
            是否操作成功
        """
        if not tweet.validate():
            self.logger.error(f"推文数据验证失败: {tweet}")
            return False

        # 跳过 is_valid=0 的推文
        if tweet.is_valid == 0:
            self.logger.info(f"跳过存储 is_valid=0 的推文: {tweet.id_str}")
            return False

        try:
            # 包含所有字段（包括新增的project_id、topic_id等）
            sql = f"""
            INSERT INTO {self.table_name} (
                id_str, conversation_id_str, in_reply_to_status_id_str,
                full_text, created_at, created_at_datetime,
                bookmark_count, favorite_count, quote_count, reply_count,
                retweet_count, view_count, engagement_total, update_time,
                kol_id, entity_id, project_id, topic_id, is_valid, sentiment, tweet_url, link_url, token_tag, project_tag, isAnnounce, summary, is_real_project_tweet
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """

            tweet_data = tweet.to_dict()
            params = (
                tweet_data['id_str'],
                tweet_data['conversation_id_str'],
                tweet_data['in_reply_to_status_id_str'],
                tweet_data['full_text'],
                tweet_data['created_at'],
                tweet_data['created_at_datetime'],
                tweet_data['bookmark_count'],
                tweet_data['favorite_count'],
                tweet_data['quote_count'],
                tweet_data['reply_count'],
                tweet_data['retweet_count'],
                tweet_data['view_count'],
                tweet_data['engagement_total'],
                tweet_data['update_time'],
                tweet_data['kol_id'],
                tweet_data['entity_id'],
                tweet_data['project_id'],
                tweet_data['topic_id'],
                tweet_data['is_valid'],
                tweet_data['sentiment'],
                tweet_data['tweet_url'],
                tweet_data.get('link_url'),  # 使用get方法以防字段不存在
                tweet_data.get('token_tag'),
                tweet_data.get('project_tag'),
                tweet_data.get('is_announce', 0),  # 默认为0
                tweet_data.get('summary'),  # 公告总结
                tweet_data.get('is_real_project_tweet', 0)  # 是否为项目官方推文
            )
            
            affected_rows = self.db_manager.execute_update(sql, params)
            success = affected_rows > 0
            
            if success:
                self.logger.info(f"推文upsert成功: {tweet.id_str}")
            else:
                self.logger.warning(f"推文upsert失败: {tweet.id_str}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"推文upsert失败: {tweet.id_str}, 错误: {e}")
            return False
    
    def batch_upsert_tweets(self, tweets: List[Tweet]) -> int:
        """
        批量插入或更新推文数据
        
        Args:
            tweets: 推文对象列表
            
        Returns:
            成功操作的数量
        """
        if not tweets:
            return 0
        
        # 过滤有效的推文（排除 is_valid=0 的推文）
        valid_tweets = [tweet for tweet in tweets if tweet.validate() and tweet.is_valid != 0]
        filtered_count = len(tweets) - len(valid_tweets)
        if filtered_count > 0:
            invalid_by_validation = len([t for t in tweets if not t.validate()])
            invalid_by_is_valid = len([t for t in tweets if t.validate() and t.is_valid == 0])
            self.logger.info(f"过滤推文: 数据验证失败={invalid_by_validation}, is_valid=0={invalid_by_is_valid}, 总共过滤={filtered_count}")
        
        if not valid_tweets:
            return 0
        
        try:
            # 包含所有字段（包括新增的project_id、topic_id等）
            sql = f"""
            INSERT INTO {self.table_name} (
                id_str, conversation_id_str, in_reply_to_status_id_str,
                full_text, created_at, created_at_datetime,
                bookmark_count, favorite_count, quote_count, reply_count,
                retweet_count, view_count, engagement_total, update_time,
                kol_id, entity_id, project_id, topic_id, is_valid, sentiment, tweet_url, link_url, token_tag, project_tag, isAnnounce, summary, is_real_project_tweet
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """

            success_count = 0
            for tweet in valid_tweets:
                try:
                    tweet_data = tweet.to_dict()
                    
                    params = (
                        tweet_data['id_str'],
                        tweet_data['conversation_id_str'],
                        tweet_data['in_reply_to_status_id_str'],
                        tweet_data['full_text'],
                        tweet_data['created_at'],
                        tweet_data['created_at_datetime'],
                        tweet_data['bookmark_count'],
                        tweet_data['favorite_count'],
                        tweet_data['quote_count'],
                        tweet_data['reply_count'],
                        tweet_data['retweet_count'],
                        tweet_data['view_count'],
                        tweet_data['engagement_total'],
                        tweet_data['update_time'],
                        tweet_data['kol_id'],
                        tweet_data['entity_id'],
                        tweet_data['project_id'],
                        tweet_data['topic_id'],
                        tweet_data['is_valid'],
                        tweet_data['sentiment'],
                        tweet_data['tweet_url'],
                        tweet_data.get('link_url'),  # 使用get方法以防字段不存在
                        tweet_data.get('token_tag'),
                        tweet_data.get('project_tag'),
                        tweet_data.get('is_announce', 0),  # 默认为0
                        tweet_data.get('summary'),  # 公告总结
                        tweet_data.get('is_real_project_tweet', 0)  # 是否为项目官方推文
                    )
                    
                    affected_rows = self.db_manager.execute_update(sql, params)
                    if affected_rows > 0:
                        success_count += 1
                        
                except Exception as e:
                    self.logger.error(f"插入推文失败: {tweet.id_str}, 错误: {e}")
                    continue
            
            self.logger.info(f"批量upsert推文成功: {success_count}/{len(valid_tweets)} 条数据")
            return success_count
            
        except Exception as e:
            self.logger.error(f"批量upsert推文数据失败: {e}")
            return 0
    
    def get_tweet_by_id(self, id_str: str) -> Optional[Tweet]:
        """
        根据ID获取推文
        
        Args:
            id_str: 推文ID
            
        Returns:
            推文对象或None
        """
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE id_str = %s"
            results = self.db_manager.execute_query(sql, (id_str,))
            
            if results:
                return self._dict_to_tweet(results[0])
            return None
            
        except Exception as e:
            self.logger.error(f"查询推文失败: {id_str}, 错误: {e}")
            return None
    
    def get_tweets_by_date_range(self, start_date: datetime, end_date: datetime, 
                                limit: int = 1000) -> List[Tweet]:
        """
        根据日期范围获取推文
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制数量
            
        Returns:
            推文对象列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE created_at_datetime BETWEEN %s AND %s 
            ORDER BY created_at_datetime DESC 
            LIMIT %s
            """
            results = self.db_manager.execute_query(sql, (start_date, end_date, limit))
            
            return [self._dict_to_tweet(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"按日期范围查询推文失败: {e}")
            return []
    
    def get_tweet_count(self) -> int:
        """
        获取推文总数
        
        Returns:
            推文总数
        """
        try:
            sql = f"SELECT COUNT(*) as count FROM {self.table_name}"
            results = self.db_manager.execute_query(sql)
            
            if results:
                return results[0]['count']
            return 0
            
        except Exception as e:
            self.logger.error(f"查询推文总数失败: {e}")
            return 0
    
    def delete_tweet(self, id_str: str) -> bool:
        """
        删除推文
        
        Args:
            id_str: 推文ID
            
        Returns:
            是否删除成功
        """
        try:
            sql = f"DELETE FROM {self.table_name} WHERE id_str = %s"
            affected_rows = self.db_manager.execute_update(sql, (id_str,))
            
            success = affected_rows > 0
            if success:
                self.logger.info(f"推文删除成功: {id_str}")
            else:
                self.logger.warning(f"推文删除失败，可能不存在: {id_str}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"删除推文失败: {id_str}, 错误: {e}")
            return False
    
    def _dict_to_tweet(self, data: Dict[str, Any]) -> Tweet:
        """
        将数据库查询结果转换为Tweet对象
        
        Args:
            data: 数据库查询结果字典
            
        Returns:
            Tweet对象
        """
        return Tweet(
            id_str=data['id_str'],
            conversation_id_str=data.get('conversation_id_str'),
            in_reply_to_status_id_str=data.get('in_reply_to_status_id_str'),
            full_text=data.get('full_text'),
            is_quote_status=False,  # 数据库表中没有此字段，设为默认值
            created_at=data.get('created_at'),
            created_at_datetime=data.get('created_at_datetime'),
            bookmark_count=data.get('bookmark_count', 0),
            favorite_count=data.get('favorite_count', 0),
            quote_count=data.get('quote_count', 0),
            reply_count=data.get('reply_count', 0),
            retweet_count=data.get('retweet_count', 0),
            view_count=data.get('view_count', 0),
            engagement_total=data.get('engagement_total'),
            update_time=data.get('update_time')
        )
    
    def get_recent_tweets(self, since_time: datetime = None, limit: int = 100) -> List[Tweet]:
        """
        获取最近的推文

        Args:
            since_time: 起始时间
            limit: 限制数量

        Returns:
            推文列表
        """
        try:
            if since_time:
                sql = f"""
                SELECT * FROM {self.table_name}
                WHERE created_at_datetime >= %s
                ORDER BY created_at_datetime DESC
                LIMIT %s
                """
                results = self.db_manager.execute_query(sql, (since_time, limit))
            else:
                sql = f"""
                SELECT * FROM {self.table_name}
                ORDER BY created_at_datetime DESC
                LIMIT %s
                """
                results = self.db_manager.execute_query(sql, (limit,))

            return [self._dict_to_tweet(row) for row in results]

        except Exception as e:
            self.logger.error(f"查询最近推文失败: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取推文统计信息
        
        Returns:
            统计信息字典
        """
        try:
            sql = f"""
            SELECT 
                COUNT(*) as total_count,
                MIN(created_at_datetime) as earliest_date,
                MAX(created_at_datetime) as latest_date,
                AVG(engagement_total) as avg_engagement
            FROM {self.table_name}
            WHERE created_at_datetime IS NOT NULL
            """
            
            results = self.db_manager.execute_query(sql)
            
            if results:
                stats = results[0]
                return {
                    'total_tweets': stats['total_count'] or 0,
                    'earliest_date': stats['earliest_date'],
                    'latest_date': stats['latest_date'],
                    'average_engagement': round(stats['avg_engagement'] or 0, 2)
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"获取推文统计信息失败: {e}")
            return {}
    
    def get_tweets_by_users_and_time_range(self, user_ids: List[str], 
                                         start_time: datetime, 
                                         end_time: datetime,
                                         limit: int = 1000) -> List[Dict[str, Any]]:
        """
        根据用户ID列表和时间范围查询推文
        
        Args:
            user_ids: 用户ID列表
            start_time: 开始时间
            end_time: 结束时间
            limit: 限制数量
            
        Returns:
            推文数据列表
        """
        try:
            if not user_ids:
                return []
            
            # 构建IN子句的占位符
            placeholders = ','.join(['%s'] * len(user_ids))
            
            sql = f"""
            SELECT id_str, full_text, created_at_datetime, engagement_total, user_id
            FROM {self.table_name}
            WHERE user_id IN ({placeholders})
            AND created_at_datetime >= %s 
            AND created_at_datetime <= %s
            AND full_text IS NOT NULL
            AND LENGTH(full_text) > 10
            ORDER BY created_at_datetime DESC
            LIMIT %s
            """
            
            params = user_ids + [start_time, end_time, limit]
            results = self.db_manager.execute_query(sql, params)
            
            self.logger.info(f"查询到{len(results)}条推文数据")
            return results
            
        except Exception as e:
            self.logger.error(f"按用户和时间范围查询推文失败: {e}")
            return []


# 全局推文DAO实例
tweet_dao = TweetDAO() 