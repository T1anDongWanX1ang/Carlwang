"""
Project分析器
实现项目识别、分类和热度计算算法
"""
import re
import math
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

from ..api.chatgpt_client import chatgpt_client
from ..models.tweet import Tweet
from ..models.project import Project
from ..utils.logger import get_logger


class ProjectAnalyzer:
    """Project分析器"""
    
    def __init__(self):
        """初始化Project分析器"""
        self.logger = get_logger(__name__)
        self.chatgpt_client = chatgpt_client
        
        # 预定义的项目映射表
        self.project_mappings = self._load_project_mappings()
        
        # 热度计算权重
        self.popularity_weights = {
            'mention_count': 0.4,     # 提及次数权重
            'engagement': 0.3,        # 互动质量权重
            'kol_participation': 0.2, # KOL参与度权重
            'time_concentration': 0.1  # 时间集中度权重
        }
    
    def extract_projects_from_tweets(self, tweets: List[Tweet]) -> List[Project]:
        """
        从推文中提取项目信息
        
        Args:
            tweets: 推文列表
            
        Returns:
            识别的项目列表
        """
        try:
            self.logger.info(f"开始从 {len(tweets)} 条推文中提取项目...")
            
            if not tweets:
                return []
            
            # 1. 准备推文数据
            tweets_data = []
            for tweet in tweets:
                tweet_data = {
                    'tweet_id': tweet.id_str,
                    'content': tweet.full_text,
                    'user_screen_name': getattr(tweet, 'screen_name', 'unknown'),
                    'engagement_total': tweet.engagement_total or 0,
                    'created_at': tweet.created_at
                }
                tweets_data.append(tweet_data)
            
            # 2. 使用ChatGPT分析项目
            analysis_result = self.chatgpt_client.analyze_projects_in_tweets(tweets_data)
            
            if not analysis_result or 'projects' not in analysis_result:
                self.logger.warning("ChatGPT未识别出任何项目")
                return []
            
            # 3. 转换为Project对象
            projects = []
            for project_data in analysis_result['projects']:
                try:
                    project = self._create_project_from_analysis(project_data, tweets)
                    if project and project.validate():
                        projects.append(project)
                        
                except Exception as e:
                    self.logger.error(f"创建项目对象失败: {e}")
                    continue
            
            # 4. 计算项目热度
            for project in projects:
                popularity = self._calculate_project_popularity(project, tweets)
                project.popularity = popularity
                project.add_popularity_history(popularity)
            
            # 5. 生成项目总结
            for project in projects:
                related_tweets = self._get_project_related_tweets(project, tweets)
                summary = self.chatgpt_client.generate_project_summary(
                    project.to_dict(), 
                    [tweet.full_text for tweet in related_tweets]
                )
                if summary:
                    project.summary = summary
            
            self.logger.info(f"成功提取 {len(projects)} 个项目")
            return projects
            
        except Exception as e:
            self.logger.error(f"提取项目失败: {e}")
            return []
    
    def _create_project_from_analysis(self, project_data: Dict[str, Any], 
                                    tweets: List[Tweet]) -> Optional[Project]:
        """
        从分析结果创建Project对象
        
        Args:
            project_data: ChatGPT分析结果
            tweets: 相关推文
            
        Returns:
            Project对象
        """
        try:
            project_id = project_data.get('project_id') or f"{project_data['name'].lower()}_{project_data['symbol'].lower()}"
            
            project = Project(
                project_id=project_id,
                name=project_data['name'],
                symbol=project_data['symbol'],
                category=project_data.get('category'),
                narratives=project_data.get('narratives', []),
                sentiment_index=project_data.get('sentiment_index'),
                popularity=project_data.get('popularity_score', 0)
            )
            
            # 添加情感历史
            if project.sentiment_index:
                project.add_sentiment_history(project.sentiment_index)
            
            return project
            
        except Exception as e:
            self.logger.error(f"创建项目对象失败: {e}")
            return None
    
    def _calculate_project_popularity(self, project: Project, tweets: List[Tweet]) -> int:
        """
        计算项目热度
        基于derived-metrics-calculation-details.md中的算法
        
        Args:
            project: 项目对象
            tweets: 推文列表
            
        Returns:
            热度分数 (0-1000)
        """
        try:
            # 获取项目相关推文
            project_tweets = self._get_project_related_tweets(project, tweets)
            
            if not project_tweets:
                return 0
            
            # 1. 推文数量基础分 (40%)
            mention_count = len(project_tweets)
            mention_score = min(1000, mention_count * 10)  # 每次提及10分
            
            # 2. 互动质量分 (30%)
            total_engagement = sum(
                (tweet.engagement_total or 0) for tweet in project_tweets
            )
            engagement_score = min(1000, total_engagement / 10)
            
            # 3. KOL参与度分 (20%) - 简化版本
            # 基于用户粉丝数估算KOL参与度
            kol_score = 0
            unique_users = set()
            for tweet in project_tweets:
                user_id = getattr(tweet, 'user_id', None)
                if user_id:
                    unique_users.add(user_id)
            
            # 简化计算：假设高互动推文来自KOL
            high_engagement_tweets = [t for t in project_tweets if (t.engagement_total or 0) > 100]
            kol_score = min(1000, len(high_engagement_tweets) * 50)
            
            # 4. 时间集中度加成 (10%)
            time_concentration = self._calculate_time_concentration(project_tweets)
            time_score = time_concentration * 100
            
            # 计算最终热度
            popularity = int(
                mention_score * self.popularity_weights['mention_count'] +
                engagement_score * self.popularity_weights['engagement'] +
                kol_score * self.popularity_weights['kol_participation'] +
                time_score * self.popularity_weights['time_concentration']
            )
            
            self.logger.debug(f"项目热度计算 {project.name}: "
                            f"提及({mention_score:.0f}) + 互动({engagement_score:.0f}) + "
                            f"KOL({kol_score:.0f}) + 时间({time_score:.0f}) = {popularity}")
            
            return min(1000, max(0, popularity))
            
        except Exception as e:
            self.logger.error(f"计算项目热度失败: {project.name}, 错误: {e}")
            return 0
    
    def _get_project_related_tweets(self, project: Project, tweets: List[Tweet]) -> List[Tweet]:
        """
        获取与项目相关的推文
        
        Args:
            project: 项目对象
            tweets: 推文列表
            
        Returns:
            相关推文列表
        """
        related_tweets = []
        
        # 构建匹配关键词
        keywords = [
            project.name.lower(),
            project.symbol.lower(),
            f"${project.symbol.lower()}",
            f"#{project.symbol.lower()}"
        ]
        
        # 添加中文别名
        chinese_aliases = self._get_chinese_aliases(project.symbol)
        keywords.extend(chinese_aliases)
        
        for tweet in tweets:
            content_lower = (tweet.full_text or '').lower()
            
            # 检查是否包含项目关键词
            for keyword in keywords:
                if keyword in content_lower:
                    related_tweets.append(tweet)
                    break
        
        return related_tweets
    
    def _calculate_time_concentration(self, tweets: List[Tweet]) -> float:
        """
        计算时间集中度
        
        Args:
            tweets: 推文列表
            
        Returns:
            时间集中度 (0.0-1.0)
        """
        if len(tweets) < 2:
            return 0.0
        
        try:
            # 计算推文时间间隔
            timestamps = []
            for tweet in tweets:
                if tweet.created_at_datetime:
                    timestamps.append(tweet.created_at_datetime)
            
            if len(timestamps) < 2:
                return 0.0
            
            timestamps.sort()
            
            # 计算平均时间间隔（小时）
            total_span = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
            
            if total_span <= 0:
                return 1.0
            
            # 时间越集中，集中度越高
            concentration = 1.0 / (1.0 + total_span / 24)  # 24小时内集中度最高
            
            return min(1.0, concentration)
            
        except Exception as e:
            self.logger.error(f"计算时间集中度失败: {e}")
            return 0.0
    
    def _get_chinese_aliases(self, symbol: str) -> List[str]:
        """
        获取代币的中文别名
        
        Args:
            symbol: 代币符号
            
        Returns:
            中文别名列表
        """
        aliases_map = {
            'BTC': ['比特币', '大饼', 'bitcoin'],
            'ETH': ['以太坊', '以太币', '姨太', 'ethereum'],
            'BNB': ['币安币', 'binance coin'],
            'SOL': ['索拉纳', 'solana'],
            'ADA': ['艾达币', 'cardano'],
            'DOT': ['波卡', 'polkadot'],
            'MATIC': ['马蹄', 'polygon'],
            'UNI': ['独角兽', 'uniswap'],
            'LINK': ['链克', 'chainlink'],
            'DOGE': ['狗狗币', 'dogecoin']
        }
        
        return aliases_map.get(symbol.upper(), [])
    
    def _load_project_mappings(self) -> Dict[str, Dict[str, Any]]:
        """
        加载预定义的项目映射表
        
        Returns:
            项目映射字典
        """
        return {
            'bitcoin': {
                'project_id': 'bitcoin_btc',
                'name': 'Bitcoin',
                'symbol': 'BTC',
                'category': 'Layer1',
                'narratives': ['Digital Gold', 'Store of Value']
            },
            'ethereum': {
                'project_id': 'ethereum_eth',
                'name': 'Ethereum',
                'symbol': 'ETH',
                'category': 'Layer1',
                'narratives': ['Smart Contract Platform', 'DeFi']
            },
            'solana': {
                'project_id': 'solana_sol',
                'name': 'Solana',
                'symbol': 'SOL',
                'category': 'Layer1',
                'narratives': ['High Performance', 'DeFi']
            },
            'uniswap': {
                'project_id': 'uniswap_uni',
                'name': 'Uniswap',
                'symbol': 'UNI',
                'category': 'DeFi',
                'narratives': ['DEX', 'DeFi Summer']
            },
            'chainlink': {
                'project_id': 'chainlink_link',
                'name': 'Chainlink',
                'symbol': 'LINK',
                'category': 'Infrastructure',
                'narratives': ['Oracle', 'DeFi Infrastructure']
            }
        }
    
    def update_project_metrics(self, project: Project, new_tweets: List[Tweet]) -> Project:
        """
        更新项目指标
        
        Args:
            project: 项目对象
            new_tweets: 新推文列表
            
        Returns:
            更新后的项目对象
        """
        try:
            # 重新计算热度
            if new_tweets:
                new_popularity = self._calculate_project_popularity(project, new_tweets)
                if new_popularity != project.popularity:
                    project.popularity = new_popularity
                    project.add_popularity_history(new_popularity)
                
                # 重新计算情感指数
                project_tweets = self._get_project_related_tweets(project, new_tweets)
                if project_tweets:
                    tweet_contents = [tweet.full_text for tweet in project_tweets if tweet.full_text]
                    new_sentiment = self.chatgpt_client.calculate_project_sentiment(tweet_contents)
                    
                    if new_sentiment is not None and new_sentiment != project.sentiment_index:
                        project.sentiment_index = new_sentiment
                        project.add_sentiment_history(new_sentiment)
            
            # 更新时间
            project.last_updated = datetime.now()
            project.update_time = datetime.now()
            
            return project
            
        except Exception as e:
            self.logger.error(f"更新项目指标失败: {project.name}, 错误: {e}")
            return project
    
    def identify_trending_projects(self, projects: List[Project]) -> List[Project]:
        """
        识别趋势项目
        
        Args:
            projects: 项目列表
            
        Returns:
            趋势项目列表
        """
        trending_projects = []
        
        for project in projects:
            try:
                # 基于情感趋势和热度变化识别趋势项目
                sentiment_trend = project.get_sentiment_trend()
                
                # 趋势项目条件
                is_trending = (
                    (project.sentiment_index or 0) > 60 and  # 情感积极
                    (project.popularity or 0) > 100 and      # 热度较高
                    sentiment_trend == 'rising'              # 情感上升
                )
                
                if is_trending:
                    trending_projects.append(project)
                    
            except Exception as e:
                self.logger.error(f"识别趋势项目失败: {project.name}, 错误: {e}")
                continue
        
        # 按热度排序
        trending_projects.sort(key=lambda p: p.popularity or 0, reverse=True)
        
        self.logger.info(f"识别出 {len(trending_projects)} 个趋势项目")
        return trending_projects
    
    def cluster_similar_projects(self, projects: List[Project]) -> List[Project]:
        """
        聚类相似项目（简化版本）
        
        Args:
            projects: 项目列表
            
        Returns:
            聚类后的项目列表
        """
        if not projects:
            return []
        
        # 简化版本：基于符号去重
        unique_projects = {}
        for project in projects:
            key = project.symbol.upper()
            
            if key not in unique_projects:
                unique_projects[key] = project
            else:
                # 合并相同项目的数据
                existing = unique_projects[key]
                
                # 取较高的热度和情感值
                if (project.popularity or 0) > (existing.popularity or 0):
                    existing.popularity = project.popularity
                
                if (project.sentiment_index or 0) > (existing.sentiment_index or 0):
                    existing.sentiment_index = project.sentiment_index
                
                # 合并叙事
                for narrative in project.narratives or []:
                    existing.add_narrative(narrative)
        
        clustered_projects = list(unique_projects.values())
        
        self.logger.info(f"项目聚类: {len(projects)} → {len(clustered_projects)}")
        return clustered_projects
    
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
            'popularity_weights': self.popularity_weights,
            'known_projects': len(self.project_mappings)
        }


# 全局Project分析器实例
project_analyzer = ProjectAnalyzer() 