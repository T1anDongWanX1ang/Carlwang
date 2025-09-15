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
from ..models.tweet import Tweet
from ..models.topic import Topic
from ..models.project import Project
from .advanced_topic_processor import advanced_topic_processor
from .smart_classifier import smart_classifier


class TweetEnricher:
    """推文增强处理器"""
    
    def __init__(self):
        """初始化推文增强器"""
        self.logger = logging.getLogger(__name__)
        self.chatgpt = chatgpt_client
        self.topic_dao = topic_dao
        self.kol_dao = kol_dao
        self.project_dao = ProjectDAO()
        
        # 缓存已知的KOL用户ID，避免重复查询
        self._kol_user_cache = {}
        self._refresh_kol_cache()
    
    def _refresh_kol_cache(self):
        """刷新KOL用户缓存"""
        try:
            kols = self.kol_dao.get_active_kols()
            self._kol_user_cache = {kol.user_id: kol.kol_id for kol in kols}
            self.logger.info(f"刷新KOL缓存，找到 {len(self._kol_user_cache)} 个KOL用户")
        except Exception as e:
            self.logger.error(f"刷新KOL缓存失败: {e}")
            self._kol_user_cache = {}
    
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
                        # 如果增强失败，使用原始推文
                        enriched_tweets.append(tweet)
                        
                except Exception as e:
                    self.logger.error(f"增强推文 {tweet.id_str} 失败: {e}")
                    enriched_tweets.append(tweet)
            
            self.logger.info(f"推文增强完成，处理 {len(enriched_tweets)} 条推文")
            return enriched_tweets
            
        except Exception as e:
            self.logger.error(f"批量增强推文失败: {e}")
            return tweets
    
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
            # 1. 设置 kol_id（从用户数据中获取 user.id_str）
            kol_id = self._extract_kol_id_from_user_data(tweet, user_data_map)
            tweet.kol_id = kol_id
            
            # 2. 生成推文URL
            tweet_url = self._generate_tweet_url(tweet)
            tweet.tweet_url = tweet_url
            
            # 3. 内容质量检查：判断是否为有效的Crypto相关内容
            is_valid = self._validate_crypto_content(tweet.full_text, use_ai=True)
            tweet.is_valid = is_valid
            
            # 4. 仅对有效推文进行进一步分析
            if is_valid:
                # 4.1 情绪分析
                sentiment = self._analyze_tweet_sentiment(tweet.full_text, use_ai=True)
                tweet.sentiment = sentiment
                
                # 4.2 使用智能分类器处理项目和话题
                classification_result = self._classify_and_set_ids(tweet)
                
                # 设置相应的ID字段（确保互斥性）
                if classification_result.content_type == 'project':
                    tweet.project_id = classification_result.project_id
                    tweet.topic_id = None  # 确保topic_id为空
                    tweet.entity_id = classification_result.project_id
                elif classification_result.content_type == 'topic':
                    tweet.project_id = None  # 确保project_id为空
                    tweet.topic_id = classification_result.topic_id
                    tweet.entity_id = classification_result.topic_id
                else:
                    # 未知类型，清空所有分类字段
                    tweet.project_id = None
                    tweet.topic_id = None
                    tweet.entity_id = None
                
                self.logger.info(f"推文 {tweet.id_str} 增强完成: kol_id={kol_id}, valid={is_valid}, sentiment={sentiment}, project_id={tweet.project_id}, topic_id={tweet.topic_id}, entity_id={tweet.entity_id}, url={tweet_url}")
            else:
                # 无效推文不进行话题分析和情绪分析
                tweet.sentiment = None
                tweet.entity_id = None
                tweet.project_id = None
                tweet.topic_id = None
                self.logger.info(f"推文 {tweet.id_str} 标记为无效，kol_id={kol_id}, url={tweet_url}")
            
            return tweet
            
        except Exception as e:
            self.logger.error(f"增强推文 {tweet.id_str} 失败: {e}")
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
            prompt = f"""
            请分析以下推文是否符合以下标准：
            1. 与加密货币、区块链、DeFi、NFT等相关
            2. 不是明显的广告、推广或垃圾内容
            3. 包含有价值的信息、观点或讨论
            
            推文内容: {text}
            
            请只返回 true 或 false：
            - true: 符合标准的有效加密货币相关内容
            - false: 不符合标准（非加密货币相关或明显广告）
            """
            
            response = self.chatgpt._make_request([
                {"role": "system", "content": "你是一个专业的内容质量检查员，专门识别有价值的加密货币内容。"},
                {"role": "user", "content": prompt}
            ], temperature=0.1, max_tokens=10)
            
            if response:
                result = response.strip().lower()
                return result == 'true'
            
            return None
            
        except Exception as e:
            self.logger.warning(f"AI内容验证失败: {e}")
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


# 全局推文增强器实例
tweet_enricher = TweetEnricher()
