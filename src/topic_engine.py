"""
话题分析引擎
整合话题提取、分析和存储的完整流程
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .database.tweet_dao import tweet_dao
from .database.topic_dao import topic_dao
from .utils.topic_analyzer import TopicAnalyzer
from .utils.config_manager import config
from .utils.logger import get_logger
from .models.tweet import Tweet
from .models.topic import Topic


class TopicEngine:
    """话题分析引擎"""
    
    def __init__(self):
        """初始化话题引擎"""
        self.logger = get_logger(__name__)
        self.tweet_dao = tweet_dao
        self.topic_dao = topic_dao
        self.topic_analyzer = TopicAnalyzer()
        
        # 配置参数
        self.chatgpt_config = config.get('chatgpt', {})
        self.enable_topic_analysis = self.chatgpt_config.get('enable_topic_analysis', True)
        
        # 批处理配置
        batch_config = self.chatgpt_config.get('batch_processing', {})
        self.batch_size = batch_config.get('topic_batch_size', 20)
        self.enable_intelligent_grouping = batch_config.get('enable_intelligent_grouping', True)
        self.content_merge_threshold = batch_config.get('content_merge_threshold', 2000)
        
        # 优化配置
        opt_config = self.chatgpt_config.get('optimization', {})
        self.enable_content_filtering = opt_config.get('enable_content_filtering', True)
        self.min_engagement_threshold = opt_config.get('min_engagement_threshold', 5)
        
        # 统计信息
        self.analysis_count = 0
        self.success_count = 0
        self.error_count = 0
        self.topics_generated = 0
        
        self.logger.info("话题分析引擎初始化完成")
    
    def analyze_recent_tweets(self, hours: int = 24, max_tweets: int = 100) -> bool:
        """
        分析最近的推文并生成话题
        
        Args:
            hours: 分析最近多少小时的推文
            max_tweets: 最大分析推文数量
            
        Returns:
            是否成功
        """
        if not self.enable_topic_analysis:
            self.logger.info("话题分析功能已禁用")
            return True
        
        try:
            self.analysis_count += 1
            self.logger.info(f"开始分析最近 {hours} 小时的推文（最多 {max_tweets} 条）")
            
            # 1. 获取最近的推文
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            recent_tweets = self.tweet_dao.get_tweets_by_date_range(
                start_date=start_time,
                end_date=end_time,
                limit=max_tweets
            )
            
            if not recent_tweets:
                self.logger.warning("没有找到最近的推文数据")
                return True
            
            self.logger.info(f"获取到 {len(recent_tweets)} 条最近推文")
            
            # 2. 内容预筛选（如果启用）
            if self.enable_content_filtering:
                filtered_tweets = self._filter_high_quality_tweets(recent_tweets)
                self.logger.info(f"预筛选后剩余 {len(filtered_tweets)} 条高质量推文")
                recent_tweets = filtered_tweets
                
                if not recent_tweets:
                    self.logger.warning("预筛选后没有符合条件的推文")
                    return True
            
            # 3. 分批处理推文以控制ChatGPT API调用
            topics = []
            for i in range(0, len(recent_tweets), self.batch_size):
                batch_tweets = recent_tweets[i:i + self.batch_size]
                self.logger.info(f"处理推文批次 {i//self.batch_size + 1}/{(len(recent_tweets)-1)//self.batch_size + 1}")
                
                # 提取话题
                batch_topics = self.topic_analyzer.extract_topics_from_tweets(batch_tweets)
                topics.extend(batch_topics)
            
            if not topics:
                self.logger.warning("未能从推文中提取到有效话题")
                return True
            
            self.logger.info(f"成功提取 {len(topics)} 个话题")
            
            # 3. 话题聚类和去重
            clustered_topics = self.topic_analyzer.cluster_similar_topics(topics)
            self.logger.info(f"聚类后得到 {len(clustered_topics)} 个话题")
            
            # 4. 保存话题到数据库
            saved_count = self._save_topics_to_database(clustered_topics)
            
            if saved_count > 0:
                self.logger.info(f"成功保存 {saved_count} 个话题到数据库")
                self.success_count += 1
                self.topics_generated += saved_count
                return True
            else:
                self.logger.error("保存话题到数据库失败")
                self.error_count += 1
                return False
                
        except Exception as e:
            self.logger.error(f"话题分析异常: {e}")
            self.error_count += 1
            return False
    
    def analyze_specific_tweets(self, tweet_ids: List[str]) -> bool:
        """
        分析指定的推文并生成话题
        
        Args:
            tweet_ids: 推文ID列表
            
        Returns:
            是否成功
        """
        try:
            self.logger.info(f"开始分析指定的 {len(tweet_ids)} 条推文")
            
            # 获取指定推文
            tweets = []
            for tweet_id in tweet_ids:
                tweet = self.tweet_dao.get_tweet_by_id(tweet_id)
                if tweet:
                    tweets.append(tweet)
            
            if not tweets:
                self.logger.warning("没有找到有效的推文数据")
                return True
            
            self.logger.info(f"获取到 {len(tweets)} 条有效推文")
            
            # 提取和分析话题
            topics = self.topic_analyzer.extract_topics_from_tweets(tweets)
            
            if not topics:
                self.logger.warning("未能从推文中提取到有效话题")
                return True
            
            # 保存话题
            saved_count = self._save_topics_to_database(topics)
            
            if saved_count > 0:
                self.logger.info(f"成功保存 {saved_count} 个话题")
                self.topics_generated += saved_count
                return True
            else:
                self.logger.error("保存话题失败")
                return False
                
        except Exception as e:
            self.logger.error(f"分析指定推文失败: {e}")
            return False
    
    def update_existing_topics(self, hours: int = 24) -> bool:
        """
        更新现有话题的数据
        
        Args:
            hours: 更新最近多少小时的话题
            
        Returns:
            是否成功
        """
        try:
            self.logger.info(f"开始更新最近 {hours} 小时的话题数据")
            
            # 获取最近的话题
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            recent_topics = self.topic_dao.get_topics_by_date_range(
                start_date=start_time,
                end_date=end_time,
                limit=50
            )
            
            if not recent_topics:
                self.logger.info("没有最近的话题需要更新")
                return True
            
            self.logger.info(f"找到 {len(recent_topics)} 个话题需要更新")
            
            updated_count = 0
            for topic in recent_topics:
                try:
                    # 获取话题相关的新推文（这里需要实现话题-推文关联）
                    # 简化版本：基于话题名称搜索相关推文
                    new_tweets = self._find_related_tweets(topic.topic_name, hours=6)
                    
                    if new_tweets:
                        # 更新话题
                        updated_topic = self.topic_analyzer.update_topic_with_new_tweets(topic, new_tweets)
                        
                        # 保存更新后的话题
                        if self.topic_dao.upsert_topic(updated_topic):
                            updated_count += 1
                            self.logger.info(f"话题更新成功: {topic.topic_name}")
                        
                except Exception as e:
                    self.logger.error(f"更新话题失败: {topic.topic_name}, 错误: {e}")
                    continue
            
            self.logger.info(f"成功更新 {updated_count}/{len(recent_topics)} 个话题")
            return updated_count > 0
            
        except Exception as e:
            self.logger.error(f"更新话题数据异常: {e}")
            return False
    
    def _save_topics_to_database(self, topics: List[Topic]) -> int:
        """
        保存话题到数据库，并更新相关推文的topic_id
        
        Args:
            topics: 话题列表
            
        Returns:
            成功保存的数量
        """
        try:
            self.logger.info(f"开始保存 {len(topics)} 个话题到数据库...")
            
            saved_count = 0
            
            for topic in topics:
                # 保存单个话题
                if self.topic_dao.upsert_topic(topic):
                    saved_count += 1
                    self.logger.info(f"话题保存成功: {topic.topic_name} (ID: {topic.topic_id})")
                    
                    # 更新相关推文的topic_id
                    self._update_related_tweets_topic_id(topic)
                else:
                    self.logger.error(f"话题保存失败: {topic.topic_name}")
            
            return saved_count
            
        except Exception as e:
            self.logger.error(f"保存话题到数据库失败: {e}")
            return 0
    
    def _update_related_tweets_topic_id(self, topic: Topic):
        """
        更新与话题相关的推文的topic_id字段
        
        Args:
            topic: 话题对象
        """
        try:
            # 查找与话题相关的推文（基于话题名称关键词匹配）
            related_tweets = self._find_related_tweets(topic.topic_name, hours=48)
            
            if not related_tweets:
                self.logger.warning(f"未找到与话题 {topic.topic_name} 相关的推文")
                return
            
            self.logger.info(f"找到 {len(related_tweets)} 条与话题 {topic.topic_name} 相关的推文，开始更新topic_id...")
            
            updated_count = 0
            for tweet in related_tweets:
                # 只更新那些没有topic_id或project_id的推文，避免覆盖已分类的推文
                # 增强保护：如果推文已有 project_id，绝不覆盖
                if not tweet.topic_id and not tweet.project_id:
                    # 更新推文的topic_id，使用双重保护确保不覆盖project_id
                    update_sql = f"""
                    UPDATE {self.tweet_dao.table_name} 
                    SET topic_id = %s, update_time = %s 
                    WHERE id_str = %s 
                      AND (topic_id IS NULL OR topic_id = '') 
                      AND (project_id IS NULL OR project_id = '')
                    """
                    
                    affected_rows = self.tweet_dao.db_manager.execute_update(
                        update_sql, 
                        (topic.topic_id, datetime.now(), tweet.id_str)
                    )
                    
                    if affected_rows > 0:
                        updated_count += 1
                        self.logger.debug(f"推文 {tweet.id_str} 已关联到话题 {topic.topic_id}")
                    else:
                        self.logger.debug(f"推文 {tweet.id_str} 未更新（可能已有project_id或topic_id）")
                else:
                    if tweet.project_id:
                        self.logger.debug(f"推文 {tweet.id_str} 已有project_id={tweet.project_id}，跳过话题关联")
                    if tweet.topic_id:
                        self.logger.debug(f"推文 {tweet.id_str} 已有topic_id={tweet.topic_id}，跳过话题关联")
            
            self.logger.info(f"成功将 {updated_count} 条推文关联到话题 {topic.topic_name}")
            
        except Exception as e:
            self.logger.error(f"更新话题相关推文失败: {topic.topic_name}, 错误: {e}")
    
    def _find_related_tweets(self, topic_name: str, hours: int = 24) -> List[Tweet]:
        """
        查找与话题相关的推文（简化版本）
        
        Args:
            topic_name: 话题名称
            hours: 时间范围（小时）
            
        Returns:
            相关推文列表
        """
        try:
            # 简化版本：基于关键词匹配
            # 在实际应用中，这里应该有更复杂的相关性算法
            
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            # 获取时间范围内的推文
            tweets = self.tweet_dao.get_tweets_by_date_range(
                start_date=start_time,
                end_date=end_time,
                limit=200
            )
            
            # 简单的关键词匹配
            keywords = topic_name.lower().split()
            related_tweets = []
            
            for tweet in tweets:
                if tweet.full_text:
                    tweet_text = tweet.full_text.lower()
                    # 如果推文包含话题的任何关键词
                    if any(keyword in tweet_text for keyword in keywords):
                        related_tweets.append(tweet)
            
            return related_tweets[:20]  # 限制数量
            
        except Exception as e:
            self.logger.error(f"查找相关推文失败: {topic_name}, 错误: {e}")
            return []
    
    def get_topic_statistics(self) -> Dict[str, Any]:
        """
        获取话题分析统计信息
        
        Returns:
            统计信息字典
        """
        try:
            analyzer_stats = self.topic_analyzer.get_statistics()
            topic_count = self.topic_dao.get_topic_count()
            
            # 获取热门话题
            hot_topics = self.topic_dao.get_hot_topics(limit=5)
            
            return {
                'analysis_count': self.analysis_count,
                'success_count': self.success_count,
                'error_count': self.error_count,
                'success_rate': (self.success_count / max(self.analysis_count, 1)) * 100,
                'topics_generated': self.topics_generated,
                'total_topics_in_db': topic_count,
                'chatgpt_stats': analyzer_stats,
                'hot_topics_sample': [
                    {
                        'name': topic.topic_name,
                        'popularity': topic.popularity,
                        'sentiment': topic.mob_opinion_direction
                    }
                    for topic in hot_topics
                ]
            }
            
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def reset_statistics(self):
        """重置统计信息"""
        self.analysis_count = 0
        self.success_count = 0
        self.error_count = 0
        self.topics_generated = 0
        self.topic_analyzer.chatgpt_client.reset_statistics()
        self.logger.info("话题引擎统计信息已重置")
    
    def _filter_high_quality_tweets(self, tweets: List[Tweet]) -> List[Tweet]:
        """
        筛选高质量推文，减少不必要的API调用
        
        Args:
            tweets: 原始推文列表
            
        Returns:
            过滤后的高质量推文列表
        """
        filtered_tweets = []
        
        for tweet in tweets:
            try:
                # 1. 互动数量过滤
                engagement = (tweet.favorite_count or 0) + (tweet.retweet_count or 0) * 2
                if engagement < self.min_engagement_threshold:
                    continue
                
                # 2. 内容质量过滤
                if not tweet.full_text or len(tweet.full_text.strip()) < 20:
                    continue
                    
                # 3. 过滤垃圾内容
                content_lower = tweet.full_text.lower()
                spam_keywords = ['spam', 'bot', '机器人', '广告', 'ad', 'promotion']
                if any(keyword in content_lower for keyword in spam_keywords):
                    continue
                
                # 4. 过滤纯转发（没有原创内容）
                if content_lower.startswith('rt @') and len(tweet.full_text) < 50:
                    continue
                
                # 5. 优先包含加密货币相关关键词的推文
                crypto_keywords = ['btc', 'bitcoin', 'eth', 'ethereum', 'crypto', 'defi', 'nft', 
                                 '比特币', '以太坊', '加密', '币', '链', 'blockchain']
                has_crypto_content = any(keyword in content_lower for keyword in crypto_keywords)
                
                if has_crypto_content or engagement > self.min_engagement_threshold * 3:
                    filtered_tweets.append(tweet)
                    
            except Exception as e:
                self.logger.debug(f"推文筛选失败: {e}")
                continue
        
        # 按互动数排序，优先处理高互动推文
        filtered_tweets.sort(key=lambda t: (t.favorite_count or 0) + (t.retweet_count or 0) * 2, reverse=True)
        
        return filtered_tweets


# 全局话题引擎实例
topic_engine = TopicEngine() 