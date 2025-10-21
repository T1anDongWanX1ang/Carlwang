"""
KOL分析引擎
整合KOL识别、分析和存储的完整流程
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .database.user_dao import user_dao
from .database.tweet_dao import tweet_dao
from .database.kol_dao import kol_dao
from .utils.kol_analyzer import kol_analyzer
from .utils.config_manager import config
from .utils.logger import get_logger
from .models.user import TwitterUser
from .models.kol import KOL


class KOLEngine:
    """KOL分析引擎"""
    
    def __init__(self):
        """初始化KOL引擎"""
        self.logger = get_logger(__name__)
        self.user_dao = user_dao
        self.tweet_dao = tweet_dao
        self.kol_dao = kol_dao
        self.kol_analyzer = kol_analyzer
        
        # 配置参数
        self.chatgpt_config = config.get('chatgpt', {})
        self.enable_kol_analysis = self.chatgpt_config.get('enable_kol_analysis', True)
        
        # 批处理配置
        batch_config = self.chatgpt_config.get('batch_processing', {})
        self.batch_size = batch_config.get('kol_batch_size', 8)  # KOL分析优化后的批次大小
        
        # 统计信息
        self.analysis_count = 0
        self.success_count = 0
        self.error_count = 0
        self.kols_identified = 0
        
        self.logger.info("KOL分析引擎初始化完成")
    
    def analyze_all_users_as_kols(self, min_followers: int = 1000, max_users: int = 50) -> bool:
        """
        分析所有用户，识别KOL
        
        Args:
            min_followers: 最小粉丝数阈值
            max_users: 最大分析用户数
            
        Returns:
            是否成功
        """
        if not self.enable_kol_analysis:
            self.logger.info("KOL分析功能已禁用")
            return True
        
        try:
            self.analysis_count += 1
            self.logger.info(f"开始分析所有用户，识别KOL（最小粉丝数: {min_followers}, 最多分析: {max_users} 个用户）")
            
            # 1. 获取高粉丝数用户
            high_follower_users = self._get_high_follower_users(min_followers, max_users)
            
            if not high_follower_users:
                self.logger.warning("没有找到符合条件的高粉丝用户")
                return True
            
            self.logger.info(f"找到 {len(high_follower_users)} 个高粉丝用户")
            
            # 2. 获取用户的推文数据（用于更准确的分析）
            user_tweets_map = self._get_user_tweets_map(high_follower_users)
            
            # 3. 分批分析用户
            all_kols = []
            for i in range(0, len(high_follower_users), self.batch_size):
                batch_users = high_follower_users[i:i + self.batch_size]
                self.logger.info(f"分析用户批次 {i//self.batch_size + 1}/{(len(high_follower_users)-1)//self.batch_size + 1}")
                
                # 分析这批用户
                batch_kols = self.kol_analyzer.batch_analyze_users_as_kols(batch_users, user_tweets_map)
                all_kols.extend(batch_kols)
                
                # 避免ChatGPT API请求过于频繁
                import time
                time.sleep(2)
            
            if not all_kols:
                self.logger.warning("未识别出任何KOL")
                return True
            
            self.logger.info(f"成功识别 {len(all_kols)} 个KOL")
            
            # 4. 识别KOL100候选人
            kol100_candidates = self.kol_analyzer.identify_kol100_candidates(all_kols)
            
            # 5. 保存KOL数据到数据库
            saved_count = self._save_kols_to_database(all_kols)
            
            if saved_count > 0:
                self.logger.info(f"成功保存 {saved_count} 个KOL到数据库")
                self.logger.info(f"其中 {len(kol100_candidates)} 个被纳入KOL100")
                self.success_count += 1
                self.kols_identified += saved_count
                return True
            else:
                self.logger.error("保存KOL到数据库失败")
                self.error_count += 1
                return False
                
        except Exception as e:
            self.logger.error(f"KOL分析异常: {e}")
            self.error_count += 1
            return False
    
    def analyze_specific_users(self, user_ids: List[str]) -> bool:
        """
        分析指定用户是否为KOL
        
        Args:
            user_ids: 用户ID列表
            
        Returns:
            是否成功
        """
        try:
            self.logger.info(f"开始分析指定的 {len(user_ids)} 个用户")
            
            # 获取用户数据
            users = []
            for user_id in user_ids:
                user = self.user_dao.get_user_by_id(user_id)
                if user:
                    users.append(user)
            
            if not users:
                self.logger.warning("没有找到有效的用户数据")
                return True
            
            self.logger.info(f"获取到 {len(users)} 个有效用户")
            
            # 获取用户推文
            user_tweets_map = self._get_user_tweets_map(users)
            
            # 分析KOL
            kols = self.kol_analyzer.batch_analyze_users_as_kols(users, user_tweets_map)
            
            if not kols:
                self.logger.warning("未识别出任何KOL")
                return True
            
            # 保存KOL
            saved_count = self._save_kols_to_database(kols)
            
            if saved_count > 0:
                self.logger.info(f"成功保存 {saved_count} 个KOL")
                self.kols_identified += saved_count
                return True
            else:
                self.logger.error("保存KOL失败")
                return False
                
        except Exception as e:
            self.logger.error(f"分析指定用户失败: {e}")
            return False
    
    def update_existing_kols(self, days: int = 7) -> bool:
        """
        更新现有KOL的数据
        
        Args:
            days: 更新最近多少天的KOL
            
        Returns:
            是否成功
        """
        try:
            self.logger.info(f"开始更新最近 {days} 天的KOL数据")
            
            # 获取需要更新的KOL
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # 获取所有KOL（简化版本）
            all_kols = self.kol_dao.get_top_kols_by_influence(limit=100)
            
            if not all_kols:
                self.logger.info("没有KOL需要更新")
                return True
            
            self.logger.info(f"找到 {len(all_kols)} 个KOL需要更新")
            
            updated_count = 0
            for kol in all_kols:
                try:
                    # 获取KOL的最新推文
                    user = self.user_dao.get_user_by_id(kol.kol_id)
                    if not user:
                        continue
                    
                    # 获取最近推文（简化版本：获取最近的推文）
                    recent_tweets = self._get_user_recent_tweets(kol.kol_id, days=3)
                    
                    if recent_tweets:
                        # 更新KOL指标
                        updated_kol = self.kol_analyzer.update_kol_metrics(kol, recent_tweets)
                        
                        # 保存更新后的KOL
                        if self.kol_dao.upsert_kol(updated_kol):
                            updated_count += 1
                            self.logger.info(f"KOL更新成功: @{user.screen_name}")
                        
                except Exception as e:
                    self.logger.error(f"更新KOL失败: {kol.kol_id}, 错误: {e}")
                    continue
            
            self.logger.info(f"成功更新 {updated_count}/{len(all_kols)} 个KOL")
            return updated_count > 0
            
        except Exception as e:
            self.logger.error(f"更新KOL数据异常: {e}")
            return False
    
    def _get_high_follower_users(self, min_followers: int, limit: int) -> List[TwitterUser]:
        """
        获取高粉丝数用户
        
        Args:
            min_followers: 最小粉丝数
            limit: 限制数量
            
        Returns:
            高粉丝用户列表
        """
        try:
            # 获取粉丝数最多的用户
            top_users = self.user_dao.get_top_users_by_followers(limit=limit * 2)  # 多获取一些以便筛选
            
            # 筛选符合条件的用户
            filtered_users = [
                user for user in top_users 
                if (user.followers_count or 0) >= min_followers
            ]
            
            return filtered_users[:limit]
            
        except Exception as e:
            self.logger.error(f"获取高粉丝用户失败: {e}")
            return []
    
    def _get_user_tweets_map(self, users: List[TwitterUser]) -> Dict[str, List]:
        """
        获取用户推文映射
        
        Args:
            users: 用户列表
            
        Returns:
            用户ID到推文列表的映射
        """
        user_tweets_map = {}
        
        # 简化版本：暂时返回空映射
        # 在实际应用中，这里应该查询每个用户的最近推文
        # 由于当前数据库结构限制，我们先使用空映射
        
        for user in users:
            user_tweets_map[user.id_str] = []
        
        return user_tweets_map
    
    def _get_user_recent_tweets(self, user_id: str, days: int = 7) -> List:
        """
        获取用户最近推文（简化版本）
        
        Args:
            user_id: 用户ID
            days: 天数
            
        Returns:
            推文列表
        """
        # 简化版本：由于当前数据库结构没有user_id字段，暂时返回空列表
        # 在实际应用中，这里应该根据user_id查询推文
        return []
    
    def _save_kols_to_database(self, kols: List[KOL]) -> int:
        """
        保存KOL到数据库
        
        Args:
            kols: KOL列表
            
        Returns:
            成功保存的数量
        """
        try:
            self.logger.info(f"开始保存 {len(kols)} 个KOL到数据库...")
            
            saved_count = self.kol_dao.batch_upsert_kols(kols)
            
            return saved_count
            
        except Exception as e:
            self.logger.error(f"保存KOL到数据库失败: {e}")
            return 0
    
    def get_kol_statistics(self) -> Dict[str, Any]:
        """
        获取KOL分析统计信息
        
        Returns:
            统计信息字典
        """
        try:
            analyzer_stats = self.kol_analyzer.get_statistics()
            kol_count = self.kol_dao.get_kol_count()
            
            # 获取KOL分布统计
            type_stats = {}
            for kol_type in ['founder', 'influencer', 'investor', 'trader', 'analyst']:
                type_kols = self.kol_dao.get_kols_by_type(kol_type, limit=1000)
                type_stats[kol_type] = len(type_kols)
            
            # 获取情感分布
            sentiment_stats = {}
            for sentiment in ['bullish', 'bearish', 'neutral']:
                sentiment_kols = self.kol_dao.get_kols_by_sentiment(sentiment, limit=1000)
                sentiment_stats[sentiment] = len(sentiment_kols)
            
            # 获取KOL100数量
            kol100_list = self.kol_dao.get_kol100_list()
            
            return {
                'analysis_count': self.analysis_count,
                'success_count': self.success_count,
                'error_count': self.error_count,
                'success_rate': (self.success_count / max(self.analysis_count, 1)) * 100,
                'kols_identified': self.kols_identified,
                'total_kols_in_db': kol_count,
                'kol100_count': len(kol100_list),
                'type_distribution': type_stats,
                'sentiment_distribution': sentiment_stats,
                'chatgpt_stats': analyzer_stats
            }
            
        except Exception as e:
            self.logger.error(f"获取KOL统计信息失败: {e}")
            return {}
    
    def reset_statistics(self):
        """重置统计信息"""
        self.analysis_count = 0
        self.success_count = 0
        self.error_count = 0
        self.kols_identified = 0
        self.kol_analyzer.chatgpt_client.reset_statistics()
        self.logger.info("KOL引擎统计信息已重置")


# 全局KOL引擎实例
# 全局KOL引擎实例
kol_engine = KOLEngine() 