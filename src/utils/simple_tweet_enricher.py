"""
简化版推文增强处理器 - 专门用于项目推文处理
去除所有复杂的数据加载和AI处理逻辑
"""
import logging
import re
import json
from typing import List, Dict, Any, Optional

from ..models.tweet import Tweet


class SimpleTweetEnricher:
    """简化版推文增强处理器"""
    
    def __init__(self):
        """初始化简化版推文增强器"""
        self.logger = logging.getLogger(__name__)
        
        # 延迟导入 chatgpt_client 来支持 AI 功能但避免在初始化时加载
        self._chatgpt_client = None
        
        self.logger.info("简化版推文增强器初始化完成 - 无额外数据加载")
    
    def _get_chatgpt_client(self):
        """延迟加载 ChatGPT 客户端"""
        if self._chatgpt_client is None:
            try:
                from ..api.chatgpt_client import chatgpt_client
                self._chatgpt_client = chatgpt_client
                self.logger.debug("ChatGPT客户端延迟加载成功")
            except Exception as e:
                self.logger.error(f"ChatGPT客户端加载失败: {e}")
                self._chatgpt_client = None
        return self._chatgpt_client
    
    def enrich_project_tweets_simple(self, tweets: List[Tweet], 
                                   user_data_map: Dict[str, Dict[str, Any]]) -> List[Tweet]:
        """
        简化的项目推文增强处理
        
        Args:
            tweets: 推文列表
            user_data_map: 用户数据映射 {tweet_id: user_data}
            
        Returns:
            增强后的推文列表
        """
        try:
            enriched_tweets = []
            
            for tweet in tweets:
                try:
                    # 简化增强单条推文
                    enriched_tweet = self._enrich_single_project_tweet(tweet, user_data_map)
                    if enriched_tweet:
                        enriched_tweets.append(enriched_tweet)
                    else:
                        # 如果增强失败，使用最基础的处理
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
    
    def _enrich_single_project_tweet(self, tweet: Tweet, 
                                   user_data_map: Dict[str, Dict[str, Any]]) -> Optional[Tweet]:
        """
        增强单条项目推文
        
        Args:
            tweet: 推文对象
            user_data_map: 用户数据映射
            
        Returns:
            增强后的推文对象
        """
        try:
            self.logger.debug(f"开始简化增强项目推文 {tweet.id_str}")
            
            # 1. 设置 kol_id 和 user_name（直接从user_data获取）
            if tweet.id_str in user_data_map:
                user_data = user_data_map[tweet.id_str]
                tweet.kol_id = user_data.get('id_str')
                tweet.user_name = user_data.get('screen_name')

                # 2. 生成推文URL（使用实际用户名）
                screen_name = user_data.get('screen_name', 'unknown')
                tweet.tweet_url = f"https://x.com/{screen_name}/status/{tweet.id_str}"
            else:
                tweet.kol_id = None
                tweet.user_name = None
                tweet.tweet_url = f"https://x.com/unknown/status/{tweet.id_str}"
            
            # 3. 简化情绪分析
            tweet.sentiment = self._simple_sentiment_analysis(tweet.full_text)

            # 3.1 设置转发状态为False（项目推文一般不是转发）
            # 注意：如果需要从API数据检测，需要传入api_data参数
            tweet.is_retweet = False

            # 4. 简化公告检测
            tweet.isAnnounce = self._simple_announcement_detection(tweet.full_text)
            # 如果是公告推文，生成AI总结
            if tweet.isAnnounce == 1:
                tweet.summary = self._generate_announcement_summary(tweet.full_text)
            else:
                tweet.summary = None
            
            # 5. 简化活动检测
            tweet.is_activity = self._simple_activity_detection(tweet.full_text)
            # 如果是活动推文，生成结构化活动详情
            if tweet.is_activity == 1:
                tweet.activity_detail = self._generate_activity_detail(tweet.full_text, tweet.id_str)
            else:
                tweet.activity_detail = None
            
            # 6. 简化链接提取
            tweet.link_url = self._simple_link_extraction(tweet.full_text)
            
            # 7. 其他字段设置为默认值
            tweet.project_tag = None
            tweet.token_tag = None
            
            self.logger.info(f"项目推文 {tweet.id_str} 简化增强完成: kol_id={tweet.kol_id}, sentiment={tweet.sentiment}, isAnnounce={tweet.isAnnounce}, is_activity={tweet.is_activity}")
            return tweet
            
        except Exception as e:
            self.logger.error(f"简化增强项目推文 {tweet.id_str} 失败: {e}")
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
            # 1. 设置kol_id和user_name（直接从用户数据获取）
            if tweet.id_str in user_data_map:
                user_data = user_data_map[tweet.id_str]
                tweet.kol_id = user_data.get('id_str')
                tweet.user_name = user_data.get('screen_name')

                # 2. 生成推文URL
                screen_name = user_data.get('screen_name', 'unknown')
                tweet.tweet_url = f"https://x.com/{screen_name}/status/{tweet.id_str}"
            else:
                tweet.kol_id = None
                tweet.user_name = None
                tweet.tweet_url = f"https://x.com/unknown/status/{tweet.id_str}"
            
            # 3. 设置默认值
            tweet.sentiment = None
            tweet.is_retweet = False
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

    def _detect_retweet_status(self, api_data: Dict[str, Any]) -> bool:
        """
        从API数据中检测是否为转发推文

        Args:
            api_data: Twitter API返回的原始推文数据

        Returns:
            True表示是转发，False表示不是
        """
        try:
            if not api_data:
                return False

            # 检查是否包含retweeted_status字段
            # 当推文是转发时，Twitter API会返回retweeted_status对象
            has_retweeted_status = 'retweeted_status' in api_data and api_data.get('retweeted_status')

            if has_retweeted_status:
                self.logger.debug(f"检测到转发推文: {api_data.get('id_str')}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"检测转发状态失败: {e}")
            return False

    def _simple_sentiment_analysis(self, text: str) -> Optional[str]:
        """
        简化的情绪分析 - 仅基于关键词
        
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
        简化的公告检测 - 仅基于关键词
        
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
        简化的活动检测 - 仅基于关键词
        
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
                
            # 匹配HTTP/HTTPS链接
            url_pattern = r'https?://[^\s]+'
            urls = re.findall(url_pattern, text)
            
            return urls[0] if urls else None
            
        except Exception as e:
            self.logger.error(f"简化链接提取失败: {e}")
            return None
    
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
            
            # 获取ChatGPT客户端
            chatgpt_client = self._get_chatgpt_client()
            if not chatgpt_client:
                self.logger.warning("ChatGPT客户端不可用，无法生成公告总结")
                return None
            
            # 使用ChatGPT生成公告总结
            summary = chatgpt_client.summarize_announcement(text)
            
            if summary:
                self.logger.info(f"成功生成公告总结: {summary}")
                return summary
            else:
                self.logger.warning("公告总结生成失败，返回None")
                return None
                
        except Exception as e:
            self.logger.error(f"生成公告总结失败: {e}")
            return None
    
    def _generate_activity_detail(self, text: str, tweet_id: str) -> Optional[str]:
        """
        为活动推文生成结构化活动详情（JSON格式）
        
        Args:
            text: 推文文本
            tweet_id: 推文ID
            
        Returns:
            活动详情JSON字符串，失败则返回None
        """
        try:
            if not text or len(text.strip()) < 10:
                return None
            
            # 获取ChatGPT客户端
            chatgpt_client = self._get_chatgpt_client()
            if not chatgpt_client:
                self.logger.warning("ChatGPT客户端不可用，无法生成活动详情")
                return None
            
            # 生成推文URL（使用通用格式）
            tweet_url = f"https://twitter.com/i/status/{tweet_id}"
            
            # 使用ChatGPT提取结构化数据
            activity_data = chatgpt_client.extract_activity_structured_data(
                tweet_text=text,
                tweet_url=tweet_url,
                tweet_time=""  # 简化版本不传时间
            )
            
            if activity_data:
                # 将结构化数据转换为JSON字符串
                activity_detail_json = json.dumps(activity_data, ensure_ascii=False)
                self.logger.info(f"成功生成活动详情: {activity_data.get('title', '未知活动')}")
                return activity_detail_json
            else:
                self.logger.warning(f"无法提取活动结构化数据: {tweet_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"生成活动详情失败: {e}")
            return None


# 全局实例
simple_tweet_enricher = SimpleTweetEnricher()