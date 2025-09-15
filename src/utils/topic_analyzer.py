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
        从推文列表中提取话题
        
        Args:
            tweets: 推文列表
            
        Returns:
            话题列表
        """
        self.logger.info(f"开始从 {len(tweets)} 条推文中提取话题...")
        
        topics_dict = {}  # 用于话题聚合
        processed_count = 0
        
        for tweet in tweets:
            if not tweet.full_text:
                continue
                
            try:
                # 使用ChatGPT提取话题
                topic_info = self.chatgpt_client.extract_topic_from_tweet(tweet.full_text)
                
                if topic_info and topic_info.get('topic_name'):
                    topic_name = topic_info['topic_name']
                    
                    # 话题聚合（相同话题名称合并）
                    if topic_name in topics_dict:
                        # 更新现有话题
                        existing_topic = topics_dict[topic_name]
                        existing_topic['tweets'].append(tweet)
                        existing_topic['engagement_total'] += tweet.engagement_total or 0
                    else:
                        # 创建新话题
                        topics_dict[topic_name] = {
                            'topic_name': topic_name,
                            'brief': topic_info.get('brief', ''),
                            'tweets': [tweet],
                            'engagement_total': tweet.engagement_total or 0,
                            'created_at': tweet.created_at_datetime or datetime.now()
                        }
                
                processed_count += 1
                
                if processed_count % 10 == 0:
                    self.logger.info(f"已处理 {processed_count}/{len(tweets)} 条推文")
                
            except Exception as e:
                self.logger.error(f"处理推文失败: {tweet.id_str}, 错误: {e}")
                continue
        
        # 转换为Topic对象列表
        topics = []
        for topic_data in topics_dict.values():
            topic = self._create_topic_from_data(topic_data)
            if topic:
                topics.append(topic)
        
        self.logger.info(f"成功提取 {len(topics)} 个话题")
        return topics
    
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
        if len(tweets) < 2:
            return {"5m": 0.0, "1h": 0.0, "4h": 0.0}
        
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
    
    def _calculate_timeframe_speed(self, sorted_tweets: List[Tweet], window_minutes: int) -> float:
        """
        计算特定时间窗口的传播速度
        
        Args:
            sorted_tweets: 按时间排序的推文列表
            window_minutes: 时间窗口（分钟）
            
        Returns:
            传播速度
        """
        if len(sorted_tweets) < 2:
            return 0.0
        
        # 获取时间窗口内的推文
        end_time = sorted_tweets[-1].created_at_datetime or datetime.now()
        start_time = end_time - timedelta(minutes=window_minutes)
        
        window_tweets = [
            tweet for tweet in sorted_tweets
            if tweet.created_at_datetime and tweet.created_at_datetime >= start_time
        ]
        
        if len(window_tweets) < 2:
            return 0.0
        
        # 计算传播速度指标
        unique_users = set(tweet.id_str[:10] for tweet in window_tweets)  # 简化的用户识别
        total_engagement = sum(
            (tweet.favorite_count or 0) + 
            (tweet.retweet_count or 0) + 
            (tweet.reply_count or 0)
            for tweet in window_tweets
        )
        
        # 传播速度 = (参与用户数 * 总互动数) / 时间窗口(分钟)
        base_speed = (len(unique_users) * total_engagement) / window_minutes
        
        # 病毒式传播检测
        time_intervals = []
        for i in range(1, len(window_tweets)):
            if (window_tweets[i].created_at_datetime and 
                window_tweets[i-1].created_at_datetime):
                interval = (window_tweets[i].created_at_datetime - 
                           window_tweets[i-1].created_at_datetime).total_seconds() / 60
                time_intervals.append(interval)
        
        if time_intervals:
            avg_interval = sum(time_intervals) / len(time_intervals)
            if avg_interval < 1:  # 平均间隔小于1分钟
                viral_multiplier = 2.0
            elif avg_interval < 5:
                viral_multiplier = 1.5
            else:
                viral_multiplier = 1.0
        else:
            viral_multiplier = 1.0
        
        final_speed = base_speed * viral_multiplier
        
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