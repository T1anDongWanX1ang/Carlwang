"""
话题分析器
基于derived-metrics-calculation-details.md中的算法实现
"""
import math
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from ..api.chatgpt_client import chatgpt_client
from ..models.tweet import Tweet
from ..models.topic import Topic
from ..utils.logger import get_logger


class TopicAnalyzer:
    """话题分析器"""
    
    def __init__(self):
        """初始化话题分析器"""
        self.logger = get_logger(__name__)
        self.chatgpt_client = chatgpt_client
    
    def extract_topics_from_tweets(self, tweets: List[Tweet]) -> List[Topic]:
        """
        从推文列表中提取话题（优化版本，减少单条推文话题）
        
        Args:
            tweets: 推文列表
            
        Returns:
            话题列表
        """
        self.logger.info(f"开始从 {len(tweets)} 条推文中提取话题...")
        
        # 第一步：预处理和初步分组
        tweet_groups = self._preprocess_and_group_tweets(tweets)
        
        topics_dict = {}  # 用于话题聚合
        processed_count = 0
        
        for group_tweets in tweet_groups:
            try:
                if len(group_tweets) == 1:
                    # 单条推文：使用单推文话题提取
                    tweet = group_tweets[0]
                    topic_info = self._extract_topic_from_single_tweet(tweet)
                else:
                    # 多条推文：使用批量话题提取
                    topic_info = self._extract_topic_from_tweet_group(group_tweets)
                
                if topic_info and topic_info.get('topic_name'):
                    topic_name = topic_info['topic_name']
                    
                    # 智能话题聚合（基于语义相似度）
                    merged_topic_name = self._find_similar_topic(topic_name, topics_dict.keys())
                    
                    if merged_topic_name:
                        # 合并到相似话题
                        existing_topic = topics_dict[merged_topic_name]
                        existing_topic['tweets'].extend(group_tweets)
                        existing_topic['engagement_total'] += sum(t.engagement_total or 0 for t in group_tweets)
                        self.logger.debug(f"话题合并: '{topic_name}' → '{merged_topic_name}'")
                    else:
                        # 创建新话题
                        topics_dict[topic_name] = {
                            'topic_name': topic_name,
                            'brief': topic_info.get('brief', ''),
                            'tweets': group_tweets,
                            'engagement_total': sum(t.engagement_total or 0 for t in group_tweets),
                            'created_at': min(t.created_at_datetime or datetime.now() for t in group_tweets)
                        }
                
                processed_count += len(group_tweets)
                
                if processed_count % 10 == 0:
                    self.logger.info(f"已处理 {processed_count}/{len(tweets)} 条推文")
                
            except Exception as e:
                self.logger.error(f"处理推文组失败, 错误: {e}")
                continue
        
        # 转换为Topic对象列表
        topics = []
        for topic_data in topics_dict.values():
            topic = self._create_topic_from_data(topic_data)
            if topic:
                topics.append(topic)
        
        self.logger.info(f"成功提取 {len(topics)} 个话题")
        return topics
    
    def _preprocess_and_group_tweets(self, tweets: List[Tweet]) -> List[List[Tweet]]:
        """
        预处理推文并进行初步分组
        基于关键词、时间、用户等特征进行分组
        
        Args:
            tweets: 推文列表
            
        Returns:
            推文分组列表
        """
        try:
            # 简单的关键词分组算法
            groups = []
            ungrouped_tweets = tweets.copy()
            
            # 第一轮：基于关键词分组
            while ungrouped_tweets:
                current_tweet = ungrouped_tweets.pop(0)
                current_group = [current_tweet]
                
                # 提取当前推文的关键词
                current_keywords = self._extract_keywords(current_tweet.full_text)
                
                # 查找相似推文
                i = 0
                while i < len(ungrouped_tweets):
                    candidate_tweet = ungrouped_tweets[i]
                    candidate_keywords = self._extract_keywords(candidate_tweet.full_text)
                    
                    # 计算关键词重叠度
                    if self._calculate_keyword_similarity(current_keywords, candidate_keywords) > 0.3:
                        current_group.append(candidate_tweet)
                        ungrouped_tweets.pop(i)
                    else:
                        i += 1
                
                groups.append(current_group)
            
            self.logger.info(f"推文分组完成: {len(tweets)} 条推文 → {len(groups)} 个组")
            
            # 统计分组情况
            group_sizes = [len(g) for g in groups]
            single_tweet_groups = sum(1 for size in group_sizes if size == 1)
            multi_tweet_groups = len(groups) - single_tweet_groups
            
            self.logger.info(f"分组统计: {single_tweet_groups} 个单推文组, {multi_tweet_groups} 个多推文组")
            
            return groups
            
        except Exception as e:
            self.logger.error(f"推文分组失败: {e}")
            # 降级为单独处理
            return [[tweet] for tweet in tweets]
    
    def _extract_keywords(self, text: str) -> set:
        """提取文本关键词（简化版本）"""
        if not text:
            return set()
        
        # 简单的关键词提取
        import re
        
        # 提取话题标签、币种符号、关键术语
        keywords = set()
        
        # 话题标签 #hashtag
        hashtags = re.findall(r'#\w+', text.lower())
        keywords.update(hashtags)
        
        # 币种符号 $SYMBOL
        symbols = re.findall(r'\$[A-Z]{2,10}', text.upper())
        keywords.update(symbols)
        
        # 常见关键词
        crypto_terms = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'defi', 'nft', 'dao', 'dex', 'cex',
            'trading', 'investment', 'market', 'pump', 'dump', 'bull', 'bear',
            'blockchain', 'crypto', 'token', 'coin', 'yield', 'staking', 'mining'
        ]
        
        text_lower = text.lower()
        for term in crypto_terms:
            if term in text_lower:
                keywords.add(term)
        
        return keywords
    
    def _calculate_keyword_similarity(self, keywords1: set, keywords2: set) -> float:
        """计算关键词相似度"""
        if not keywords1 or not keywords2:
            return 0.0
        
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _extract_topic_from_single_tweet(self, tweet: Tweet) -> Dict[str, Any]:
        """
        从单条推文提取话题（更严格的标准）
        """
        try:
            # 对单条推文使用原有方法
            topic_info = self.chatgpt_client.extract_topic_from_tweet(tweet.full_text)
            
            # 额外验证：单条推文话题必须有足够的重要性
            if topic_info and topic_info.get('topic_name'):
                # 检查互动数据，低互动推文归类到通用话题
                engagement = (tweet.favorite_count or 0) + (tweet.retweet_count or 0) * 2
                
                if engagement < 5:  # 低互动推文
                    # 添加通用标识，便于后续合并
                    topic_name = topic_info['topic_name']
                    if not any(word in topic_name.lower() for word in ['市场', 'defi', 'bitcoin', 'crypto']):
                        topic_info['topic_name'] = f"加密货币讨论 - {topic_name}"
            
            return topic_info
            
        except Exception as e:
            self.logger.error(f"单推文话题提取失败: {e}")
            return None
    
    def _extract_topic_from_tweet_group(self, tweets: List[Tweet]) -> Dict[str, Any]:
        """
        从推文组提取话题（优化版本，使用批量处理）
        """
        try:
            if not tweets:
                return None
                
            # 提取推文内容
            tweet_contents = [tweet.full_text for tweet in tweets if tweet.full_text]
            if not tweet_contents:
                return None
            
            # 使用新的批量话题提取方法
            batch_results = self.chatgpt_client.batch_extract_topics_from_tweets(tweet_contents)
            
            # 选择最佳结果（优先选择有内容的、高质量的话题）
            best_result = None
            best_score = 0
            
            for i, result in enumerate(batch_results):
                if result and result.get('topic_name'):
                    # 计算话题质量分数
                    score = self._calculate_topic_quality_score(result, tweets[i] if i < len(tweets) else tweets[0])
                    if score > best_score:
                        best_score = score
                        best_result = result
            
            return best_result
            
        except Exception as e:
            self.logger.error(f"推文组话题提取失败: {e}")
            # 回退到原始方法
            if tweets:
                return self.chatgpt_client.extract_topic_from_tweet(tweets[0].full_text)
            return None
    
    def _calculate_topic_quality_score(self, topic_info: Dict[str, Any], tweet: Tweet) -> float:
        """
        计算话题质量分数，用于选择最佳话题
        """
        score = 0.0
        
        try:
            # 基础分数
            if topic_info.get('topic_name'):
                score += 1.0
            if topic_info.get('brief'):
                score += 0.5
            
            # 话题名称质量
            topic_name = topic_info.get('topic_name', '')
            if len(topic_name) > 3:  # 避免过短的话题名
                score += 0.3
            if not topic_name.startswith('加密货币讨论'):  # 优先非通用话题
                score += 0.5
            
            # 推文互动质量加成
            if tweet:
                engagement = (tweet.favorite_count or 0) + (tweet.retweet_count or 0) * 2
                if engagement > 10:
                    score += 0.3
                elif engagement > 50:
                    score += 0.5
                elif engagement > 100:
                    score += 0.8
            
            return score
            
        except Exception as e:
            self.logger.debug(f"计算话题质量分数失败: {e}")
            return 0.0
    
    def _find_similar_topic(self, topic_name: str, existing_topics: List[str]) -> str:
        """
        查找相似的已存在话题
        
        Args:
            topic_name: 新话题名称
            existing_topics: 已存在的话题名称列表
            
        Returns:
            相似话题名称，如果没有则返回None
        """
        if not existing_topics:
            return None
        
        topic_name_lower = topic_name.lower()
        
        for existing_topic in existing_topics:
            existing_topic_lower = existing_topic.lower()
            
            # 1. 完全相同
            if topic_name_lower == existing_topic_lower:
                return existing_topic
            
            # 2. 包含关系
            if topic_name_lower in existing_topic_lower or existing_topic_lower in topic_name_lower:
                return existing_topic
            
            # 3. 关键词重叠度
            topic_words = set(topic_name_lower.split())
            existing_words = set(existing_topic_lower.split())
            
            if topic_words and existing_words:
                overlap = len(topic_words.intersection(existing_words))
                union = len(topic_words.union(existing_words))
                similarity = overlap / union
                
                if similarity > 0.6:  # 60%相似度阈值
                    return existing_topic
            
            # 4. 特殊规则：通用话题合并
            generic_patterns = ['加密货币讨论', '市场分析', '投资策略', 'defi', 'bitcoin']
            for pattern in generic_patterns:
                if pattern in topic_name_lower and pattern in existing_topic_lower:
                    return existing_topic
        
        return None
    
    def _create_topic_from_data(self, topic_data: Dict[str, Any]) -> Optional[Topic]:
        """
        从话题数据创建Topic对象
        
        Args:
            topic_data: 话题数据字典
            
        Returns:
            Topic对象
        """
        try:
            # DEBUG: 版本标记和输入数据追踪
            self.logger.info("FIXED_VERSION_2025_12_12: 使用修复后的话题创建逻辑")
            self.logger.debug(f"DEBUG: 开始创建话题，topic_data keys: {list(topic_data.keys())}")
            self.logger.debug(f"DEBUG: 话题名称: {topic_data.get('topic_name', 'N/A')}")
            
            tweets = topic_data['tweets']
            
            # 计算基础指标
            popularity = self.calculate_topic_popularity(tweets)
            
            # 计算传播速度
            propagation_speeds = self.calculate_propagation_speeds(tweets)
            
            # 分析散户观点方向
            tweet_contents = [tweet.full_text for tweet in tweets if tweet.full_text]
            mob_direction = self.chatgpt_client.analyze_mob_opinion_direction(tweet_contents)
            
            # 先生成topic_id，用于summary生成
            topic_id = Topic.generate_topic_id()
            self.logger.debug(f"DEBUG: 生成的新topic_id: {topic_id}")
            
            # 将topic_id添加到topic_data中，用于summary生成
            enhanced_topic_data = topic_data.copy()
            enhanced_topic_data['topic_id'] = topic_id
            self.logger.debug(f"DEBUG: enhanced_topic_data中的topic_id: {enhanced_topic_data.get('topic_id')}")
            
            # 生成KOL观点共识总结
            self.logger.debug(f"DEBUG: 调用_generate_enhanced_topic_summary，传入topic_id: {enhanced_topic_data.get('topic_id')}")
            summary = self._generate_enhanced_topic_summary(enhanced_topic_data, tweets)
            self.logger.info(f"话题 {topic_data['topic_name']} 生成summary结果: {'成功' if summary else '失败(None)'}")
            if summary:
                self.logger.debug(f"DEBUG: 生成的summary前150字符: {summary[:150]}...")
                # 解析summary检查topic_id
                try:
                    import json
                    parsed_summary = json.loads(summary)
                    summary_topic_id = parsed_summary.get('topic_id', 'N/A')
                    self.logger.debug(f"DEBUG: Summary中解析的topic_id: '{summary_topic_id}'")
                    self.logger.debug(f"DEBUG: 预期的topic_id: '{topic_id}'")
                    self.logger.debug(f"DEBUG: topic_id匹配: {summary_topic_id == topic_id}")
                except:
                    self.logger.error("DEBUG: 无法解析生成的summary JSON")
            else:
                self.logger.error("DEBUG: summary生成失败或为None")
            
            # 创建Topic对象，使用预生成的topic_id
            topic = Topic(
                topic_id=topic_id,  # 明确指定topic_id
                topic_name=topic_data['topic_name'],
                brief=topic_data['brief'],
                created_at=topic_data.get('created_at'),  # 使用get避免KeyError
                popularity=popularity,
                propagation_speed_5m=propagation_speeds.get('5m'),
                propagation_speed_1h=propagation_speeds.get('1h'),
                propagation_speed_4h=propagation_speeds.get('4h'),
                mob_opinion_direction=mob_direction,
                summary=summary
            )
            
            # 添加热度历史
            self.logger.debug(f"DEBUG: 添加热度历史，热度值: {popularity}")
            topic.add_popularity_history(popularity)
            
            # 最终验证
            self.logger.debug(f"DEBUG: 最终创建的Topic对象:")
            self.logger.debug(f"DEBUG: - topic_id: {topic.topic_id}")
            self.logger.debug(f"DEBUG: - topic_name: {topic.topic_name}")
            self.logger.debug(f"DEBUG: - summary存在: {bool(topic.summary)}")
            self.logger.debug(f"DEBUG: - popularity_history存在: {bool(topic.popularity_history)}")
            
            return topic
            
        except Exception as e:
            self.logger.error(f"创建话题对象失败: {e}")
            return None
    
    def calculate_topic_popularity(self, tweets: List[Tweet]) -> int:
        """
        计算话题热度
        基于derived-metrics-calculation-details.md中的算法
        
        Args:
            tweets: 相关推文列表
            
        Returns:
            热度分数 (0-1000)
        """
        if not tweets:
            return 0
        
        # 1. 推文数量基础分 (40%)
        tweet_count_score = min(1000, len(tweets))
        
        # 2. 互动质量分 (30%)  
        total_engagement = 0
        for tweet in tweets:
            engagement = (
                (tweet.favorite_count or 0) + 
                (tweet.retweet_count or 0) * 2 + 
                (tweet.reply_count or 0) * 1.5
            )
            total_engagement += engagement
        
        engagement_score = min(1000, total_engagement / 10)
        
        # 3. KOL参与度分 (20%) - 简化版本，基于用户多样性
        unique_users = set(tweet.id_str[:10] for tweet in tweets)  # 简化的用户识别
        kol_score = min(1000, len(unique_users) * 10)
        
        # 4. 传播速度加成 (10%)
        propagation_bonus = self._calculate_propagation_bonus(tweets)
        
        popularity = int(
            tweet_count_score * 0.4 + 
            engagement_score * 0.3 + 
            kol_score * 0.2 + 
            propagation_bonus * 0.1
        )
        
        return min(1000, max(0, popularity))
    
    def calculate_propagation_speeds(self, tweets: List[Tweet]) -> Dict[str, float]:
        """
        计算传播速度
        基于derived-metrics-calculation-details.md中的算法
        
        Args:
            tweets: 推文列表
            
        Returns:
            传播速度字典 {"5m": speed, "1h": speed, "4h": speed}
        """
        if not tweets:
            return {"5m": 0.0, "1h": 0.0, "4h": 0.0}
        
        # 单条推文：基于推文传播能力计算潜在速度
        if len(tweets) == 1:
            return self._calculate_single_tweet_propagation_speed(tweets[0])
        
        # 按时间排序
        sorted_tweets = sorted(tweets, key=lambda t: t.created_at_datetime or datetime.now())
        
        speeds = {}
        timeframes = {
            "5m": 5,
            "1h": 60,
            "4h": 240
        }
        
        for timeframe, minutes in timeframes.items():
            speed = self._calculate_timeframe_speed(sorted_tweets, minutes)
            speeds[timeframe] = speed
        
        return speeds
    
    def _calculate_single_tweet_propagation_speed(self, tweet: Tweet) -> Dict[str, float]:
        """
        计算单条推文的传播速度
        基于推文的互动数据预测传播能力
        
        Args:
            tweet: 单条推文
            
        Returns:
            传播速度字典
        """
        try:
            # 获取推文的互动数据
            likes = tweet.favorite_count or 0
            retweets = tweet.retweet_count or 0
            replies = tweet.reply_count or 0
            views = getattr(tweet, 'view_count', 0) or 0
            
            # 计算总互动强度
            engagement_intensity = likes + (retweets * 3) + (replies * 2)
            
            # 计算推文年龄（分钟）
            if tweet.created_at_datetime:
                tweet_age_minutes = (datetime.now() - tweet.created_at_datetime).total_seconds() / 60
                tweet_age_minutes = max(1, tweet_age_minutes)  # 避免除零
            else:
                tweet_age_minutes = 60  # 默认1小时
            
            # 基于互动强度和时间计算传播速度
            # 如果推文很新但已有高互动，说明传播速度快
            if tweet_age_minutes <= 5:
                # 推文发布5分钟内
                speed_5m = engagement_intensity / max(tweet_age_minutes, 0.5)
                speed_1h = speed_5m * 0.6  # 预测1小时内会放缓
                speed_4h = speed_5m * 0.3  # 预测4小时内进一步放缓
            elif tweet_age_minutes <= 60:
                # 推文发布1小时内
                speed_5m = 0  # 5分钟窗口已过
                speed_1h = engagement_intensity / max(tweet_age_minutes, 1)
                speed_4h = speed_1h * 0.5  # 预测4小时内会放缓
            elif tweet_age_minutes <= 240:
                # 推文发布4小时内
                speed_5m = 0
                speed_1h = 0
                speed_4h = engagement_intensity / max(tweet_age_minutes, 1)
            else:
                # 推文发布超过4小时，基于历史数据估算平均速度
                avg_speed = engagement_intensity / tweet_age_minutes
                speed_5m = avg_speed * 2  # 推测早期传播更快
                speed_1h = avg_speed * 1.5
                speed_4h = avg_speed
            
            # 应用阈值限制，避免过高的数值
            speed_5m = min(100, max(0, speed_5m))
            speed_1h = min(50, max(0, speed_1h))
            speed_4h = min(25, max(0, speed_4h))
            
            # 如果有观看数，进一步优化计算
            if views > 0:
                view_factor = min(2.0, views / max(engagement_intensity, 1))
                speed_5m *= view_factor
                speed_1h *= view_factor
                speed_4h *= view_factor
            
            self.logger.debug(f"单条推文传播速度计算: 互动={engagement_intensity}, 年龄={tweet_age_minutes:.1f}分钟")
            self.logger.debug(f"计算结果: 5m={speed_5m:.2f}, 1h={speed_1h:.2f}, 4h={speed_4h:.2f}")
            
            return {
                "5m": round(speed_5m, 2),
                "1h": round(speed_1h, 2), 
                "4h": round(speed_4h, 2)
            }
            
        except Exception as e:
            self.logger.error(f"单条推文传播速度计算失败: {e}")
            return {"5m": 0.0, "1h": 0.0, "4h": 0.0}
    
    def _calculate_timeframe_speed(self, sorted_tweets: List[Tweet], window_minutes: int) -> float:
        """
        计算特定时间窗口的传播速度
        
        Args:
            sorted_tweets: 按时间排序的推文列表
            window_minutes: 时间窗口（分钟）
            
        Returns:
            传播速度
        """
        if len(sorted_tweets) < 1:
            self.logger.debug(f"推文数量不足: {len(sorted_tweets)}")
            return 0.0
        
        # 获取时间窗口内的推文
        end_time = sorted_tweets[-1].created_at_datetime or datetime.now()
        start_time = end_time - timedelta(minutes=window_minutes)
        
        window_tweets = [
            tweet for tweet in sorted_tweets
            if tweet.created_at_datetime and tweet.created_at_datetime >= start_time
        ]
        
        self.logger.debug(f"{window_minutes}分钟窗口内推文数: {len(window_tweets)}")
        
        if len(window_tweets) < 1:
            return 0.0
        
        # 使用推文ID作为用户识别（每条推文代表一个用户参与）
        unique_users = set(tweet.id_str for tweet in window_tweets)
        
        # 计算总互动数
        total_engagement = 0
        for tweet in window_tweets:
            engagement = (tweet.favorite_count or 0) + (tweet.retweet_count or 0) + (tweet.reply_count or 0)
            total_engagement += engagement
        
        self.logger.debug(f"唯一用户数: {len(unique_users)}, 总互动数: {total_engagement}")
        
        # 改进的传播速度公式
        if total_engagement == 0:
            # 如果没有互动数据，使用推文数量作为基础指标
            base_speed = len(window_tweets) / window_minutes * 10  # 乘以10提高数值可见性
        else:
            # 传播速度 = (参与用户数 + 总互动数) / 时间窗口(分钟)
            base_speed = (len(unique_users) + total_engagement) / window_minutes
        
        # 病毒式传播检测
        viral_multiplier = 1.0
        if len(window_tweets) >= 2:
            time_intervals = []
            for i in range(1, len(window_tweets)):
                if (window_tweets[i].created_at_datetime and 
                    window_tweets[i-1].created_at_datetime):
                    interval = (window_tweets[i].created_at_datetime - 
                               window_tweets[i-1].created_at_datetime).total_seconds() / 60
                    time_intervals.append(interval)
            
            if time_intervals:
                avg_interval = sum(time_intervals) / len(time_intervals)
                self.logger.debug(f"平均推文间隔: {avg_interval:.2f}分钟")
                
                if avg_interval < 1:  # 平均间隔小于1分钟
                    viral_multiplier = 2.0
                elif avg_interval < 5:
                    viral_multiplier = 1.5
                else:
                    viral_multiplier = 1.0
        
        final_speed = base_speed * viral_multiplier
        
        self.logger.debug(f"{window_minutes}分钟传播速度: {final_speed:.2f} (基础:{base_speed:.2f}, 倍数:{viral_multiplier})")
        
        return round(final_speed, 2)
    
    def _calculate_propagation_bonus(self, tweets: List[Tweet]) -> float:
        """
        计算传播速度加成
        
        Args:
            tweets: 推文列表
            
        Returns:
            传播加成分数
        """
        speeds = self.calculate_propagation_speeds(tweets)
        speed_5m = speeds.get('5m', 0)
        speed_1h = speeds.get('1h', 0)
        
        # 病毒式传播检测
        if speed_5m > 50 and speed_1h > 100:
            return 500  # 病毒式传播加成
        elif speed_5m > 20:
            return 200  # 快速传播加成
        else:
            return 0
    
    def cluster_similar_topics(self, topics: List[Topic], similarity_threshold: float = 0.8) -> List[Topic]:
        """
        聚类相似话题
        
        Args:
            topics: 话题列表
            similarity_threshold: 相似度阈值
            
        Returns:
            聚类后的话题列表
        """
        if len(topics) <= 1:
            return topics
        
        # 简化版本：基于话题名称的相似性聚类
        clustered_topics = []
        used_indices = set()
        
        for i, topic in enumerate(topics):
            if i in used_indices:
                continue
                
            # 找到相似的话题
            similar_topics = [topic]
            used_indices.add(i)
            
            for j, other_topic in enumerate(topics[i+1:], i+1):
                if j in used_indices:
                    continue
                    
                # 简单的相似性检测（基于关键词重叠）
                if self._are_topics_similar(topic.topic_name, other_topic.topic_name):
                    similar_topics.append(other_topic)
                    used_indices.add(j)
            
            # 合并相似话题
            if len(similar_topics) > 1:
                merged_topic = self._merge_topics(similar_topics)
                clustered_topics.append(merged_topic)
            else:
                clustered_topics.append(topic)
        
        self.logger.info(f"话题聚类: {len(topics)} → {len(clustered_topics)}")
        return clustered_topics
    
    def _are_topics_similar(self, topic1: str, topic2: str) -> bool:
        """
        判断两个话题是否相似
        
        Args:
            topic1: 话题1名称
            topic2: 话题2名称
            
        Returns:
            是否相似
        """
        # 简化版本：基于关键词重叠
        words1 = set(topic1.lower().split())
        words2 = set(topic2.lower().split())
        
        if not words1 or not words2:
            return False
        
        # 计算Jaccard相似度
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        similarity = len(intersection) / len(union)
        return similarity > 0.5  # 50%相似度阈值
    
    def _merge_topics(self, topics: List[Topic]) -> Topic:
        """
        合并相似话题
        
        Args:
            topics: 相似话题列表
            
        Returns:
            合并后的话题
        """
        if not topics:
            return None
        
        if len(topics) == 1:
            return topics[0]
        
        # 选择热度最高的话题作为主话题
        main_topic = max(topics, key=lambda t: t.popularity or 0)
        
        # 合并数据
        total_popularity = sum(t.popularity or 0 for t in topics)
        
        # 合并简介（如果主话题的简介较短，补充其他话题的信息）
        brief = main_topic.brief or ""
        if len(brief) < 50:
            for topic in topics:
                if topic != main_topic and topic.brief and len(topic.brief) > len(brief):
                    brief = topic.brief
        
        # 合并KOL观点
        all_kol_opinions = []
        for topic in topics:
            if topic.kol_opinions:
                all_kol_opinions.extend(topic.kol_opinions)
        
        # 创建合并后的话题
        merged_topic = Topic(
            topic_name=main_topic.topic_name,
            brief=brief,
            created_at=min(t.created_at for t in topics if t.created_at),
            popularity=total_popularity,
            propagation_speed_5m=max(t.propagation_speed_5m or 0 for t in topics),
            propagation_speed_1h=max(t.propagation_speed_1h or 0 for t in topics),
            propagation_speed_4h=max(t.propagation_speed_4h or 0 for t in topics),
            kol_opinions=all_kol_opinions,
            mob_opinion_direction=main_topic.mob_opinion_direction,
            summary=main_topic.summary
        )
        
        return merged_topic
    
    def update_topic_with_new_tweets(self, existing_topic: Topic, new_tweets: List[Tweet]) -> Topic:
        """
        使用新推文更新现有话题
        
        Args:
            existing_topic: 现有话题
            new_tweets: 新推文列表
            
        Returns:
            更新后的话题
        """
        try:
            # 重新计算热度
            new_popularity = self.calculate_topic_popularity(new_tweets)
            updated_popularity = (existing_topic.popularity or 0) + new_popularity
            
            # 重新计算传播速度
            propagation_speeds = self.calculate_propagation_speeds(new_tweets)
            
            # 更新散户观点方向
            new_tweet_contents = [tweet.full_text for tweet in new_tweets if tweet.full_text]
            if new_tweet_contents:
                mob_direction = self.chatgpt_client.analyze_mob_opinion_direction(new_tweet_contents)
            else:
                mob_direction = existing_topic.mob_opinion_direction
            
            # 更新总结（使用增强版方法）
            topic_data_for_update = {
                'topic_id': existing_topic.topic_id,  # 使用现有话题的topic_id
                'topic_name': existing_topic.topic_name,
                'brief': existing_topic.brief,
                'category': 'crypto',
                'key_entities': [],
                'created_at': existing_topic.created_at
            }
            updated_summary = self._generate_enhanced_topic_summary(topic_data_for_update, new_tweets)
            
            # 更新话题对象
            existing_topic.popularity = updated_popularity
            existing_topic.propagation_speed_5m = propagation_speeds.get('5m')
            existing_topic.propagation_speed_1h = propagation_speeds.get('1h')
            existing_topic.propagation_speed_4h = propagation_speeds.get('4h')
            existing_topic.mob_opinion_direction = mob_direction
            existing_topic.summary = updated_summary or existing_topic.summary
            existing_topic.update_time = datetime.now()
            
            # 添加热度历史记录
            existing_topic.add_popularity_history(updated_popularity)
            
            return existing_topic
            
        except Exception as e:
            self.logger.error(f"更新话题失败: {e}")
            return existing_topic
    
    def calculate_topic_popularity(self, tweets: List[Tweet]) -> int:
        """
        计算话题热度（实现derived-metrics-calculation-details.md中的算法）
        
        Args:
            tweets: 推文列表
            
        Returns:
            热度分数
        """
        if not tweets:
            return 0
        
        # 1. 推文数量基础分 (40%)
        tweet_count_score = min(1000, len(tweets))
        
        # 2. 互动质量分 (30%)  
        total_engagement = 0
        for tweet in tweets:
            engagement = (
                (tweet.favorite_count or 0) + 
                (tweet.retweet_count or 0) * 2 + 
                (tweet.reply_count or 0) * 1.5
            )
            total_engagement += engagement
        
        engagement_score = min(1000, total_engagement / 10)
        
        # 3. KOL参与度分 (20%) - 简化版本
        # 这里可以后续集成真正的KOL识别系统
        unique_users = set(tweet.id_str[:10] for tweet in tweets)
        kol_score = min(1000, len(unique_users) * 20)
        
        # 4. 传播速度加成 (10%)
        propagation_bonus = self._calculate_propagation_bonus(tweets)
        
        popularity = int(
            tweet_count_score * 0.4 + 
            engagement_score * 0.3 + 
            kol_score * 0.2 + 
            propagation_bonus * 0.1
        )
        
        return min(1000, max(0, popularity))
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取分析统计信息
        
        Returns:
            统计信息字典
        """
        chatgpt_stats = self.chatgpt_client.get_statistics()
        
        return {
            'chatgpt_requests': chatgpt_stats['total_requests'],
            'chatgpt_success_rate': chatgpt_stats['success_rate'],
            'chatgpt_errors': chatgpt_stats['error_count']
        }
    
    def _generate_enhanced_topic_summary(self, topic_data: Dict[str, Any], tweets: List[Any]) -> Optional[str]:
        """
        生成增强版的话题总结（始终使用大模型KOL观点分析格式）
        
        Args:
            topic_data: 话题数据
            tweets: 相关推文列表
            
        Returns:
            KOL观点共识总结
        """
        try:
            self.logger.debug(f"开始生成AI总结，推文数量: {len(tweets)}")
            
            if not tweets:
                self.logger.warning(f"话题 {topic_data.get('topic_name')} 没有推文数据")
                return None
            
            # 构建完整的话题数据结构
            # 直接使用传入的topic_id，因为在调用前已确保格式正确
            topic_id = topic_data.get('topic_id', '')
            self.logger.debug(f"DEBUG: _generate_enhanced_topic_summary接收到的topic_id: '{topic_id}'")
            
            if not topic_id:
                # 如果仍然没有topic_id，生成一个临时的（这不应该发生）
                import hashlib
                topic_name = topic_data.get('topic_name', '')
                if topic_name:
                    topic_id = f"topic_{hashlib.md5(topic_name.encode()).hexdigest()}"
                else:
                    topic_id = f"topic_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                self.logger.warning(f"DEBUG: topic_data缺少topic_id，生成临时ID: {topic_id}")
            else:
                self.logger.debug(f"DEBUG: 使用传入的topic_id: {topic_id}")
            
            enhanced_topic_data = {
                'topic_id': topic_id,
                'topic_name': topic_data.get('topic_name', ''),
                'category': topic_data.get('category', 'crypto'),
                'key_entities': topic_data.get('key_entities', []),
                'timestamp': topic_data.get('created_at', datetime.now()).isoformat() if isinstance(topic_data.get('created_at'), datetime) else str(topic_data.get('created_at', '')),
                'brief': topic_data.get('brief', ''),
                'related_tweets': []
            }
            
            # 构建所有推文数据（不再区分KOL和非KOL，都使用大模型分析）
            for tweet in tweets:
                tweet_data = {
                    'id_str': getattr(tweet, 'id_str', ''),
                    'kol_id': getattr(tweet, 'kol_id', '') or '',
                    'full_text': getattr(tweet, 'full_text', '')
                }
                enhanced_topic_data['related_tweets'].append(tweet_data)
            
            kol_count = sum(1 for tweet in tweets if getattr(tweet, 'kol_id', None))
            self.logger.info(f"话题 {topic_data.get('topic_name')} 使用AI分析方法，总推文{len(tweets)}条，KOL推文{kol_count}条")
            
            # 始终使用KOL共识分析方法（大模型）
            result = self.chatgpt_client.generate_kol_consensus_summary(enhanced_topic_data)
            
            if result:
                self.logger.debug(f"AI分析返回结果: {'有内容' if result else 'None'}")
                
                # 验证和修正返回格式（更严格的验证）
                try:
                    import json
                    parsed = json.loads(result)
                    
                    # 强制修正topic_id字段（不管AI返回什么）
                    original_topic_id = parsed.get('topic_id', '')
                    self.logger.debug(f"DEBUG: 修正前解析的topic_id: '{original_topic_id}'")
                    self.logger.debug(f"DEBUG: 预期的正确topic_id: '{topic_id}'")
                    
                    if original_topic_id != topic_id:
                        self.logger.warning(f"DEBUG: 强制修正topic_id: '{original_topic_id}' -> '{topic_id}'")
                        parsed['topic_id'] = topic_id
                        self.logger.debug(f"DEBUG: 修正后的topic_id: '{parsed['topic_id']}'")
                    else:
                        self.logger.debug(f"DEBUG: topic_id无需修正，已正确")
                    
                    if 'summary' in parsed:
                        for viewpoint in parsed['summary']:
                            if 'related_tweets' in viewpoint:
                                # 确保related_tweets包含推文ID而不是推文内容或描述
                                tweet_refs = viewpoint['related_tweets']
                                tweet_ids = []
                                
                                for ref in tweet_refs:
                                    if isinstance(ref, str):
                                        ref = ref.strip()
                                        # 检查是否是推文ID格式（纯数字，长度在10-25之间）
                                        if ref.isdigit() and 10 <= len(ref) <= 25:
                                            tweet_ids.append(ref)
                                        elif len(ref) > 50 or not ref.isdigit():
                                            # 长文本或非ID，查找对应的推文ID
                                            for tweet in tweets:
                                                tweet_text = getattr(tweet, 'full_text', '')
                                                if ref in tweet_text or tweet_text[:30] in ref:
                                                    tweet_id = getattr(tweet, 'id_str', '')
                                                    if tweet_id and tweet_id not in tweet_ids:
                                                        tweet_ids.append(tweet_id)
                                                    break
                                        elif ref in ["initial_discussion", "discussion", "mentioned", "placeholder"] or len(ref) < 10:
                                            # 处理AI生成的占位符或无效ID，用真实推文ID替换
                                            for tweet in tweets:
                                                tweet_id = getattr(tweet, 'id_str', '')
                                                if tweet_id and tweet_id not in tweet_ids:
                                                    tweet_ids.append(tweet_id)
                                                    self.logger.warning(f"替换无效的related_tweets: '{ref}' -> '{tweet_id}'")
                                                    break
                                        else:
                                            # 其他情况，假设是推文ID
                                            tweet_ids.append(ref)
                                
                                # 确保至少有一个推文ID
                                if not tweet_ids and tweets:
                                    tweet_ids.append(getattr(tweets[0], 'id_str', ''))
                                
                                viewpoint['related_tweets'] = tweet_ids[:3]  # 限制数量
                    
                    # 重新序列化
                    result = json.dumps(parsed, ensure_ascii=False)
                    self.logger.debug(f"修正后的AI结果: {result[:200]}...")
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"AI返回的JSON格式错误: {e}")
                    # JSON格式错误，保持原样
                    pass
                
                return result
            else:
                self.logger.warning(f"AI分析返回空结果")
                return None
            
        except Exception as e:
            self.logger.error(f"生成AI话题总结失败: {e}")
            return None


# 全局话题分析器实例已移除 - 使用类直接实例化以确保使用最新代码
# topic_analyzer = TopicAnalyzer() 