"""
KOL分析器
基于derived-metrics-calculation-details.md中的算法实现
"""
import math
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ..api.chatgpt_client import chatgpt_client
from ..models.user import TwitterUser
from ..models.tweet import Tweet
from ..models.kol import KOL
from ..utils.logger import get_logger


class KOLAnalyzer:
    """KOL分析器"""
    
    def __init__(self):
        """初始化KOL分析器"""
        self.logger = get_logger(__name__)
        self.chatgpt_client = chatgpt_client
        
        # 影响力评分阈值
        self.min_followers_for_kol = 1000  # 最小粉丝数
        self.min_influence_score = 30  # 最小影响力分数
    
    def analyze_user_as_kol(self, user: TwitterUser, user_tweets: List[Tweet] = None) -> Optional[KOL]:
        """
        分析用户是否为KOL并生成KOL数据
        
        Args:
            user: 用户对象
            user_tweets: 用户的推文列表（可选）
            
        Returns:
            KOL对象或None（如果不是KOL）
        """
        try:
            self.logger.info(f"分析用户 @{user.screen_name} 是否为KOL...")
            
            # 1. 基础筛选：粉丝数过少直接排除
            if (user.followers_count or 0) < self.min_followers_for_kol:
                self.logger.debug(f"用户 @{user.screen_name} 粉丝数不足，跳过KOL分析")
                return None
            
            # 2. 计算影响力评分
            influence_score = self.calculate_influence_score(user, user_tweets or [])
            
            if influence_score < self.min_influence_score:
                self.logger.debug(f"用户 @{user.screen_name} 影响力评分过低: {influence_score}")
                return None
            
            # 3. 使用ChatGPT进行KOL特征分析
            user_info = {
                'screen_name': user.screen_name,
                'name': user.name,
                'followers_count': user.followers_count,
                'friends_count': user.friends_count,
                'statuses_count': user.statuses_count,
                'description': user.description
            }
            
            tweet_contents = [tweet.full_text for tweet in user_tweets if tweet.full_text] if user_tweets else []
            
            kol_analysis = self.chatgpt_client.analyze_kol_profile(user_info, tweet_contents)
            
            if not kol_analysis:
                self.logger.debug(f"ChatGPT判断 @{user.screen_name} 不是KOL")
                return None
            
            # 4. 生成详细总结
            summary = self.chatgpt_client.generate_kol_summary(
                user_info, 
                tweet_contents, 
                kol_analysis.get('type')
            )
            
            # 5. 创建KOL对象
            kol = KOL(
                kol_id=user.id_str,
                type=kol_analysis.get('type'),
                tag=kol_analysis.get('tag'),
                influence_score=influence_score,
                sentiment=kol_analysis.get('sentiment'),
                summary=summary or kol_analysis.get('summary'),
                trust_rating=kol_analysis.get('trust_rating', 5),
                is_kol100=1 if influence_score >= 80 else 0  # 高影响力KOL纳入KOL100
            )
            
            # 添加历史记录
            kol.add_influence_history(influence_score)
            if kol.sentiment:
                kol.add_sentiment_history(kol.sentiment)
            
            self.logger.info(f"成功识别KOL: @{user.screen_name}, 类型: {kol.type}, 影响力: {influence_score}")
            
            return kol
            
        except Exception as e:
            self.logger.error(f"分析用户KOL特征失败: @{user.screen_name}, 错误: {e}")
            return None
    
    def calculate_influence_score(self, user: TwitterUser, user_tweets: List[Tweet]) -> int:
        """
        计算影响力评分
        基于derived-metrics-calculation-details.md中的算法
        
        Args:
            user: 用户对象
            user_tweets: 用户推文列表
            
        Returns:
            影响力评分 (0-100)
        """
        try:
            # 1. 基础影响力 (30%) - 基于粉丝数和账号质量
            follower_score = min(30, math.log10((user.followers_count or 0) + 1) * 3)
            
            # 2. 内容质量 (25%) - 基于推文数量和活跃度
            if user_tweets and len(user_tweets) > 0:
                # 简化版本：基于推文的互动质量
                total_engagement = sum(
                    (tweet.engagement_total or 0) for tweet in user_tweets
                )
                avg_engagement = total_engagement / len(user_tweets)
                quality_score = min(25, math.log10(avg_engagement + 1) * 5)
            else:
                # 基于推文总数估算
                tweet_count = user.statuses_count or 0
                quality_score = min(25, math.log10(tweet_count + 1) * 3)
            
            # 3. 互动质量 (20%) - 基于真实互动vs bot互动
            if user_tweets:
                engagement_quality = self._calculate_engagement_quality(user_tweets)
            else:
                # 基于粉丝比例估算
                followers = user.followers_count or 0
                following = user.friends_count or 0
                if following > 0:
                    follower_ratio = followers / following
                    engagement_quality = min(1.0, follower_ratio / 10)  # 比例越高质量越好
                else:
                    engagement_quality = 0.5
            
            interaction_score = engagement_quality * 20
            
            # 4. 预测准确性 (15%) - 暂时设为基础分
            # TODO: 后续实现真实的喊单追踪
            accuracy_score = 10  # 基础分
            
            # 5. 网络影响力 (10%) - 基于账号年龄和验证状态
            # 简化版本：基于账号历史
            if user.created_at_datetime:
                try:
                    # 处理时区问题
                    now = datetime.now()
                    if user.created_at_datetime.tzinfo is not None:
                        # 如果有时区信息，转换为UTC
                        from datetime import timezone
                        now = now.replace(tzinfo=timezone.utc)
                        created_at = user.created_at_datetime
                    else:
                        # 如果没有时区信息，假设都是UTC
                        created_at = user.created_at_datetime
                    
                    account_age_days = (now - created_at).days
                    age_score = min(10, account_age_days / 365 * 5)  # 每年5分，最多10分
                except Exception as e:
                    self.logger.warning(f"计算账号年龄失败: {e}")
                    age_score = 5  # 默认分数
            else:
                age_score = 5  # 默认分数
            
            network_score = age_score
            
            # 计算总分
            total_score = (
                follower_score + 
                quality_score + 
                interaction_score + 
                accuracy_score + 
                network_score
            )
            
            final_score = int(min(100, max(0, total_score)))
            
            self.logger.debug(f"影响力评分详情 @{user.screen_name}: "
                            f"粉丝({follower_score:.1f}) + 质量({quality_score:.1f}) + "
                            f"互动({interaction_score:.1f}) + 准确性({accuracy_score:.1f}) + "
                            f"网络({network_score:.1f}) = {final_score}")
            
            return final_score
            
        except Exception as e:
            self.logger.error(f"计算影响力评分失败: @{user.screen_name}, 错误: {e}")
            return 0
    
    def _calculate_engagement_quality(self, tweets: List[Tweet]) -> float:
        """
        计算互动质量（检测bot互动模式）
        基于derived-metrics-calculation-details.md中的算法
        
        Args:
            tweets: 推文列表
            
        Returns:
            互动质量评分 (0.0-1.0)
        """
        if not tweets:
            return 0.0
        
        total_quality = 0
        
        for tweet in tweets:
            # 互动比例分析 - 正常用户互动模式
            like_count = tweet.favorite_count or 0
            retweet_count = tweet.retweet_count or 0
            reply_count = tweet.reply_count or 0
            
            total_engagement = like_count + retweet_count + reply_count
            
            if total_engagement == 0:
                quality = 0
            else:
                # 正常比例: likes > retweets > replies
                like_ratio = like_count / total_engagement
                retweet_ratio = retweet_count / total_engagement
                
                # 异常模式检测 (可能的bot行为)
                if retweet_ratio > 0.8:  # 异常高转发比例
                    quality = 0.3
                elif like_ratio < 0.3:  # 异常低点赞比例
                    quality = 0.5
                else:
                    quality = 1.0
                    
            total_quality += quality
        
        return total_quality / len(tweets)
    
    def batch_analyze_users_as_kols(self, users: List[TwitterUser], 
                                   user_tweets_map: Dict[str, List[Tweet]] = None) -> List[KOL]:
        """
        批量分析用户是否为KOL
        
        Args:
            users: 用户列表
            user_tweets_map: 用户ID到推文列表的映射
            
        Returns:
            KOL列表
        """
        kols = []
        processed_count = 0
        
        for user in users:
            try:
                user_tweets = user_tweets_map.get(user.id_str, []) if user_tweets_map else []
                
                kol = self.analyze_user_as_kol(user, user_tweets)
                
                if kol:
                    kols.append(kol)
                
                processed_count += 1
                
                if processed_count % 10 == 0:
                    self.logger.info(f"已处理 {processed_count}/{len(users)} 个用户")
                
            except Exception as e:
                self.logger.error(f"分析用户失败: @{user.screen_name}, 错误: {e}")
                continue
        
        self.logger.info(f"从 {len(users)} 个用户中识别出 {len(kols)} 个KOL")
        return kols
    
    def update_kol_metrics(self, kol: KOL, new_tweets: List[Tweet] = None) -> KOL:
        """
        更新KOL的指标数据
        
        Args:
            kol: KOL对象
            new_tweets: 新推文列表
            
        Returns:
            更新后的KOL对象
        """
        try:
            # 重新计算影响力评分（如果有新推文数据）
            if new_tweets:
                # 这里需要获取用户信息来重新计算
                # 简化版本：基于新推文的互动质量调整
                engagement_quality = self._calculate_engagement_quality(new_tweets)
                
                # 调整影响力评分
                adjustment = (engagement_quality - 0.5) * 10  # -5 到 +5 的调整
                new_influence_score = max(0, min(100, (kol.influence_score or 0) + adjustment))
                
                if new_influence_score != kol.influence_score:
                    kol.influence_score = int(new_influence_score)
                    kol.add_influence_history(kol.influence_score)
            
            # 更新时间
            kol.last_updated = datetime.now()
            
            return kol
            
        except Exception as e:
            self.logger.error(f"更新KOL指标失败: {kol.kol_id}, 错误: {e}")
            return kol
    
    def identify_kol100_candidates(self, kols: List[KOL]) -> List[KOL]:
        """
        识别KOL100候选人
        
        Args:
            kols: KOL列表
            
        Returns:
            KOL100候选人列表
        """
        # 按影响力评分排序
        sorted_kols = sorted(kols, key=lambda k: k.influence_score or 0, reverse=True)
        
        # 选择前100名或影响力评分≥80的KOL
        kol100_candidates = []
        for i, kol in enumerate(sorted_kols):
            if i < 100 or (kol.influence_score or 0) >= 80:
                kol.is_kol100 = 1
                kol100_candidates.append(kol)
            else:
                break
        
        self.logger.info(f"识别出 {len(kol100_candidates)} 个KOL100候选人")
        return kol100_candidates
    
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
            'chatgpt_errors': chatgpt_stats['error_count'],
            'min_followers_threshold': self.min_followers_for_kol,
            'min_influence_threshold': self.min_influence_score
        }


# 全局KOL分析器实例
kol_analyzer = KOLAnalyzer() 