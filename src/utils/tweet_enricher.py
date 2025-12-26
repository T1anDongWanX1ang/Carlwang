"""
推文增强处理器
处理推文的kol_id和entity_id字段，以及话题分析和存储
"""
import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..api.chatgpt_client import chatgpt_client
from ..database.topic_dao import topic_dao
from ..database.kol_dao import kol_dao
from ..database.project_dao import ProjectDAO
from ..database.connection import db_manager
from ..models.tweet import Tweet
from ..models.topic import Topic
from ..models.project import Project
from .advanced_topic_processor import advanced_topic_processor
from .smart_classifier import smart_classifier
from .token_extractor import token_extractor


class TweetEnricher:
    """推文增强处理器"""
    
    def __init__(self):
        """初始化推文增强器"""
        self.logger = logging.getLogger(__name__)
        self.chatgpt = chatgpt_client
        self.topic_dao = topic_dao
        self.kol_dao = kol_dao
        self.project_dao = ProjectDAO()
        self.token_extractor = token_extractor

        # 缓存已知的KOL用户ID，避免重复查询
        self._kol_user_cache = {}
        self._refresh_kol_cache()
        
        # 缓存项目kol_id，避免重复查询
        self._project_kol_cache = {}
        self._refresh_project_kol_cache()
    
    def _refresh_kol_cache(self):
        """刷新KOL用户缓存"""
        try:
            kols = self.kol_dao.get_active_kols()
            self._kol_user_cache = {kol.user_id: kol.kol_id for kol in kols}
            self.logger.info(f"刷新KOL缓存，找到 {len(self._kol_user_cache)} 个KOL用户")
        except Exception as e:
            self.logger.error(f"刷新KOL缓存失败: {e}")
            self._kol_user_cache = {}
    
    def _refresh_project_kol_cache(self):
        """刷新项目KOL缓存（从twitter_kol_token_project表）"""
        try:
            # 查询twitter_kol_token_project表，获取所有项目的kol_id
            sql = "SELECT DISTINCT id as kol_id FROM twitter_kol_token_project WHERE id IS NOT NULL AND id != ''"
            results = db_manager.execute_query(sql)
            
            if results:
                self._project_kol_cache = {row['kol_id'] for row in results}
                self.logger.info(f"刷新项目KOL缓存，找到 {len(self._project_kol_cache)} 个项目KOL")
            else:
                self._project_kol_cache = set()
                self.logger.warning("twitter_kol_token_project表中没有找到项目数据")
        except Exception as e:
            self.logger.error(f"刷新项目KOL缓存失败: {e}")
            self._project_kol_cache = set()
    
    def _is_project_kol(self, kol_id: Optional[str]) -> bool:
        """
        检查kol_id是否是项目官方账号（通过twitter_kol_token_project表判断）
        
        Args:
            kol_id: KOL用户ID
            
        Returns:
            如果是项目官方账号返回True，否则返回False
        """
        if not kol_id:
            return False
        
        # 先检查缓存
        if kol_id in self._project_kol_cache:
            return True
        
        # 如果缓存中没有，查询数据库
        try:
            sql = "SELECT COUNT(*) as count FROM twitter_kol_token_project WHERE id = %s"
            results = db_manager.execute_query(sql, (kol_id,))
            
            if results and results[0]['count'] > 0:
                # 添加到缓存
                self._project_kol_cache.add(kol_id)
                return True
            
            return False
        except Exception as e:
            self.logger.error(f"查询项目KOL失败: {e}")
            return False
    
    def enrich_tweets(self, tweets: List[Tweet], 
                     user_data_map: Dict[str, Dict[str, Any]]) -> List[Tweet]:
        """
        批量增强推文数据
        
        Args:
            tweets: 推文列表
            user_data_map: 用户数据映射 {user_id: user_data}
            
        Returns:
            增强后的推文列表
        """
        try:
            enriched_tweets = []
            
            for tweet in tweets:
                try:
                    # 增强单条推文
                    enriched_tweet = self.enrich_single_tweet(tweet, user_data_map)
                    if enriched_tweet:
                        enriched_tweets.append(enriched_tweet)
                    else:
                        # 如果增强失败，至少设置基础字段后再使用
                        self.logger.warning(f"推文 {tweet.id_str} 增强失败，使用基础增强")
                        fallback_tweet = self._apply_basic_enrichment(tweet, user_data_map)
                        enriched_tweets.append(fallback_tweet)
                        
                except Exception as e:
                    self.logger.error(f"增强推文 {tweet.id_str} 发生异常: {e}")
                    self.logger.error(f"异常详情: {type(e).__name__}: {str(e)}")
                    # 发生异常时，至少应用基础增强
                    try:
                        fallback_tweet = self._apply_basic_enrichment(tweet, user_data_map)
                        enriched_tweets.append(fallback_tweet)
                        self.logger.info(f"推文 {tweet.id_str} 应用基础增强成功")
                    except Exception as fallback_error:
                        self.logger.error(f"推文 {tweet.id_str} 基础增强也失败: {fallback_error}")
                        # 最后兜底：使用原始推文但设置基本KOL信息
                        if tweet.id_str in user_data_map:
                            user_data = user_data_map[tweet.id_str]
                            tweet.kol_id = user_data.get('id_str')
                        enriched_tweets.append(tweet)
            
            self.logger.info(f"推文增强完成，处理 {len(enriched_tweets)} 条推文")
            return enriched_tweets
            
        except Exception as e:
            self.logger.error(f"批量增强推文失败: {e}")
            return tweets
    
    def enrich_project_tweets_simplified(self, tweets: List[Tweet], 
                                       user_data_map: Dict[str, Dict[str, Any]]) -> List[Tweet]:
        """
        简化的项目推文增强处理（去除特定字段计算和复杂数据加载）
        
        去除字段：is_valid, entity_id, topic_id, project_id, narrative_id, is_real_project_tweet
        去除逻辑：KOL缓存、项目匹配器、token提取器等重型组件
        保留字段：kol_id（从user_data直接获取）, sentiment（基于关键词）, is_announce（映射为isAnnounce）
        
        Args:
            tweets: 推文列表
            user_data_map: 用户数据映射 {user_id: user_data}
            
        Returns:
            简化增强后的推文列表
        """
        try:
            enriched_tweets = []
            
            for tweet in tweets:
                try:
                    # 简化增强单条推文
                    enriched_tweet = self._enrich_project_tweet_simplified(tweet, user_data_map)
                    if enriched_tweet:
                        enriched_tweets.append(enriched_tweet)
                    else:
                        # 如果增强失败，使用最基础的处理
                        self.logger.warning(f"项目推文 {tweet.id_str} 增强失败，使用最基础处理")
                        fallback_tweet = self._apply_minimal_enrichment(tweet, user_data_map)
                        enriched_tweets.append(fallback_tweet)
                        
                except Exception as e:
                    self.logger.error(f"增强项目推文 {tweet.id_str} 发生异常: {e}")
                    # 发生异常时，使用最基础的处理
                    try:
                        fallback_tweet = self._apply_minimal_enrichment(tweet, user_data_map)
                        enriched_tweets.append(fallback_tweet)
                    except Exception as fallback_e:
                        self.logger.error(f"项目推文基础处理也失败: {fallback_e}")
                        # 最后的保险：设置基本字段后使用原推文
                        tweet.kol_id = user_data_map.get(tweet.id_str, {}).get('id_str')
                        tweet.sentiment = None
                        tweet.isAnnounce = 0
                        enriched_tweets.append(tweet)
            
            self.logger.info(f"项目推文简化增强完成: {len(enriched_tweets)}/{len(tweets)} 成功")
            return enriched_tweets
        
        except Exception as e:
            self.logger.error(f"增强项目推文列表失败: {e}")
            return tweets
    
    def _enrich_project_tweet_simplified(self, tweet: Tweet, 
                                       user_data_map: Dict[str, Dict[str, Any]]) -> Optional[Tweet]:
        """
        极简化增强单条项目推文 - 去掉所有复杂逻辑和AI处理
        
        Args:
            tweet: 推文对象
            user_data_map: 用户数据映射
            
        Returns:
            增强后的推文对象
        """
        try:
            self.logger.debug(f"开始极简化增强项目推文 {tweet.id_str}")
            
            # 1. 设置 kol_id（直接从user_data获取，不依赖缓存）
            if tweet.id_str in user_data_map:
                user_data = user_data_map[tweet.id_str]
                tweet.kol_id = user_data.get('id_str')
                
                # 2. 生成推文URL（使用实际用户名）
                screen_name = user_data.get('screen_name', 'unknown')
                tweet.tweet_url = f"https://x.com/{screen_name}/status/{tweet.id_str}"
            else:
                tweet.kol_id = None
                tweet.tweet_url = f"https://x.com/unknown/status/{tweet.id_str}"
            
            # 3. 设置基础情绪（简化版本，基于关键词）
            tweet.sentiment = self._simple_sentiment_analysis(tweet.full_text)
            
            # 4. 基础公告检测（简化版本）
            tweet.isAnnounce = self._simple_announcement_detection(tweet.full_text)
            tweet.summary = None  # 不生成AI总结
            
            # 5. 基础活动检测（简化版本）
            tweet.is_activity = self._simple_activity_detection(tweet.full_text)
            tweet.activity_detail = None  # 不生成复杂活动详情
            
            # 6. 基础链接提取（简化版本）
            tweet.link_url = self._simple_link_extraction(tweet.full_text)
            
            # 7. 其他字段设置为默认值
            tweet.project_tag = None
            tweet.token_tag = None
            
            self.logger.info(f"项目推文 {tweet.id_str} 极简化增强完成: kol_id={tweet.kol_id}, sentiment={tweet.sentiment}, isAnnounce={tweet.isAnnounce}, is_activity={tweet.is_activity}")
            return tweet
            
        except Exception as e:
            self.logger.error(f"极简化增强项目推文 {tweet.id_str} 失败: {e}")
            return None
    
    def _simple_sentiment_analysis(self, text: str) -> Optional[str]:
        """
        简化的情绪分析 - 仅基于关键词，不使用AI
        
        Args:
            text: 推文内容
            
        Returns:
            情绪倾向：'Positive'/'Negative'/'Neutral'
        """
        try:
            if not text:
                return 'Neutral'
                
            text_lower = text.lower()
            
            # 积极关键词
            positive_keywords = [
                'bullish', 'moon', 'pump', 'surge', 'rally', 'breakout',
                'gains', 'profit', 'good', 'great', 'amazing', 'awesome',
                'up', 'rise', 'green', 'buy', 'hold', '涨', '好', '牛', '看好'
            ]
            
            # 消极关键词
            negative_keywords = [
                'bearish', 'dump', 'crash', 'dip', 'decline', 'fall',
                'bad', 'terrible', 'awful', 'down', 'red', 'sell',
                '跌', '坏', '熊', '看空', '糟糕'
            ]
            
            positive_score = sum(1 for keyword in positive_keywords if keyword in text_lower)
            negative_score = sum(1 for keyword in negative_keywords if keyword in text_lower)
            
            if positive_score > negative_score:
                return 'Positive'
            elif negative_score > positive_score:
                return 'Negative'
            else:
                return 'Neutral'
                
        except Exception as e:
            self.logger.error(f"简化情绪分析失败: {e}")
            return 'Neutral'
    
    def _simple_announcement_detection(self, text: str) -> int:
        """
        简化的公告检测 - 仅基于关键词，不使用AI
        
        Args:
            text: 推文内容
            
        Returns:
            1表示是公告，0表示不是
        """
        try:
            if not text or len(text.strip()) < 20:
                return 0
                
            text_lower = text.lower()
            
            # 公告关键词
            announcement_keywords = [
                'announce', 'announcement', 'update', 'news', 'release',
                'launch', 'partnership', 'integration', 'upgrade',
                '公告', '宣布', '发布', '更新', '启动', '合作'
            ]
            
            return 1 if any(keyword in text_lower for keyword in announcement_keywords) else 0
            
        except Exception as e:
            self.logger.error(f"简化公告检测失败: {e}")
            return 0
    
    def _simple_activity_detection(self, text: str) -> int:
        """
        简化的活动检测 - 仅基于关键词，不使用AI
        
        Args:
            text: 推文内容
            
        Returns:
            1表示是活动，0表示不是
        """
        try:
            if not text or len(text.strip()) < 20:
                return 0
                
            text_lower = text.lower()
            
            # 活动关键词
            activity_keywords = [
                'airdrop', 'giveaway', 'campaign', 'contest', 'reward',
                'prize', 'bounty', 'quest', 'distribution',
                '空投', '活动', '奖励', '赠送', '竞赛'
            ]
            
            return 1 if any(keyword in text_lower for keyword in activity_keywords) else 0
            
        except Exception as e:
            self.logger.error(f"简化活动检测失败: {e}")
            return 0
    
    def _simple_link_extraction(self, text: str) -> Optional[str]:
        """
        简化的链接提取 - 仅使用正则表达式
        
        Args:
            text: 推文内容
            
        Returns:
            提取的第一个链接，如果没有则返回None
        """
        try:
            if not text:
                return None
                
            import re
            # 匹配HTTP/HTTPS链接
            url_pattern = r'https?://[^\s]+'
            urls = re.findall(url_pattern, text)
            
            return urls[0] if urls else None
            
        except Exception as e:
            self.logger.error(f"简化链接提取失败: {e}")
            return None
    
    def _apply_minimal_enrichment(self, tweet: Tweet, user_data_map: Dict[str, Dict[str, Any]]) -> Tweet:
        """
        应用最小化增强，仅设置必要字段
        
        Args:
            tweet: 原始推文
            user_data_map: 用户数据映射
            
        Returns:
            最小化增强的推文
        """
        try:
            # 1. 设置kol_id（直接从用户数据获取）
            if tweet.id_str in user_data_map:
                user_data = user_data_map[tweet.id_str]
                tweet.kol_id = user_data.get('id_str')
                
                # 2. 生成推文URL
                screen_name = user_data.get('screen_name', 'unknown')
                tweet.tweet_url = f"https://x.com/{screen_name}/status/{tweet.id_str}"
            else:
                tweet.kol_id = None
                tweet.tweet_url = f"https://x.com/unknown/status/{tweet.id_str}"
            
            # 3. 设置默认值
            tweet.sentiment = None
            tweet.isAnnounce = 0
            tweet.summary = None
            tweet.is_activity = 0
            tweet.activity_detail = None
            tweet.link_url = None
            tweet.project_tag = None
            tweet.token_tag = None
            
            self.logger.debug(f"推文 {tweet.id_str} 最小化增强: kol_id={tweet.kol_id}")
            return tweet
            
        except Exception as e:
            self.logger.error(f"最小化增强推文 {tweet.id_str} 失败: {e}")
            return tweet
        """
        应用基础增强，确保关键字段被设置
        
        Args:
            tweet: 原始推文
            user_data_map: 用户数据映射
            
        Returns:
            应用基础增强的推文
        """
        try:
            # 1. 设置基本的KOL ID
            if tweet.id_str in user_data_map:
                user_data = user_data_map[tweet.id_str]
                kol_id = user_data.get('id_str')
                tweet.kol_id = kol_id
                
                # 2. 检查是否是项目官方推文（这是关键字段）
                is_project_kol = self._is_project_kol(kol_id)
                tweet.is_real_project_tweet = 1 if is_project_kol else 0
                
                # 3. 设置基本有效性
                tweet.is_valid = 1  # 默认有效
                
                # 4. 记录基础增强信息
                tweet_url = f"https://x.com/{user_data.get('screen_name', 'unknown')}/status/{tweet.id_str}"
                tweet.tweet_url = tweet_url
                
                self.logger.debug(f"推文 {tweet.id_str} 基础增强: kol_id={kol_id}, is_real_project_tweet={tweet.is_real_project_tweet}")
                
            return tweet
            
        except Exception as e:
            self.logger.error(f"基础增强推文 {tweet.id_str} 失败: {e}")
            return tweet
    
    def enrich_single_tweet(self, tweet: Tweet, 
                          user_data_map: Dict[str, Dict[str, Any]]) -> Optional[Tweet]:
        """
        增强单条推文
        
        Args:
            tweet: 推文对象
            user_data_map: 用户数据映射
            
        Returns:
            增强后的推文对象
        """
        try:
            self.logger.debug(f"开始增强推文 {tweet.id_str}")
            
            # 1. 设置 kol_id（从用户数据中获取 user.id_str）
            try:
                kol_id = self._extract_kol_id_from_user_data(tweet, user_data_map)
                tweet.kol_id = kol_id
                self.logger.debug(f"推文 {tweet.id_str} KOL ID设置: {kol_id}")
            except Exception as e:
                self.logger.error(f"推文 {tweet.id_str} 设置KOL ID失败: {e}")
                raise
            
            # 2. 生成推文URL
            try:
                tweet_url = self._generate_tweet_url(tweet)
                tweet.tweet_url = tweet_url
                self.logger.debug(f"推文 {tweet.id_str} URL设置: {tweet_url}")
            except Exception as e:
                self.logger.error(f"推文 {tweet.id_str} 生成URL失败: {e}")
                # URL生成失败不应该阻止后续处理
                tweet.tweet_url = f"https://x.com/unknown/status/{tweet.id_str}"
            
            # 3. 先检查是否为项目官方推文
            is_project_kol = self._is_project_kol(tweet.kol_id)
            tweet.is_real_project_tweet = 1 if is_project_kol else 0
            
            # 4. 内容质量检查：判断是否为有效的Crypto相关内容
            # 项目官方推文无需严格的内容验证，直接标记为有效
            try:
                if is_project_kol:
                    is_valid = True
                    self.logger.debug(f"推文 {tweet.id_str} 来自项目官方账号，跳过内容验证")
                else:
                    # 尝试AI验证，失败则fallback到关键词验证
                    is_valid = self._validate_crypto_content(tweet.full_text, use_ai=True)
                    
                tweet.is_valid = is_valid
                self.logger.debug(f"推文 {tweet.id_str} 内容有效性: {is_valid}")
            except Exception as e:
                self.logger.error(f"推文 {tweet.id_str} 内容验证失败: {e}")
                # 内容验证失败时默认为有效
                tweet.is_valid = 1
                is_valid = 1
            
            # 5. 仅对有效推文进行进一步分析
            if is_valid:
                # 5.1 情绪分析
                sentiment = self._analyze_tweet_sentiment(tweet.full_text, use_ai=True)
                tweet.sentiment = sentiment

                # 4.2 使用智能分类器处理项目和话题
                classification_result = self._classify_and_set_ids(tweet)

                # 设置相应的ID字段（确保互斥性）
                if classification_result.content_type == 'project':
                    tweet.project_id = classification_result.project_id
                    tweet.topic_id = None  # 确保topic_id为空
                    tweet.entity_id = classification_result.project_id
                    tweet.project_tag = classification_result.project_tag  # 设置RootData匹配的项目名称
                    # 项目推文不需要提取token_tag
                    tweet.token_tag = None
                elif classification_result.content_type == 'topic':
                    tweet.project_id = None  # 确保project_id为空
                    tweet.topic_id = classification_result.topic_id
                    tweet.entity_id = classification_result.topic_id
                    tweet.project_tag = None  # 确保project_tag为空
                    # 4.3 对于非项目推文，提取token symbols
                    token_tag = self._extract_token_symbols(tweet.full_text)
                    tweet.token_tag = token_tag
                else:
                    # 未知类型，清空所有分类字段
                    tweet.project_id = None
                    tweet.topic_id = None
                    tweet.entity_id = None
                    tweet.project_tag = None
                    # 4.3 对于非项目推文，提取token symbols
                    token_tag = self._extract_token_symbols(tweet.full_text)
                    tweet.token_tag = token_tag

                # 4.4 只对项目官方推文判断是否为重要公告
                if tweet.is_real_project_tweet == 1:
                    is_announce = self._classify_announcement(tweet.full_text)
                    tweet.is_announce = is_announce

                    # 4.6 对于公告推文，生成AI总结
                    if is_announce == 1:
                        announce_summary = self._generate_announcement_summary(tweet.full_text)
                        tweet.summary = announce_summary
                        self.logger.info(f"推文 {tweet.id_str} 公告总结: {announce_summary}")
                else:
                    # 非项目官方推文不判断公告
                    tweet.is_announce = 0
                    tweet.summary = None

                self.logger.info(f"推文 {tweet.id_str} 增强完成: kol_id={kol_id}, valid={is_valid}, sentiment={sentiment}, project_id={tweet.project_id}, topic_id={tweet.topic_id}, entity_id={tweet.entity_id}, project_tag={tweet.project_tag}, token_tag={tweet.token_tag}, is_real_project_tweet={tweet.is_real_project_tweet}, is_announce={tweet.is_announce}, url={tweet_url}")
            else:
                # 无效推文不进行话题分析和情绪分析
                tweet.sentiment = None
                tweet.entity_id = None
                tweet.project_id = None
                tweet.topic_id = None
                tweet.project_tag = None
                tweet.token_tag = None  # 无效推文也不提取token
                tweet.is_announce = 0  # 无效推文不是公告
                
                # 确认项目官方推文字段已设置（前面已经检查过了）
                if not hasattr(tweet, 'is_real_project_tweet'):
                    # 如果前面的检查失败了，重新检查
                    try:
                        is_project_kol = self._is_project_kol(tweet.kol_id)
                        tweet.is_real_project_tweet = 1 if is_project_kol else 0
                        self.logger.debug(f"补充检查无效推文 {tweet.id_str} 项目官方推文: kol_id={tweet.kol_id}, is_project_kol={is_project_kol}")
                    except Exception as e:
                        self.logger.error(f"补充检查无效推文 {tweet.id_str} 项目官方推文失败: {e}")
                        tweet.is_real_project_tweet = 0
                
                self.logger.info(f"推文 {tweet.id_str} 标记为无效，kol_id={tweet.kol_id}, is_real_project_tweet={tweet.is_real_project_tweet}, url={tweet.tweet_url}")
            
            return tweet
            
        except Exception as e:
            self.logger.error(f"增强推文 {tweet.id_str} 失败: {e}")
            self.logger.error(f"异常详情: {type(e).__name__}: {str(e)}")
            import traceback
            self.logger.error(f"异常堆栈: {traceback.format_exc()}")
            
            # 异常时至少确保关键字段被设置
            try:
                # 确保至少有基本的KOL信息
                if not hasattr(tweet, 'kol_id') or tweet.kol_id is None:
                    kol_id = self._extract_kol_id_from_user_data(tweet, user_data_map)
                    tweet.kol_id = kol_id
                
                # 确保is_real_project_tweet字段被设置
                if not hasattr(tweet, 'is_real_project_tweet'):
                    is_project_kol = self._is_project_kol(tweet.kol_id)
                    tweet.is_real_project_tweet = 1 if is_project_kol else 0
                    
                self.logger.info(f"推文 {tweet.id_str} 异常恢复成功，保留关键字段")
                
            except Exception as recovery_error:
                self.logger.error(f"推文 {tweet.id_str} 异常恢复也失败: {recovery_error}")
            
            return None
    
    def _validate_crypto_content(self, text: str, use_ai: bool = True) -> bool:
        """
        验证推文是否为有效的加密货币相关内容（且非广告）
        
        Args:
            text: 推文内容
            use_ai: 是否使用AI分析（默认使用关键词模式避免API消耗）
            
        Returns:
            是否为有效内容
        """
        try:
            if not text or len(text.strip()) < 10:
                return False
            
            text_lower = text.lower()
            
            # 方法1: 使用AI分析（如果API可用且启用）
            if use_ai:
                validation_result = self._ai_validate_content(text)
                if validation_result is not None:
                    return validation_result
            
            # 方法2: 基于关键词的内容验证（默认方法）
            return self._keyword_validate_content(text_lower)
            
        except Exception as e:
            self.logger.error(f"内容验证失败: {e}")
            return False
    
    def _keyword_validate_content(self, text_lower: str) -> bool:
        """
        基于关键词的内容验证
        
        Args:
            text_lower: 小写文本内容
            
        Returns:
            是否为有效内容
        """
        try:
            # 加密货币相关关键词
            crypto_keywords = [
                'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency',
                'blockchain', 'defi', 'nft', 'dao', 'web3', 'altcoin',
                'doge', 'ada', 'sol', 'matic', 'avax', 'dot', 'link', 'usdt', 'usdc',
                'binance', 'coinbase', 'trading', 'market', 'price', 'bull', 'bear',
                'hodl', 'satoshi', 'mining', 'wallet', 'exchange', 'token',
                '比特币', '以太坊', '加密货币', '区块链', '数字货币', '币', '代币'
            ]
            
            # 检查是否包含加密货币关键词
            has_crypto_keywords = any(keyword in text_lower for keyword in crypto_keywords)
            
            if not has_crypto_keywords:
                self.logger.debug("推文不包含加密货币关键词")
                return False
            
            # 强制排除的明显广告关键词（权重高）
            high_spam_keywords = [
                'airdrop', '空投', 'giveaway', '赠送', 'free tokens', '免费代币',
                'click here', '点击这里', 'link in bio', 'dm me', '私信我',
                'follow for free', '关注获得免费', 'join telegram', '加入电报群',
                'presale', '预售', 'ido', 'ico', '首发', 'listing soon', '即将上市'
            ]
            
            # 中等权重的广告关键词
            medium_spam_keywords = [
                'promotion', '推广', 'sponsored', '赞助', 'partnership', '合作',
                'exclusive', '独家', 'limited offer', '限时优惠', 'special deal', '特价',
                'buy now', '立即购买', 'get rich', '暴富', 'easy money', '轻松赚钱',
                'guaranteed profit', '保证盈利', '100x', '1000x', 'moon mission', '登月'
            ]
            
            # 低权重的可疑关键词
            low_spam_keywords = [
                'pump', 'dump', 'diamond hands', 'ape in', 'lambo', 'fomo',
                'degen', 'alpha', 'gem', 'rocket', 'fire', 'bullish af'
            ]
            
            # 计算广告得分
            high_spam_score = sum(2 for keyword in high_spam_keywords if keyword in text_lower)
            medium_spam_score = sum(1 for keyword in medium_spam_keywords if keyword in text_lower)
            low_spam_score = sum(0.5 for keyword in low_spam_keywords if keyword in text_lower)
            
            total_spam_score = high_spam_score + medium_spam_score + low_spam_score
            
            # 如果包含高权重广告关键词，直接标记为无效
            if high_spam_score > 0:
                self.logger.debug(f"推文包含明显广告关键词，spam_score: {total_spam_score}")
                return False
            
            # 如果总得分过高，标记为无效
            if total_spam_score >= 3:
                self.logger.debug(f"推文广告特征得分过高: {total_spam_score}")
                return False
            
            # URL检查：包含过多链接的可能是推广
            import re
            url_count = len(re.findall(r'http[s]?://\S+', text_lower))
            if url_count > 1:  # 降低阈值，超过1个链接就可疑
                self.logger.debug(f"推文包含过多链接 ({url_count}个)")
                return False
            
            # 文本质量检查
            if self._is_low_quality_text(text_lower):
                return False
            
            # 检查是否包含有价值的分析内容
            if self._has_valuable_content(text_lower):
                self.logger.debug("推文包含有价值内容，通过验证")
                return True
            
            # 对于一般内容，根据spam得分决定
            if total_spam_score <= 1:
                self.logger.debug(f"推文通过关键词验证，spam_score: {total_spam_score}")
                return True
            else:
                self.logger.debug(f"推文可疑，spam_score: {total_spam_score}")
                return False
            
        except Exception as e:
            self.logger.error(f"关键词验证失败: {e}")
            return False
    
    def _has_valuable_content(self, text_lower: str) -> bool:
        """
        检查是否包含有价值的分析内容
        
        Args:
            text_lower: 小写文本
            
        Returns:
            是否包含有价值内容
        """
        valuable_keywords = [
            'analysis', '分析', 'chart', '图表', 'technical', '技术',
            'support', '支撑', 'resistance', '阻力', 'breakout', '突破',
            'pattern', '形态', 'trend', '趋势', 'forecast', '预测',
            'market cap', '市值', 'volume', '成交量', 'fundamentals', '基本面',
            'adoption', '采用', 'regulation', '监管', 'news', '新闻',
            'development', '开发', 'upgrade', '升级', 'partnership', '合作'
        ]
        
        return any(keyword in text_lower for keyword in valuable_keywords)
    
    def _is_low_quality_text(self, text_lower: str) -> bool:
        """
        检查是否为低质量文本
        
        Args:
            text_lower: 小写文本
            
        Returns:
            是否为低质量文本
        """
        # 过多重复字符
        import re
        if re.search(r'(.)\1{4,}', text_lower):  # 同一字符重复5次以上
            return True
        
        # 过多感叹号或问号
        if text_lower.count('!') > 5 or text_lower.count('?') > 3:
            return True
        
        # 过多表情符号（简单检测）
        emoji_count = len(re.findall(r'[🚀💰💎🔥⚡️📈📉🎯🌙💯🎉✅❌]', text_lower))
        if emoji_count > 8:
            return True
        
        return False
    
    def _ai_validate_content(self, text: str) -> Optional[bool]:
        """
        使用AI验证内容质量

        Args:
            text: 推文内容

        Returns:
            是否有效，None表示AI分析失败
        """
        try:
            # 使用 /no_think 指令禁用Qwen3的思考过程
            prompt = f"""/no_think
分析推文是否为有价值的加密货币相关内容（非广告）。
推文: {text}

直接回答true或false，不要解释："""

            response = self.chatgpt._make_request([
                {"role": "system", "content": "You are a content validator. Reply ONLY with 'true' or 'false', nothing else."},
                {"role": "user", "content": prompt}
            ], temperature=0.0, max_tokens=20)

            if response:
                # 清理Qwen3可能返回的<think>标签（即使用/no_think也可能有空标签）
                import re
                cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
                cleaned = re.sub(r'</?think>', '', cleaned)  # 移除未闭合的标签
                cleaned = cleaned.strip().lower()

                # 严格匹配true或false
                if cleaned == 'true':
                    return True
                elif cleaned == 'false':
                    return False
                else:
                    # AI返回格式异常，记录并返回None（会fallback到关键词验证）
                    self.logger.debug(f"AI验证返回异常格式: {repr(response[:50])}, fallback到关键词验证")
                    return None

            return None

        except Exception as e:
            self.logger.debug(f"AI内容验证失败: {e}, fallback到关键词验证")
            return None
    
    def _analyze_tweet_sentiment(self, text: str, use_ai: bool = True) -> Optional[str]:
        """
        分析推文情绪倾向
        
        Args:
            text: 推文内容
            use_ai: 是否使用AI分析
            
        Returns:
            情绪倾向：'Positive'/'Negative'/'Neutral'
        """
        try:
            # 方法1: 使用AI分析（如果API可用且启用）
            if use_ai:
                ai_sentiment = self._ai_analyze_sentiment(text)
                if ai_sentiment:
                    return ai_sentiment
            
            # 方法2: 基于关键词的情绪分析（默认方法）
            return self._keyword_analyze_sentiment(text.lower())
            
        except Exception as e:
            self.logger.error(f"情绪分析失败: {e}")
            return 'Neutral'  # 默认中性
    
    def _keyword_analyze_sentiment(self, text_lower: str) -> str:
        """
        基于关键词的情绪分析
        
        Args:
            text_lower: 小写文本
            
        Returns:
            情绪倾向
        """
        try:
            # 积极情绪关键词
            positive_keywords = [
                'bullish', 'moon', 'pump', 'surge', 'rally', 'breakout',
                'all-time high', 'ath', 'gains', 'profit', 'buy', 'hold',
                'diamond hands', 'hodl', 'to the moon', 'green', 'up',
                '涨', '牛市', '突破', '收益', '盈利', '看好', '看涨'
            ]
            
            # 消极情绪关键词
            negative_keywords = [
                'bearish', 'dump', 'crash', 'dip', 'sell', 'panic',
                'bear market', 'correction', 'decline', 'fall', 'drop',
                'red', 'down', 'loss', 'risk', 'warning', 'scam',
                '跌', '熊市', '下跌', '风险', '警告', '亏损', '看空'
            ]
            
            # 中性关键词（分析、技术、观察等）
            neutral_keywords = [
                'analysis', 'chart', 'technical', 'support', 'resistance',
                'pattern', 'trend', 'market', 'trading', 'price',
                '分析', '技术', '观察', '市场', '价格', '走势'
            ]
            
            # 计算情绪得分
            positive_score = sum(1 for keyword in positive_keywords if keyword in text_lower)
            negative_score = sum(1 for keyword in negative_keywords if keyword in text_lower)
            neutral_score = sum(1 for keyword in neutral_keywords if keyword in text_lower)
            
            # 价格数字检查
            import re
            if re.search(r'(\+\d+%|up \d+%|\d+% gain)', text_lower):
                positive_score += 2
            elif re.search(r'(-\d+%|down \d+%|\d+% loss)', text_lower):
                negative_score += 2
            
            # 决定情绪倾向
            if positive_score > negative_score and positive_score > 0:
                return 'Positive'
            elif negative_score > positive_score and negative_score > 0:
                return 'Negative'
            else:
                return 'Neutral'
            
        except Exception as e:
            self.logger.error(f"关键词情绪分析失败: {e}")
            return 'Neutral'
    
    def _ai_analyze_sentiment(self, text: str) -> Optional[str]:
        """
        使用AI分析情绪
        
        Args:
            text: 推文内容
            
        Returns:
            情绪倾向或None
        """
        try:
            sentiment_result = self.chatgpt.analyze_sentiment(text)
            
            if sentiment_result and 'sentiment' in sentiment_result:
                ai_sentiment = sentiment_result['sentiment'].lower()
                
                # 映射到标准格式
                if ai_sentiment == 'positive':
                    return 'Positive'
                elif ai_sentiment == 'negative':
                    return 'Negative'
                else:
                    return 'Neutral'
            
            return None
            
        except Exception as e:
            self.logger.warning(f"AI情绪分析失败: {e}")
            return None
    
    def _extract_kol_id_from_user_data(self, tweet: Tweet, 
                                      user_data_map: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """
        从推文对应的用户数据中提取kol_id（即用户的id_str）
        
        Args:
            tweet: 推文对象
            user_data_map: 用户数据映射 {tweet_id: user_data}
            
        Returns:
            用户ID（作为kol_id）
        """
        try:
            # 方法1: 根据推文ID找到对应的用户数据
            # user_data_map应该是 {tweet_id: user_data} 的映射
            user_data = user_data_map.get(tweet.id_str)
            if user_data:
                user_id_str = user_data.get('id_str')
                if user_id_str:
                    self.logger.debug(f"推文 {tweet.id_str} 找到对应用户: {user_id_str}")
                    return user_id_str
            
            # 方法2: 如果没有找到对应的用户数据，遍历所有用户数据（向后兼容）
            # 但这种方法容易导致错误的映射
            if not user_data_map:
                self.logger.warning(f"推文 {tweet.id_str} 的用户数据映射为空")
                return None
            
            # 如果user_data_map不是按tweet_id组织的，尝试其他方式
            # 检查是否是按user_id组织的映射
            for key, data in user_data_map.items():
                if isinstance(data, dict) and data.get('id_str'):
                    # 这可能是一个用户数据，但我们需要找到推文对应的用户
                    # 由于没有直接的映射关系，我们无法确定哪个用户发了这条推文
                    pass
            
            self.logger.warning(f"推文 {tweet.id_str} 无法在用户数据映射中找到对应的用户")
            return None
            
        except Exception as e:
            self.logger.error(f"提取用户ID失败 {tweet.id_str}: {e}")
            return None
    
    def _generate_tweet_url(self, tweet: Tweet) -> Optional[str]:
        """
        生成推文URL
        
        Args:
            tweet: 推文对象
            
        Returns:
            推文URL
        """
        try:
            if not tweet.id_str:
                return None
            
            # 使用固定的用户名生成URL，格式：https://x.com/aixbt_agent/status/{id_str}
            base_url = "https://x.com/aixbt_agent/status/"
            tweet_url = f"{base_url}{tweet.id_str}"
            
            self.logger.info(f"为推文 {tweet.id_str} 生成URL: {tweet_url}")
            return tweet_url
            
        except Exception as e:
            self.logger.error(f"生成推文URL失败 {tweet.id_str}: {e}")
            return None
    
    
    def should_process_in_crawler_flow(self) -> bool:
        """
        判断是否应该在爬虫流程中处理话题数据生成
        
        Returns:
            是否应该在爬虫流程中处理
        """
        # 分析：话题数据生成应该在爬虫流程中完成，原因如下：
        # 1. 数据一致性：推文和话题数据需要保持关联一致性
        # 2. 实时性：话题识别需要在推文入库时就完成，避免延迟
        # 3. 性能：避免后续批量处理带来的额外开销
        # 4. 简化架构：统一在一个流程中处理，减少系统复杂度
        return True
    
    def _classify_and_set_ids(self, tweet: Tweet):
        """
        使用智能分类器对推文进行分类，并设置project_id和topic_id

        Args:
            tweet: 推文对象

        Returns:
            ClassificationResult: 分类结果
        """
        try:
            # 使用智能分类器进行分类
            classification_result = smart_classifier.classify_tweet(tweet)

            if classification_result.content_type == 'unknown':
                self.logger.debug(f"推文 {tweet.id_str} 无法分类: {classification_result.reason}")
            elif classification_result.content_type == 'project':
                self.logger.info(f"推文 {tweet.id_str} 识别为项目: {classification_result.entity_name} " +
                               f"(project_id: {classification_result.project_id}, " +
                               f"新创建: {classification_result.is_new_created})")
            elif classification_result.content_type == 'topic':
                self.logger.info(f"推文 {tweet.id_str} 识别为话题: {classification_result.entity_name} " +
                               f"(topic_id: {classification_result.topic_id}, " +
                               f"新创建: {classification_result.is_new_created})")

            return classification_result

        except Exception as e:
            self.logger.error(f"分类推文失败 {tweet.id_str}: {e}")
            # 返回空的分类结果
            from .smart_classifier import ClassificationResult
            return ClassificationResult(content_type='unknown', reason=f"分类出错: {str(e)}")

    def _extract_token_symbols(self, text: str) -> Optional[str]:
        """
        从推文文本中提取token symbols

        Args:
            text: 推文文本

        Returns:
            提取的token symbol字符串（逗号分隔），如果没有则返回None
        """
        try:
            if not text or len(text.strip()) < 10:
                return None

            # 1. 使用AI提取token symbols
            ai_symbols = None
            try:
                ai_symbols = self.chatgpt.extract_token_symbols_from_tweet(text)
                if ai_symbols:
                    self.logger.debug(f"AI提取到的symbols: {ai_symbols}")
            except Exception as e:
                self.logger.warning(f"AI提取token失败，将使用规则提取: {e}")

            # 2. 使用token_extractor验证和规范化
            token_tag = self.token_extractor.extract_symbols_from_text(text, ai_symbols)

            if token_tag:
                self.logger.info(f"成功提取token symbols: {token_tag}")
            else:
                self.logger.debug("未能提取到有效的token symbols")

            return token_tag

        except Exception as e:
            self.logger.error(f"提取token symbols失败: {e}")
            return None

    def _classify_announcement(self, text: str) -> int:
        """
        判断推文是否为重要公告

        Args:
            text: 推文文本

        Returns:
            1表示是重要公告，0表示不是
        """
        try:
            if not text or len(text.strip()) < 10:
                return 0

            # 使用ChatGPT判断是否为公告
            is_announce = self.chatgpt.classify_tweet_announcement(text)

            if is_announce == 1:
                self.logger.info(f"识别为重要公告")
            else:
                self.logger.debug(f"非重要公告")

            return is_announce

        except Exception as e:
            self.logger.error(f"判断公告失败: {e}")
            return 0

    def _generate_announcement_summary(self, text: str) -> Optional[str]:
        """
        为公告推文生成AI总结

        Args:
            text: 推文文本

        Returns:
            公告总结文本，失败则返回None
        """
        try:
            if not text or len(text.strip()) < 10:
                return None

            # 使用ChatGPT生成公告总结
            summary = self.chatgpt.summarize_announcement(text)

            if summary:
                self.logger.info(f"成功生成公告总结: {summary}")
                return summary
            else:
                self.logger.warning(f"公告总结生成失败，返回None")
                return None

        except Exception as e:
            self.logger.error(f"生成公告总结失败: {e}")
            return None


# 全局推文增强器实例
tweet_enricher = TweetEnricher()
