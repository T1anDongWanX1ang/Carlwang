"""
Project分析引擎
整合项目识别、分析和存储的完整流程
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .database.tweet_dao import tweet_dao
from .database.project_dao import project_dao
from .utils.project_analyzer import project_analyzer
from .utils.config_manager import config
from .utils.logger import get_logger
from .models.tweet import Tweet
from .models.project import Project


class ProjectEngine:
    """Project分析引擎"""
    
    def __init__(self):
        """初始化Project引擎"""
        self.logger = get_logger(__name__)
        self.tweet_dao = tweet_dao
        self.project_dao = project_dao
        self.project_analyzer = project_analyzer
        
        # 配置参数
        self.chatgpt_config = config.get('chatgpt', {})
        self.enable_project_analysis = self.chatgpt_config.get('enable_project_analysis', True)
        self.batch_size = self.chatgpt_config.get('batch_size', 20)
        
        # 统计信息
        self.analysis_count = 0
        self.success_count = 0
        self.error_count = 0
        self.projects_identified = 0
        
        self.logger.info("Project分析引擎初始化完成")
    
    def analyze_recent_tweets(self, hours: int = 24, max_tweets: int = 100) -> bool:
        """
        分析最近推文，识别项目
        
        Args:
            hours: 分析最近多少小时的推文
            max_tweets: 最大分析推文数
            
        Returns:
            是否成功
        """
        if not self.enable_project_analysis:
            self.logger.info("Project分析功能已禁用")
            return True
        
        try:
            self.analysis_count += 1
            self.logger.info(f"开始分析最近 {hours} 小时的推文（最多 {max_tweets} 条）")
            
            # 1. 获取最近推文
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_tweets = self.tweet_dao.get_recent_tweets(
                since_time=cutoff_time,
                limit=max_tweets
            )
            
            if not recent_tweets:
                self.logger.warning("没有找到最近的推文")
                return True
            
            self.logger.info(f"获取到 {len(recent_tweets)} 条最近推文")
            
            # 2. 分批分析推文
            all_projects = []
            for i in range(0, len(recent_tweets), self.batch_size):
                batch_tweets = recent_tweets[i:i + self.batch_size]
                self.logger.info(f"处理推文批次 {i//self.batch_size + 1}/{(len(recent_tweets)-1)//self.batch_size + 1}")
                
                # 分析这批推文中的项目
                batch_projects = self.project_analyzer.extract_projects_from_tweets(batch_tweets)
                all_projects.extend(batch_projects)
                
                # 避免API请求过于频繁
                import time
                time.sleep(1)
            
            if not all_projects:
                self.logger.warning("未识别出任何项目")
                return True
            
            self.logger.info(f"成功提取 {len(all_projects)} 个项目")
            
            # 3. 聚类相似项目
            clustered_projects = self.project_analyzer.cluster_similar_projects(all_projects)
            self.logger.info(f"聚类后得到 {len(clustered_projects)} 个项目")
            
            # 4. 识别趋势项目
            trending_projects = self.project_analyzer.identify_trending_projects(clustered_projects)
            
            # 5. 保存项目数据到数据库
            saved_count = self._save_projects_to_database(clustered_projects)
            
            if saved_count > 0:
                self.logger.info(f"成功保存 {saved_count} 个项目到数据库")
                self.logger.info(f"其中 {len(trending_projects)} 个被标记为趋势项目")
                self.success_count += 1
                self.projects_identified += saved_count
                return True
            else:
                self.logger.error("保存项目到数据库失败")
                self.error_count += 1
                return False
                
        except Exception as e:
            self.logger.error(f"Project分析异常: {e}")
            self.error_count += 1
            return False
    
    def analyze_specific_projects(self, project_symbols: List[str]) -> bool:
        """
        分析指定项目的最新讨论
        
        Args:
            project_symbols: 项目符号列表
            
        Returns:
            是否成功
        """
        try:
            self.logger.info(f"开始分析指定项目: {', '.join(project_symbols)}")
            
            analyzed_projects = []
            
            for symbol in project_symbols:
                try:
                    # 获取项目相关推文（简化版本：基于关键词搜索）
                    project_tweets = self._get_tweets_mentioning_project(symbol)
                    
                    if not project_tweets:
                        self.logger.warning(f"没有找到项目 {symbol} 的相关推文")
                        continue
                    
                    # 分析项目
                    projects = self.project_analyzer.extract_projects_from_tweets(project_tweets)
                    
                    # 筛选目标项目
                    target_project = None
                    for project in projects:
                        if project.symbol.upper() == symbol.upper():
                            target_project = project
                            break
                    
                    if target_project:
                        analyzed_projects.append(target_project)
                        self.logger.info(f"成功分析项目: {target_project.name}")
                    
                except Exception as e:
                    self.logger.error(f"分析项目 {symbol} 失败: {e}")
                    continue
            
            if analyzed_projects:
                saved_count = self._save_projects_to_database(analyzed_projects)
                self.logger.info(f"成功保存 {saved_count} 个项目")
                self.projects_identified += saved_count
                return True
            else:
                self.logger.warning("没有成功分析任何项目")
                return False
                
        except Exception as e:
            self.logger.error(f"分析指定项目失败: {e}")
            return False
    
    def update_existing_projects(self, days: int = 7) -> bool:
        """
        更新现有项目的数据
        
        Args:
            days: 更新最近多少天的项目
            
        Returns:
            是否成功
        """
        try:
            self.logger.info(f"开始更新最近 {days} 天的项目数据")
            
            # 获取需要更新的项目
            all_projects = self.project_dao.get_hot_projects(limit=50)
            
            if not all_projects:
                self.logger.info("没有项目需要更新")
                return True
            
            self.logger.info(f"找到 {len(all_projects)} 个项目需要更新")
            
            updated_count = 0
            for project in all_projects:
                try:
                    # 获取项目的最新推文
                    recent_tweets = self._get_tweets_mentioning_project(project.symbol, days=days)
                    
                    if recent_tweets:
                        # 更新项目指标
                        updated_project = self.project_analyzer.update_project_metrics(project, recent_tweets)
                        
                        # 保存更新后的项目
                        if self.project_dao.upsert_project(updated_project):
                            updated_count += 1
                            self.logger.info(f"项目更新成功: {project.name}")
                        
                except Exception as e:
                    self.logger.error(f"更新项目失败: {project.name}, 错误: {e}")
                    continue
            
            self.logger.info(f"成功更新 {updated_count}/{len(all_projects)} 个项目")
            return updated_count > 0
            
        except Exception as e:
            self.logger.error(f"更新项目数据异常: {e}")
            return False
    
    def _get_tweets_mentioning_project(self, symbol: str, days: int = 1) -> List[Tweet]:
        """
        获取提及特定项目的推文
        
        Args:
            symbol: 项目符号
            days: 天数
            
        Returns:
            相关推文列表
        """
        try:
            # 简化版本：获取最近推文并过滤
            cutoff_time = datetime.now() - timedelta(days=days)
            recent_tweets = self.tweet_dao.get_recent_tweets(
                since_time=cutoff_time,
                limit=200
            )
            
            # 过滤包含项目关键词的推文
            keywords = [
                symbol.lower(),
                f"${symbol.lower()}",
                f"#{symbol.lower()}"
            ]
            
            matching_tweets = []
            for tweet in recent_tweets:
                content_lower = (tweet.full_text or '').lower()
                if any(keyword in content_lower for keyword in keywords):
                    matching_tweets.append(tweet)
            
            return matching_tweets
            
        except Exception as e:
            self.logger.error(f"获取项目推文失败: {symbol}, 错误: {e}")
            return []
    
    def _save_projects_to_database(self, projects: List[Project]) -> int:
        """
        保存项目到数据库
        
        Args:
            projects: 项目列表
            
        Returns:
            成功保存的数量
        """
        try:
            self.logger.info(f"开始保存 {len(projects)} 个项目到数据库...")
            
            saved_count = self.project_dao.batch_upsert_projects(projects)
            
            return saved_count
            
        except Exception as e:
            self.logger.error(f"保存项目到数据库失败: {e}")
            return 0
    
    def get_project_statistics(self) -> Dict[str, Any]:
        """
        获取项目分析统计信息
        
        Returns:
            统计信息字典
        """
        try:
            analyzer_stats = self.project_analyzer.get_statistics()
            project_count = self.project_dao.get_project_count()
            
            # 获取项目分类统计
            category_stats = {}
            for category in ['Layer1', 'Layer2', 'DeFi', 'GameFi', 'NFT', 'Infrastructure', 'Meme', 'AI']:
                category_projects = self.project_dao.get_projects_by_category(category, limit=1000)
                category_stats[category] = len(category_projects)
            
            # 获取情感分布
            sentiment_stats = {
                'bullish': len(self.project_dao.get_projects_by_sentiment_range(70, 100, limit=1000)),
                'neutral': len(self.project_dao.get_projects_by_sentiment_range(30, 70, limit=1000)),
                'bearish': len(self.project_dao.get_projects_by_sentiment_range(0, 30, limit=1000))
            }
            
            # 获取热门项目
            hot_projects = self.project_dao.get_hot_projects(limit=5)
            
            return {
                'analysis_count': self.analysis_count,
                'success_count': self.success_count,
                'error_count': self.error_count,
                'success_rate': (self.success_count / max(self.analysis_count, 1)) * 100,
                'projects_identified': self.projects_identified,
                'total_projects_in_db': project_count,
                'category_distribution': category_stats,
                'sentiment_distribution': sentiment_stats,
                'hot_projects': [
                    {
                        'name': p.name,
                        'symbol': p.symbol,
                        'popularity': p.popularity,
                        'sentiment': p.sentiment_index
                    } for p in hot_projects
                ],
                'chatgpt_stats': analyzer_stats
            }
            
        except Exception as e:
            self.logger.error(f"获取项目统计信息失败: {e}")
            return {}
    
    def reset_statistics(self):
        """重置统计信息"""
        self.analysis_count = 0
        self.success_count = 0
        self.error_count = 0
        self.projects_identified = 0
        self.project_analyzer.chatgpt_client.reset_statistics()
        self.logger.info("Project引擎统计信息已重置")


# 全局Project引擎实例
project_engine = ProjectEngine() 