"""
Marco数据处理器
基于推文数据生成衍生指标和AI总结
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import math
import statistics

from ..api.chatgpt_client import chatgpt_client
from ..database.tweet_dao import tweet_dao
from ..database.kol_dao import kol_dao
from ..models.marco import MarcoData


class MarcoProcessor:
    """Marco数据处理器"""
    
    def __init__(self):
        """初始化Marco处理器"""
        self.logger = logging.getLogger(__name__)
        self.chatgpt = chatgpt_client
    
    def process_tweets_to_marco(self, timestamp: datetime, 
                               lookback_hours: int = 4, 
                               mock_mode: bool = None) -> Optional[MarcoData]:
        """
        处理推文数据生成Marco数据
        
        Args:
            timestamp: 目标时间戳（30分钟对齐）
            lookback_hours: 回看时间窗口（小时）
            mock_mode: 模拟模式，None表示自动检测
            
        Returns:
            生成的Marco数据
        """
        try:
            # 获取时间窗口内的推文数据
            end_time = timestamp
            start_time = timestamp - timedelta(hours=lookback_hours)
            
            self.logger.info(f"处理时间窗口: {start_time} 到 {end_time}")
            
            # 获取KOL推文（用于情感计算和总结）
            kol_tweets = self._get_kol_tweets_in_range(start_time, end_time)
            
            if not kol_tweets:
                self.logger.warning(f"时间窗口内没有找到KOL推文数据")
                return None
            
            self.logger.info(f"找到 {len(kol_tweets)} 条KOL推文")
            
            # 默认使用真实AI模型进行计算
            if mock_mode is None:
                mock_mode = False  # 默认使用真实AI模型
                self.logger.info("使用真实AI模型生成Marco数据")
            
            # 计算情感指数 - 使用新的基于提示词的算法
            sentiment_index = self._calculate_sentiment_index(kol_tweets, mock_mode)
            
            # 生成AI总结
            summary = self._generate_ai_summary(kol_tweets, timestamp, mock_mode)
            
            # 创建Marco数据
            marco_data = MarcoData.create_for_timestamp(
                timestamp=timestamp,
                sentiment_index=sentiment_index,
                summary=summary
            )
            
            self.logger.info(f"生成Marco数据成功: sentiment={sentiment_index:.2f}")
            return marco_data
            
        except Exception as e:
            self.logger.error(f"处理推文生成Marco数据失败: {e}")
            return None
    
    def _get_kol_tweets_in_range(self, start_time: datetime, 
                                end_time: datetime) -> List[Dict[str, Any]]:
        """
        获取时间范围内的推文数据，使用推文表kol_id关联用户表获取真实粉丝数
        
        Args:
            start_time: 开始时间（最近4小时的起始时间）
            end_time: 结束时间（当前时间）
            
        Returns:
            推文列表，包含按提示词算法计算的权重信息
        """
        try:
            # 使用指定时间窗口内的推文数据（最近4小时）
            sql = """
            SELECT 
                t.id_str,
                t.full_text,
                t.created_at_datetime,
                t.update_time,
                t.retweet_count,
                t.favorite_count,
                t.reply_count,
                t.kol_id,
                u.followers_count,
                u.screen_name,
                u.name
            FROM twitter_tweet t
            LEFT JOIN twitter_user u ON t.kol_id = u.id_str
            WHERE t.full_text IS NOT NULL
            AND LENGTH(t.full_text) > 20
            AND t.kol_id IS NOT NULL
            AND t.update_time >= %s
            AND t.update_time <= %s
            AND t.is_valid = 1
            ORDER BY t.update_time DESC
            LIMIT 5000
            """
            
            results = tweet_dao.db_manager.execute_query(sql, [start_time, end_time])
            
            if not results:
                self.logger.warning("时间范围内没有找到推文数据")
                return []
            
            processed_tweets = []
            for row in results:
                # 计算互动热度系数 = log(转发数 + 点赞数×0.5 + 评论数×0.8)
                retweet_count = row.get('retweet_count', 0) or 0
                favorite_count = row.get('favorite_count', 0) or 0
                reply_count = row.get('reply_count', 0) or 0
                
                interaction_score = retweet_count + favorite_count * 0.5 + reply_count * 0.8
                interaction_coefficient = math.log(max(1, interaction_score))
                
                # 使用真实的粉丝数来计算KOL影响力权重
                real_followers = row.get('followers_count', 0) or 0
                influence_weight = self._calculate_kol_influence_weight(real_followers)
                
                # 计算时间衰减权重（4小时窗口内的推文）
                tweet_time = row.get('update_time') or row.get('created_at_datetime')
                time_decay_coefficient = self._calculate_time_decay_weight(tweet_time, end_time)
                
                # 单条推文权重 = KOL影响力权重 × 互动热度系数 × 时间衰减系数
                total_weight = influence_weight * interaction_coefficient * time_decay_coefficient
                
                tweet_data = {
                    'id': row['id_str'],
                    'content': row['full_text'],
                    'created_at': row['created_at_datetime'],
                    'retweet_count': retweet_count,
                    'favorite_count': favorite_count,
                    'reply_count': reply_count,
                    'kol_id': row.get('kol_id'),
                    'real_followers': real_followers,
                    'screen_name': row.get('screen_name'),
                    'name': row.get('name'),
                    'interaction_coefficient': interaction_coefficient,
                    'influence_weight': influence_weight,
                    'time_decay_coefficient': time_decay_coefficient,
                    'total_weight': total_weight
                }
                processed_tweets.append(tweet_data)
            
            self.logger.info(f"找到 {len(processed_tweets)} 条推文用于情绪指数计算")
            return processed_tweets
            
        except Exception as e:
            self.logger.error(f"获取推文失败: {e}")
            return []
    
    def _estimate_followers_from_engagement(self, retweet_count: int, favorite_count: int, reply_count: int) -> int:
        """
        根据互动数据估算用户粉丝数
        
        这是一个简化的估算方法，因为无法直接获取用户粉丝数
        基于经验：高互动的推文通常来自粉丝较多的KOL
        
        Args:
            retweet_count: 转发数
            favorite_count: 点赞数  
            reply_count: 评论数
            
        Returns:
            估算的粉丝数
        """
        # 计算总互动数
        total_engagement = retweet_count + favorite_count + reply_count
        
        # 基于互动数估算粉丝数（经验公式，可调整）
        if total_engagement >= 1000:
            return 1_000_000  # 高互动推文，估算为100万粉丝KOL
        elif total_engagement >= 100:
            return 100_000    # 中等互动，估算为10万粉丝KOL
        elif total_engagement >= 10:
            return 10_000     # 低互动，估算为1万粉丝KOL
        else:
            return 1_000      # 极低互动，估算为小KOL
    
    
    def _calculate_kol_influence_weight(self, followers_count: int) -> float:
        """
        根据粉丝数计算KOL影响力权重
        
        Args:
            followers_count: 粉丝数量
            
        Returns:
            影响力权重值
        """
        if followers_count >= 10_000_000:  # 1000万粉丝
            return 1.0
        elif followers_count >= 1_000_000:  # 100万粉丝
            return 0.8
        elif followers_count >= 100_000:  # 10万粉丝
            return 0.6
        elif followers_count >= 10_000:  # 1万粉丝
            return 0.4
        else:
            return 0.2  # 小于1万粉丝，给予最低权重
    
    def _calculate_sentiment_index(self, kol_tweets: List[Dict[str, Any]], mock_mode: bool = False) -> float:
        """
        根据用户提供的算法计算整体情感指数
        
        计算逻辑：
        单条推文权重 = KOL影响力权重 × 互动热度系数 × 时间衰减系数
        整个加密推特的情绪指数 = 50 + (Bullish权重总和 - Bearish权重总和) / 总权重 × 50
        
        Args:
            kol_tweets: KOL推文列表
            mock_mode: 模拟模式，不调用ChatGPT API
            
        Returns:
            情感指数 (0-100)
        """
        try:
            if not kol_tweets:
                return 50.0  # 默认中性
            
            # 初始化权重累计
            bullish_weight_sum = 0.0
            bearish_weight_sum = 0.0
            total_weight = 0.0
            
            processed_count = 0
            
            for tweet in kol_tweets:
                content = tweet.get('content', '')
                if not content or len(content) < 10:
                    continue
                
                # 获取预计算的权重
                tweet_weight = tweet.get('total_weight', 0)
                if tweet_weight <= 0:
                    continue
                
                total_weight += tweet_weight
                processed_count += 1
                
                # 分析推文情绪倾向
                if mock_mode:
                    # 模拟模式：基于内容关键词简单判断情绪
                    sentiment_tendency = self._analyze_sentiment_tendency_mock(content)
                else:
                    # 使用ChatGPT分析情绪倾向
                    sentiment_tendency = self._analyze_sentiment_tendency_ai(content)
                
                # 根据情绪倾向累计权重
                if sentiment_tendency == 'bullish':
                    bullish_weight_sum += tweet_weight
                elif sentiment_tendency == 'bearish':
                    bearish_weight_sum += tweet_weight
                # neutral情绪不计入正负情绪权重
                
                self.logger.debug(f"推文情绪分析: tendency={sentiment_tendency}, weight={tweet_weight:.4f}")
            
            if total_weight <= 0:
                self.logger.warning("总权重为0，返回中性情绪指数")
                return 50.0
            
            # 按照用户提供的公式计算情绪指数
            # 整个加密推特的情绪指数 = 50 + (Bullish权重总和 - Bearish权重总和) / 总权重 × 50
            sentiment_index = 50 + ((bullish_weight_sum - bearish_weight_sum) / total_weight) * 50
            
            # 确保在0-100范围内
            sentiment_index = max(0.0, min(100.0, sentiment_index))
            
            self.logger.info(f"情绪指数计算完成: {sentiment_index:.2f} "
                           f"(处理{processed_count}条推文, 总权重:{total_weight:.2f}, "
                           f"Bullish权重:{bullish_weight_sum:.2f}, Bearish权重:{bearish_weight_sum:.2f})")
            
            return round(sentiment_index, 2)
            
        except Exception as e:
            self.logger.error(f"计算情感指数失败: {e}")
            return 50.0
    
    def _analyze_sentiment_tendency_mock(self, content: str) -> str:
        """
        模拟模式下分析推文情绪倾向
        
        Args:
            content: 推文内容
            
        Returns:
            情绪倾向: 'bullish', 'bearish', 'neutral'
        """
        content_lower = content.lower()
        
        # 乐观关键词
        bullish_keywords = ['moon', 'bull', 'pump', 'up', 'rise', 'buy', 'long', 'bullish', 
                           '牛市', '上涨', '买入', '看涨', '涨', '拉升', '突破']
        
        # 悲观关键词  
        bearish_keywords = ['bear', 'dump', 'down', 'crash', 'sell', 'short', 'bearish', 'drop',
                           '熊市', '下跌', '卖出', '看跌', '跌', '崩盘', '暴跌', '回调']
        
        bullish_count = sum(1 for keyword in bullish_keywords if keyword in content_lower)
        bearish_count = sum(1 for keyword in bearish_keywords if keyword in content_lower)
        
        if bullish_count > bearish_count:
            return 'bullish'
        elif bearish_count > bullish_count:
            return 'bearish'
        else:
            return 'neutral'
    
    def _analyze_sentiment_tendency_ai(self, content: str) -> str:
        """
        使用AI分析推文情绪倾向
        
        Args:
            content: 推文内容
            
        Returns:
            情绪倾向: 'bullish', 'bearish', 'neutral'
        """
        try:
            prompt = f"""
            请分析以下加密货币相关推文的情绪倾向，只需要回答：bullish（看涨）、bearish（看跌）或neutral（中性）。
            
            推文内容：{content}
            
            判断标准：
            - bullish: 表达乐观、看涨、买入建议的内容
            - bearish: 表达悲观、看跌、卖出建议的内容  
            - neutral: 客观分析、中性观点或无明确方向性的内容
            
            请只回答：bullish、bearish或neutral
            """
            
            response = self.chatgpt._make_request([
                {"role": "system", "content": "你是一个专业的加密货币情绪分析专家。"},
                {"role": "user", "content": prompt}
            ], temperature=0.1, max_tokens=10)
            
            if response:
                response = response.strip().lower()
                if 'bullish' in response:
                    return 'bullish'
                elif 'bearish' in response:
                    return 'bearish'
                else:
                    return 'neutral'
            else:
                # AI分析失败，使用模拟方法
                return self._analyze_sentiment_tendency_mock(content)
                
        except Exception as e:
            self.logger.debug(f"AI情绪分析失败: {e}，使用模拟方法")
            return self._analyze_sentiment_tendency_mock(content)
    
    def _calculate_time_decay_weight(self, tweet_time: datetime, 
                                   current_time: datetime) -> float:
        """
        计算时间衰减权重（4小时窗口内）
        
        Args:
            tweet_time: 推文时间
            current_time: 当前时间
            
        Returns:
            时间权重 (0.6-1.0)
        """
        if not tweet_time:
            return 0.8  # 默认权重
        
        try:
            time_diff_hours = (current_time - tweet_time).total_seconds() / 3600
            
            # 4小时窗口内的时间衰减函数: 越新的推文权重越高
            # 0-0.5小时: 1.0
            # 0.5-1小时: 0.95
            # 1-2小时: 0.85  
            # 2-3小时: 0.75
            # 3-4小时: 0.6
            if time_diff_hours <= 0.5:
                return 1.0
            elif time_diff_hours <= 1:
                return 0.95
            elif time_diff_hours <= 2:
                return 0.85
            elif time_diff_hours <= 3:
                return 0.75
            elif time_diff_hours <= 4:
                return 0.6
            else:
                # 超过4小时的推文（理论上不应该出现在查询结果中）
                return 0.5
            
        except Exception:
            return 0.8
    
    def _calculate_engagement_weight(self, engagement_total: int) -> float:
        """
        计算互动权重
        
        Args:
            engagement_total: 总互动数
            
        Returns:
            互动权重 (0.8-1.2)
        """
        if engagement_total <= 0:
            return 0.8  # 低权重
        
        # 对数缩放避免极端值
        log_engagement = math.log10(engagement_total + 1)
        
        # 映射到权重范围
        if log_engagement <= 1:  # 少于10个互动
            return 0.8
        elif log_engagement <= 2:  # 10-100个互动
            return 0.9 + (log_engagement - 1) * 0.2  # 0.9-1.1
        elif log_engagement <= 3:  # 100-1000个互动
            return 1.1 + (log_engagement - 2) * 0.1  # 1.1-1.2
        else:  # 超过1000个互动
            return 1.2
    
    def _generate_ai_summary(self, kol_tweets: List[Dict[str, Any]], 
                           timestamp: datetime, mock_mode: bool = False) -> str:
        """
        生成AI总结
        
        Args:
            kol_tweets: KOL推文列表
            timestamp: 时间戳
            mock_mode: 模拟模式
            
        Returns:
            AI总结文本
        """
        try:
            if not kol_tweets:
                return "No significant KOL opinions available in the current time window."
            
            # 如果是模拟模式，生成模拟总结
            if mock_mode:
                return self._generate_mock_summary(kol_tweets, timestamp)
            
            # 筛选重要推文进行总结（基于互动量和影响力）
            important_tweets = self._filter_important_tweets(kol_tweets)
            
            if not important_tweets:
                return "No significant KOL opinions found in current dataset."
            
            # 构建总结prompt
            tweets_text = []
            for i, tweet in enumerate(important_tweets[:20], 1):  # 最多20条
                content = tweet.get('content', '')
                screen_name = tweet.get('screen_name', 'unknown')
                real_followers = tweet.get('real_followers', 0)
                total_weight = tweet.get('total_weight', 0)
                
                tweets_text.append(
                    f"{i}. [@{screen_name}, 粉丝:{real_followers}, 权重:{total_weight:.2f}] {content[:200]}..."
                )
            
            tweets_content = "\n".join(tweets_text)
            
            prompt = f"""
            Based on the following important crypto KOL opinions, generate a professional market summary:

            Analysis Time: {timestamp.strftime('%Y-%m-%d %H:%M')}
            KOL Opinion Data (sorted by influence weight):
            {tweets_content}

            Please provide a comprehensive analysis including:
            1. Main trending topics and projects being discussed
            2. Overall market sentiment and expectations from KOLs
            3. Important technical analysis or fundamental viewpoints
            4. Risk warnings or opportunity alerts
            5. Key characteristics of current market sentiment

            Requirements:
            - Objective and professional tone, avoid investment advice
            - Highlight consensus views and points of disagreement
            - Limit to 80 words or less
            - Output in English

            Please return only the summary content without any additional formatting.
            """
            
            summary = self.chatgpt._make_request([
                {"role": "system", "content": "You are a professional cryptocurrency market analyst, skilled at analyzing KOL opinions and generating market summaries."},
                {"role": "user", "content": prompt}
            ], temperature=0.3, max_tokens=120)
            
            if summary:
                self.logger.info(f"生成AI总结成功，长度: {len(summary)}")
                return summary.strip()
            else:
                self.logger.warning("AI总结生成失败，使用模拟模式")
                return self._generate_mock_summary(kol_tweets, timestamp)
            
        except Exception as e:
            self.logger.error(f"生成AI总结失败: {e}，使用模拟模式")
            return self._generate_mock_summary(kol_tweets, timestamp)
    
    def _generate_mock_summary(self, kol_tweets: List[Dict[str, Any]], timestamp: datetime) -> str:
        """
        生成模拟AI总结
        
        Args:
            kol_tweets: KOL推文列表
            timestamp: 时间戳
            
        Returns:
            模拟总结文本
        """
        try:
            total_engagement = sum(tweet.get('engagement_total', 0) for tweet in kol_tweets)
            avg_engagement = total_engagement / len(kol_tweets) if kol_tweets else 0
            
            # 模拟市场情绪
            if avg_engagement > 100:
                market_mood = "active"
                sentiment_desc = "High market attention with relatively positive investor sentiment"
            elif avg_engagement > 50:
                market_mood = "stable"
                sentiment_desc = "Steady market performance with cautious investor outlook"
            else:
                market_mood = "quiet"
                sentiment_desc = "Relatively calm market with low trading activity"
            
            # 模拟热门话题
            import random
            topics = ["Bitcoin", "Ethereum", "DeFi", "NFT", "Layer2", "AI tokens", "RWA", "Meme coins"]
            hot_topics = random.sample(topics, min(3, len(topics)))
            
            summary = f"""
            Based on 4-hour analysis ({timestamp.strftime('%Y-%m-%d %H:%M')}), crypto market shows {market_mood} dynamics. 
            Key discussion focuses on {', '.join(hot_topics)} sectors. {sentiment_desc}. 
            Analysis of {len(kol_tweets)} tweets shows average engagement of {avg_engagement:.1f}. 
            Technical outlook cautiously optimistic. Maintain risk management.
            
            Note: Simulated data for demonstration.
            """
            
            return summary.strip()
            
        except Exception as e:
            self.logger.error(f"生成模拟总结失败: {e}")
            return f"Market analysis based on {len(kol_tweets)} tweets is temporarily unavailable, please try again later."
    
    def _filter_important_tweets(self, kol_tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        筛选重要推文
        
        Args:
            kol_tweets: KOL推文列表
            
        Returns:
            重要推文列表
        """
        try:
            scored_tweets = []
            
            for tweet in kol_tweets:
                content = tweet.get('content', '')
                if len(content) < 20:  # 跳过太短的推文
                    continue
                
                # 使用已计算的权重作为重要性得分
                total_weight = tweet.get('total_weight', 0)
                real_followers = tweet.get('real_followers', 0)
                
                # 内容质量得分（基于长度、关键词等）
                content_score = self._calculate_content_quality_score(content)
                
                # 综合得分：权重 * 内容质量
                total_score = total_weight * (1 + content_score / 100)
                
                scored_tweets.append({
                    **tweet,
                    'importance_score': total_score
                })
            
            # 按得分排序，取前30条
            scored_tweets.sort(key=lambda x: x['importance_score'], reverse=True)
            important_tweets = scored_tweets[:30]
            
            self.logger.info(f"筛选出{len(important_tweets)}条重要推文")
            return important_tweets
            
        except Exception as e:
            self.logger.error(f"筛选重要推文失败: {e}")
            return kol_tweets[:20]  # 默认返回前20条
    
    def _calculate_content_quality_score(self, content: str) -> float:
        """
        计算内容质量得分
        
        Args:
            content: 推文内容
            
        Returns:
            内容质量得分 (0-100)
        """
        try:
            score = 0
            
            # 长度得分
            if len(content) > 100:
                score += 20
            elif len(content) > 50:
                score += 10
            
            # 加密货币关键词得分
            crypto_keywords = ['btc', 'bitcoin', 'eth', 'ethereum', 'crypto', '加密', 
                              'defi', 'nft', 'dao', 'web3', '区块链', '比特币', '以太坊']
            
            content_lower = content.lower()
            keyword_count = sum(1 for keyword in crypto_keywords if keyword in content_lower)
            score += min(30, keyword_count * 5)
            
            # 技术分析关键词得分
            ta_keywords = ['支撑', '阻力', '突破', '回调', '牛市', '熊市', '分析', 'analysis']
            ta_count = sum(1 for keyword in ta_keywords if keyword in content_lower)
            score += min(20, ta_count * 5)
            
            # 数字和价格信息得分
            import re
            if re.search(r'\$[\d,]+', content) or re.search(r'[\d,]+\$', content):
                score += 15
            
            # URL和图片得分（可能包含更多信息）
            if 'http' in content or '图片' in content:
                score += 10
            
            return min(100, score)
            
        except Exception:
            return 50  # 默认得分
    
    def generate_timestamp_sequence(self, start_date: datetime, 
                                  end_date: datetime) -> List[datetime]:
        """
        生成30分钟对齐的时间戳序列
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            时间戳列表
        """
        timestamps = []
        current = start_date.replace(minute=(start_date.minute // 30) * 30, second=0, microsecond=0)
        
        while current <= end_date:
            timestamps.append(current)
            current += timedelta(minutes=30)
        
        return timestamps


# 全局Marco处理器实例
# 全局Marco处理器实例
marco_processor = MarcoProcessor() 