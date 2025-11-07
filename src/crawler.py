"""
Twitter数据爬虫核心模块
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .api.twitter_api import twitter_api
from .database.tweet_dao import tweet_dao
from .database.user_dao import user_dao
from .utils.data_mapper import data_mapper
from .utils.config_manager import config
from .utils.logger import get_logger
from .utils.tweet_enricher import tweet_enricher
from .utils.user_language_integration import UserLanguageIntegration
from .models.tweet import Tweet
from .models.user import TwitterUser
from .topic_engine import topic_engine
# from .kol_engine import kol_engine  # KOL分析已禁用
from .project_engine import project_engine


class TwitterCrawler:
    """Twitter数据爬虫"""
    
    def __init__(self):
        """初始化爬虫"""
        self.logger = get_logger(__name__)
        self.api_client = twitter_api
        self.tweet_dao = tweet_dao
        self.user_dao = user_dao
        self.data_mapper = data_mapper
        self.topic_engine = topic_engine
        # self.kol_engine = kol_engine  # KOL分析已禁用
        self.project_engine = project_engine
        self.tweet_enricher = tweet_enricher
        
        # 初始化用户语言集成器
        from .api.chatgpt_client import chatgpt_client
        self.user_language_integration = UserLanguageIntegration(
            db_manager=self.user_dao.db_manager,
            chatgpt_client=chatgpt_client
        )
        
        # 爬取统计
        self.crawl_count = 0
        self.success_count = 0
        self.error_count = 0
        self.last_crawl_time = None
        
        self.logger.info("Twitter爬虫初始化完成")
    
    def crawl_tweets(self, list_id: str = None, max_pages: int = None, 
                    page_size: int = None, hours_limit: int = 2) -> bool:
        """
        爬取推文数据
        
        Args:
            list_id: 列表ID，如果不指定则使用配置中的默认值
            max_pages: 最大页数（不超过15页）
            page_size: 每页大小
            hours_limit: 时间限制（小时），只拉取过去N小时的推文，默认2小时（生产环境使用UTC时间）
            
        Returns:
            是否成功
        """
        self.crawl_count += 1
        self.last_crawl_time = datetime.now()
        
        try:
            self.logger.info(f"开始爬取推文数据 (第 {self.crawl_count} 次，时间限制: {hours_limit}小时)")
            
            # 1. 从API获取数据（最多15页，只拉取过去8小时）
            api_data_list = self._fetch_api_data(list_id, max_pages, page_size, hours_limit)
            
            if not api_data_list:
                self.logger.warning("未获取到任何API数据")
                self.error_count += 1
                return False
            
            self.logger.info(f"从API获取到 {len(api_data_list)} 条原始数据")
            
            # 2. 数据映射和转换
            tweets = self._map_data_to_tweets(api_data_list)
            
            if not tweets:
                self.logger.warning("数据映射后没有有效的推文数据")
                self.error_count += 1
                return False
            
            self.logger.info(f"成功映射 {len(tweets)} 条推文数据")
            
            # 2.1 提取用户数据
            users = self._extract_users_from_api_data(api_data_list)
            self.logger.info(f"成功提取 {len(users)} 条用户数据")
            
            # 2.2 构建用户数据映射（用于推文增强）
            # 建立 tweet_id -> user_data 的映射关系
            user_data_map = {}
            for api_data in api_data_list:
                try:
                    tweet_id = api_data.get('id_str')
                    user_data = api_data.get('user')
                    if tweet_id and user_data and isinstance(user_data, dict):
                        user_data_map[tweet_id] = user_data
                except Exception as e:
                    self.logger.warning(f"构建用户数据映射失败: {e}")
                    continue
            
            # 2.3 增强推文数据（添加 kol_id 和 entity_id）
            self.logger.info("开始增强推文数据...")
            enriched_tweets = self.tweet_enricher.enrich_tweets(tweets, user_data_map)
            self.logger.info(f"推文增强完成，处理了 {len(enriched_tweets)} 条推文")
            
            # 3. 存储到数据库
            # 先保存用户数据（因为推文可能引用用户）
            if users:
                user_saved_count = self._save_users_to_database(users)
                self.logger.info(f"成功保存 {user_saved_count} 条用户数据")
            
            # 然后保存增强后的推文数据
            tweet_saved_count = self._save_tweets_to_database(enriched_tweets)
            
            # 4. 话题分析和生成（如果推文保存成功）
            if tweet_saved_count > 0:
                self.logger.info(f"成功保存 {tweet_saved_count} 条推文到数据库")
                
                # 进行话题分析
                try:
                    self.logger.info("开始进行话题分析...")
                    topic_success = self.topic_engine.analyze_recent_tweets(hours=1, max_tweets=50)
                    
                    if topic_success:
                        self.logger.info("话题分析完成")
                    else:
                        self.logger.warning("话题分析失败，但不影响主流程")
                        
                except Exception as e:
                    self.logger.error(f"话题分析异常: {e}")
                
                # KOL分析已禁用
                # try:
                #     self.logger.info("开始进行KOL分析...")
                #     kol_success = self.kol_engine.analyze_all_users_as_kols(min_followers=50000, max_users=10)
                #     
                #     if kol_success:
                #         self.logger.info("KOL分析完成")
                #     else:
                #         self.logger.warning("KOL分析失败，但不影响主流程")
                #         
                # except Exception as e:
                #     self.logger.error(f"KOL分析异常: {e}")
                
                # 进行项目分析
                try:
                    self.logger.info("开始进行项目分析...")
                    project_success = self.project_engine.analyze_recent_tweets(hours=1, max_tweets=50)
                    
                    if project_success:
                        self.logger.info("项目分析完成")
                    else:
                        self.logger.warning("项目分析失败，但不影响主流程")
                        
                except Exception as e:
                    self.logger.error(f"项目分析异常: {e}")
                
                self.success_count += 1
                return True
            else:
                self.logger.error("保存推文到数据库失败")
                self.error_count += 1
                return False
                
        except Exception as e:
            self.logger.error(f"爬取推文数据异常: {e}")
            self.error_count += 1
            return False
    
    def _fetch_api_data(self, list_id: str = None, max_pages: int = None, 
                       page_size: int = None, hours_limit: int = 2) -> List[Dict[str, Any]]:
        """
        从API获取数据
        
        Args:
            list_id: 列表ID
            max_pages: 最大页数（不超过15页）
            page_size: 每页大小
            hours_limit: 时间限制（小时），只拉取过去N小时的推文
            
        Returns:
            API数据列表
        """
        try:
            # 使用配置的默认值或传入的参数
            if list_id is None:
                list_id = config.get('api.default_params.list_id')
            
            self.logger.info(f"正在从API获取数据，list_id: {list_id}, 时间限制: {hours_limit}小时")
            
            # 获取所有推文数据（最多15页，只拉取过去8小时）
            api_data_list = self.api_client.fetch_all_tweets(
                list_id=list_id,
                max_pages=max_pages,
                page_size=page_size,
                hours_limit=hours_limit
            )
            
            # 获取API请求统计
            stats = self.api_client.get_request_stats()
            self.logger.info(f"API请求统计: {stats}")
            
            return api_data_list
            
        except Exception as e:
            self.logger.error(f"从API获取数据失败: {e}")
            return []
    
    def _map_data_to_tweets(self, api_data_list: List[Dict[str, Any]]) -> List[Tweet]:
        """
        将API数据映射为Tweet对象
        
        Args:
            api_data_list: API数据列表
            
        Returns:
            Tweet对象列表
        """
        try:
            self.logger.info("开始映射API数据到Tweet对象...")
            
            tweets = self.data_mapper.map_api_data_list_to_tweets(api_data_list)
            
            # 数据去重（基于id_str）
            unique_tweets = self._deduplicate_tweets(tweets)
            
            if len(unique_tweets) != len(tweets):
                self.logger.info(f"去重后剩余 {len(unique_tweets)} 条推文（原 {len(tweets)} 条）")
            
            return unique_tweets
            
        except Exception as e:
            self.logger.error(f"数据映射失败: {e}")
            return []
    
    def _deduplicate_tweets(self, tweets: List[Tweet]) -> List[Tweet]:
        """
        推文去重
        
        Args:
            tweets: 推文列表
            
        Returns:
            去重后的推文列表
        """
        seen_ids = set()
        unique_tweets = []
        
        for tweet in tweets:
            if tweet.id_str not in seen_ids:
                seen_ids.add(tweet.id_str)
                unique_tweets.append(tweet)
        
        return unique_tweets
    
    def _extract_users_from_api_data(self, api_data_list: List[Dict[str, Any]]) -> List[TwitterUser]:
        """
        从API数据中提取用户信息
        
        Args:
            api_data_list: API数据列表
            
        Returns:
            用户对象列表
        """
        try:
            self.logger.info("开始从API数据中提取用户信息...")
            
            users = self.data_mapper.extract_users_from_tweets(api_data_list)
            
            # 用户去重（基于id_str）
            unique_users = self._deduplicate_users(users)
            
            if len(unique_users) != len(users):
                self.logger.info(f"用户去重后剩余 {len(unique_users)} 个用户（原 {len(users)} 个）")
            
            return unique_users
            
        except Exception as e:
            self.logger.error(f"提取用户数据失败: {e}")
            return []
    
    def _deduplicate_users(self, users: List[TwitterUser]) -> List[TwitterUser]:
        """
        用户去重
        
        Args:
            users: 用户列表
            
        Returns:
            去重后的用户列表
        """
        seen_ids = set()
        unique_users = []
        
        for user in users:
            if user.id_str not in seen_ids:
                seen_ids.add(user.id_str)
                unique_users.append(user)
        
        return unique_users
    
    def _extract_user_data_from_api(self, api_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        从API数据中提取原始用户数据（用于推文增强）
        
        Args:
            api_data_list: API原始数据列表
            
        Returns:
            原始用户数据列表
        """
        user_data_list = []
        
        for api_data in api_data_list:
            try:
                # 从tweet数据中提取user信息
                user_data = api_data.get('user')
                if user_data and isinstance(user_data, dict):
                    user_data_list.append(user_data)
                    
            except Exception as e:
                self.logger.warning(f"提取用户数据失败: {e}")
                continue
        
        return user_data_list
    
    def _save_users_to_database(self, users: List[TwitterUser]) -> int:
        """
        保存用户到数据库
        
        Args:
            users: 用户列表
            
        Returns:
            成功保存的数量
        """
        try:
            self.logger.info(f"开始保存 {len(users)} 条用户到数据库...")
            
            # 先进行语言检测增强
            enhanced_users = self._enhance_users_with_language(users)
            
            # 批量保存增强后的用户数据
            saved_count = self.user_dao.batch_upsert_users(enhanced_users)
            
            return saved_count
            
        except Exception as e:
            self.logger.error(f"保存用户到数据库失败: {e}")
            return 0
    
    def _enhance_users_with_language(self, users: List[TwitterUser]) -> List[TwitterUser]:
        """
        为用户列表添加语言检测信息
        
        Args:
            users: 用户列表
            
        Returns:
            增强后的用户列表
        """
        try:
            self.logger.info(f"开始为 {len(users)} 个用户进行语言检测...")
            
            # 使用批量语言检测
            enhanced_users = self.user_language_integration.enhance_users_batch(
                users=users,
                use_ai_fallback=False  # 暂时不使用AI辅助，避免过多API调用
            )
            
            self.logger.info(f"完成语言检测，增强了 {len(enhanced_users)} 个用户")
            return enhanced_users
            
        except Exception as e:
            self.logger.error(f"用户语言检测失败: {e}")
            # 如果语言检测失败，设置默认语言并返回原用户列表
            for user in users:
                if not hasattr(user, 'language') or user.language is None:
                    user.language = "English"  # 默认设为English
            return users
    
    def _save_tweets_to_database(self, tweets: List[Tweet]) -> int:
        """
        保存推文到数据库
        
        Args:
            tweets: 推文列表
            
        Returns:
            成功保存的数量
        """
        try:
            self.logger.info(f"开始保存 {len(tweets)} 条推文到数据库...")
            
            # 批量保存
            saved_count = self.tweet_dao.batch_upsert_tweets(tweets)
            
            return saved_count
            
        except Exception as e:
            self.logger.error(f"保存推文到数据库失败: {e}")
            return 0
    
    def test_connection(self) -> bool:
        """
        测试数据库连接
        
        Returns:
            连接是否成功
        """
        try:
            self.logger.info("测试数据库连接...")
            success = self.tweet_dao.db_manager.test_connection()
            
            if success:
                self.logger.info("数据库连接测试成功")
            else:
                self.logger.error("数据库连接测试失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"数据库连接测试异常: {e}")
            return False
    
    def test_api_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            API连接是否成功
        """
        try:
            self.logger.info("测试API连接...")
            
            # 尝试获取少量数据
            test_data, _ = self.api_client.fetch_tweets(count=1)
            
            success = test_data is not None and len(test_data) >= 0
            
            if success:
                self.logger.info("API连接测试成功")
            else:
                self.logger.error("API连接测试失败")
            
            return success
            
        except Exception as e:
            self.logger.error(f"API连接测试异常: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取爬虫统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'crawl_count': self.crawl_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': (self.success_count / max(self.crawl_count, 1)) * 100,
            'last_crawl_time': self.last_crawl_time.isoformat() if self.last_crawl_time else None,
            'api_stats': self.api_client.get_request_stats(),
            'database_tweet_count': self.tweet_dao.get_tweet_count(),
            'database_user_count': self.user_dao.get_user_count(),
            'topic_stats': self.topic_engine.get_topic_statistics(),
            # 'kol_stats': self.kol_engine.get_kol_statistics(),  # KOL分析已禁用
            'project_stats': self.project_engine.get_project_statistics()
        }
    
    def reset_statistics(self) -> None:
        """重置统计信息"""
        self.crawl_count = 0
        self.success_count = 0
        self.error_count = 0
        self.last_crawl_time = None
        self.api_client.reset_stats()
        self.logger.info("爬虫统计信息已重置")
    
    def close(self) -> None:
        """关闭爬虫，清理资源"""
        try:
            self.api_client.close()
            self.tweet_dao.db_manager.close()
            self.user_dao.db_manager.close()
            self.logger.info("爬虫资源已清理")
        except Exception as e:
            self.logger.error(f"清理爬虫资源时出错: {e}")


# 全局爬虫实例
crawler = TwitterCrawler() 