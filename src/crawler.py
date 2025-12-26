"""
Twitter数据爬虫核心模块
"""
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# 后端可切换：默认使用 Twitter API (twitterapi)，设置环境变量 TWITTER_API_BACKEND=tweetscout 使用 TweetScout
# 为了向后兼容KOL推文爬取，现在默认使用 twitterapi
if os.getenv("TWITTER_API_BACKEND", "twitterapi").lower() == "tweetscout":
    from .api.twitter_api import twitter_api as selected_api_client
else:
    from .api.twitter_api_twitterapi import twitter_api as selected_api_client
from .database.tweet_dao import tweet_dao
from .database.user_dao import user_dao
from .database.quotation_dao import quotation_dao
from .utils.data_mapper import data_mapper
from .utils.config_manager import config
from .utils.logger import get_logger
from .utils.tweet_enricher import tweet_enricher
from .utils.simple_tweet_enricher import simple_tweet_enricher
from .utils.quotation_extractor import quotation_extractor
# from .utils.user_language_integration import UserLanguageIntegration  # 语言检测已禁用
from .models.tweet import Tweet
from .models.user import TwitterUser
# from .topic_engine import topic_engine  # 话题分析已移除
# from .kol_engine import kol_engine  # KOL分析已禁用
from .project_engine import project_engine


class TwitterCrawler:
    """Twitter数据爬虫"""
    
    def __init__(self):
        """初始化爬虫"""
        self.logger = get_logger(__name__)
        self.api_client = selected_api_client
        self.tweet_dao = tweet_dao
        self.user_dao = user_dao
        self.quotation_dao = quotation_dao
        self.data_mapper = data_mapper
        # self.topic_engine = topic_engine  # 话题分析已移除
        # self.kol_engine = kol_engine  # KOL分析已禁用
        self.project_engine = project_engine
        self.tweet_enricher = tweet_enricher
        self.quotation_extractor = quotation_extractor

        # 初始化用户语言集成器（已禁用）
        # from .api.chatgpt_client import chatgpt_client
        # self.user_language_integration = UserLanguageIntegration(
        #     db_manager=self.user_dao.db_manager,
        #     chatgpt_client=chatgpt_client
        # )

        # 爬取统计
        self.crawl_count = 0
        self.success_count = 0
        self.error_count = 0
        self.last_crawl_time = None
        
        self.logger.info("Twitter爬虫初始化完成")
    
    def crawl_tweets(self, list_id: str = None, list_ids: List[str] = None, max_pages: int = None, 
                    page_size: int = None, hours_limit: int = 2) -> bool:
        """
        爬取推文数据
        
        Args:
            list_id: 单个列表ID，如果不指定则使用配置中的默认值（向后兼容）
            list_ids: 多个列表ID列表，优先级高于list_id
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
            
            # 1. 从API获取数据（支持多个list并行处理，最多15页，只拉取过去8小时）
            api_data_list = self._fetch_api_data(list_id, list_ids, max_pages, page_size, hours_limit)
            
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
                    # 兼容两种API：TweetScout使用'user'，Twitter API使用'author'
                    user_data = api_data.get('user') or api_data.get('author')
                    if tweet_id and user_data and isinstance(user_data, dict):
                        user_data_map[tweet_id] = user_data
                except Exception as e:
                    self.logger.warning(f"构建用户数据映射失败: {e}")
                    continue
            
            # 2.3 提取引用关系数据
            self.logger.info("开始提取引用关系数据...")
            quotations = self.quotation_extractor.extract_quotations_from_api_data(api_data_list)
            valid_quotations = self.quotation_extractor.filter_valid_quotations(quotations)
            self.logger.info(f"引用关系数据提取完成，获得 {len(valid_quotations)} 条有效引用关系")
            
            # 2.4 增强推文数据（添加 kol_id 和 entity_id）
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
            
            # 保存引用关系数据
            quotation_saved_count = 0
            if valid_quotations:
                quotation_saved_count = self._save_quotations_to_database(valid_quotations)
                self.logger.info(f"成功保存 {quotation_saved_count} 条引用关系数据")
            
            # 4. 数据保存完成
            if tweet_saved_count > 0:
                self.logger.info(f"成功保存 {tweet_saved_count} 条推文到数据库")
                
                # 话题分析已移除 - 在其他独立脚本中处理
                # try:
                #     self.logger.info("开始进行话题分析...")
                #     topic_success = self.topic_engine.analyze_recent_tweets(hours=1, max_tweets=50)
                #     
                #     if topic_success:
                #         self.logger.info("话题分析完成")
                #     else:
                #         self.logger.warning("话题分析失败，但不影响主流程")
                #         
                # except Exception as e:
                #     self.logger.error(f"话题分析异常: {e}")
                
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

                # 进行活动检测和结构化
                try:
                    self.logger.info("开始进行活动检测和结构化...")
                    activity_success = self._detect_and_structure_activities(enriched_tweets)

                    if activity_success:
                        self.logger.info("活动检测和结构化完成")
                    else:
                        self.logger.warning("活动检测和结构化失败，但不影响主流程")

                except Exception as e:
                    self.logger.error(f"活动检测异常: {e}")

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
    
    def _fetch_api_data(self, list_id: str = None, list_ids: List[str] = None, max_pages: int = None, 
                       page_size: int = None, hours_limit: int = 2) -> List[Dict[str, Any]]:
        """
        从API获取数据（支持并行获取多个list）
        
        Args:
            list_id: 单个列表ID（向后兼容）
            list_ids: 多个列表ID列表，优先级高于list_id
            max_pages: 最大页数（不超过15页）
            page_size: 每页大小
            hours_limit: 时间限制（小时），只拉取过去N小时的推文
            
        Returns:
            API数据列表
        """
        try:
            # 确定要使用的list_ids列表
            if list_ids is not None:
                # 优先使用传入的list_ids
                target_list_ids = list_ids
            elif list_id is not None:
                # 向后兼容：如果只传入了单个list_id，转换为列表
                target_list_ids = [list_id]
            else:
                # 使用配置文件中的默认值
                target_list_ids = config.get('api.default_params.list_ids', [config.get('api.default_params.list_id')])
            
            self.logger.info(f"正在并行获取 {len(target_list_ids)} 个list的数据: {target_list_ids}, 时间限制: {hours_limit}小时")
            
            # 如果只有一个list，使用原有的串行逻辑
            if len(target_list_ids) == 1:
                list_id_single = target_list_ids[0]
                self.logger.info(f"单个list模式，list_id: {list_id_single}")
                
                api_data_list = self.api_client.fetch_all_tweets(
                    list_id=list_id_single,
                    max_pages=max_pages,
                    page_size=page_size,
                    hours_limit=hours_limit
                )
                
                # 获取API请求统计
                stats = self.api_client.get_request_stats()
                self.logger.info(f"API请求统计: {stats}")
                
                return api_data_list
            
            # 多个list的并行处理逻辑
            import concurrent.futures
            
            all_api_data = []
            
            # 使用线程池并行获取多个list的数据
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(target_list_ids)) as executor:
                # 提交所有任务
                future_to_list_id = {
                    executor.submit(
                        self.api_client.fetch_all_tweets,
                        list_id=single_list_id,
                        max_pages=max_pages,
                        page_size=page_size,
                        hours_limit=hours_limit
                    ): single_list_id for single_list_id in target_list_ids
                }
                
                # 收集结果
                for future in concurrent.futures.as_completed(future_to_list_id):
                    single_list_id = future_to_list_id[future]
                    try:
                        api_data = future.result()
                        if api_data:
                            self.logger.info(f"list_id {single_list_id} 获取到 {len(api_data)} 条数据")
                            all_api_data.extend(api_data)
                        else:
                            self.logger.warning(f"list_id {single_list_id} 未获取到数据")
                    except Exception as e:
                        self.logger.error(f"获取 list_id {single_list_id} 数据失败: {e}")
            
            # 获取API请求统计
            stats = self.api_client.get_request_stats()
            self.logger.info(f"并行API请求统计: {stats}")
            self.logger.info(f"总共获取到 {len(all_api_data)} 条API数据")
            
            return all_api_data
            
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

            # 语言检测已禁用，直接批量保存用户数据
            # enhanced_users = self._enhance_users_with_language(users)
            saved_count = self.user_dao.batch_upsert_users(users)

            return saved_count

        except Exception as e:
            self.logger.error(f"保存用户到数据库失败: {e}")
            return 0
    
    # def _enhance_users_with_language(self, users: List[TwitterUser]) -> List[TwitterUser]:
    #     """
    #     为用户列表添加语言检测信息（已禁用）
    #
    #     Args:
    #         users: 用户列表
    #
    #     Returns:
    #         增强后的用户列表
    #     """
    #     try:
    #         self.logger.info(f"开始为 {len(users)} 个用户进行语言检测...")
    #
    #         # 使用批量语言检测
    #         enhanced_users = self.user_language_integration.enhance_users_batch(
    #             users=users,
    #             use_ai_fallback=False  # 暂时不使用AI辅助，避免过多API调用
    #         )
    #
    #         self.logger.info(f"完成语言检测，增强了 {len(enhanced_users)} 个用户")
    #         return enhanced_users
    #
    #     except Exception as e:
    #         self.logger.error(f"用户语言检测失败: {e}")
    #         # 如果语言检测失败，设置默认语言并返回原用户列表
    #         for user in users:
    #             if not hasattr(user, 'language') or user.language is None:
    #                 user.language = "English"  # 默认设为English
    #         return users
    
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
    
    def _save_quotations_to_database(self, quotations: List[Dict[str, Any]]) -> int:
        """
        保存引用关系到数据库
        
        Args:
            quotations: 引用关系数据列表
            
        Returns:
            成功保存的数量
        """
        try:
            if not quotations:
                self.logger.info("没有引用关系数据需要保存")
                return 0
            
            # 确保数据表存在
            if not self.quotation_dao.create_table_if_not_exists():
                self.logger.error("创建引用关系表失败")
                return 0
            
            self.logger.info(f"开始保存 {len(quotations)} 条引用关系到数据库...")
            
            # 批量保存
            saved_count = self.quotation_dao.batch_insert_quotations(quotations)
            
            return saved_count
            
        except Exception as e:
            self.logger.error(f"保存引用关系到数据库失败: {e}")
            return 0

    def _detect_and_structure_activities(self, tweets: List[Tweet]) -> bool:
        """
        检测推文中的活动并结构化存储

        Args:
            tweets: 推文列表

        Returns:
            是否成功
        """
        try:
            from .api.chatgpt_client import chatgpt_client
            import json

            # 活动关键词列表（用于初步过滤）
            activity_keywords = [
                'campaign', 'airdrop', 'quest', 'reward', 'giveaway',
                'bounty', 'contest', 'prize', 'distribution', 'incentive',
                '空投', '活动', '奖励', '赠送'
            ]

            # 过滤包含活动关键词的推文
            candidate_tweets = []
            for tweet in tweets:
                if tweet.full_text:
                    text_lower = tweet.full_text.lower()
                    if any(keyword in text_lower for keyword in activity_keywords):
                        candidate_tweets.append(tweet)

            self.logger.info(f"从 {len(tweets)} 条推文中筛选出 {len(candidate_tweets)} 条候选活动推文")

            if not candidate_tweets:
                self.logger.info("没有发现包含活动关键词的推文")
                return True

            # 检测和结构化活动数据
            activity_count = 0
            for tweet in candidate_tweets:
                try:
                    # 1. 使用AI检测是否为真正的活动
                    is_activity = chatgpt_client.detect_campaign_announcement([tweet.full_text])

                    if is_activity:
                        self.logger.info(f"检测到活动推文: {tweet.id_str}")

                        # 2. 生成推文URL（使用通用格式，不需要用户名）
                        tweet_url = f"https://twitter.com/i/status/{tweet.id_str}"

                        # 3. 提取结构化数据
                        activity_data = chatgpt_client.extract_activity_structured_data(
                            tweet_text=tweet.full_text,
                            tweet_url=tweet_url,
                            tweet_time=str(tweet.created_at) if tweet.created_at else ""
                        )

                        if activity_data:
                            # 4. 将结构化数据转换为JSON字符串存储到activity_detail字段
                            activity_detail_json = json.dumps(activity_data, ensure_ascii=False)

                            # 5. 更新数据库
                            success = self._update_tweet_activity_status(
                                tweet_id=tweet.id_str,
                                is_activity=1,
                                activity_detail=activity_detail_json
                            )

                            if success:
                                activity_count += 1
                                self.logger.info(f"活动数据已结构化: {activity_data['title']}")
                        else:
                            self.logger.warning(f"无法提取活动结构化数据: {tweet.id_str}")

                except Exception as e:
                    self.logger.error(f"处理推文活动检测失败 {tweet.id_str}: {e}")
                    continue

            self.logger.info(f"成功检测并结构化 {activity_count} 条活动推文")
            return True

        except Exception as e:
            self.logger.error(f"活动检测和结构化失败: {e}")
            return False

    def _update_tweet_activity_status(self, tweet_id: str, is_activity: int,
                                     activity_detail: str) -> bool:
        """
        更新推文的活动状态

        Args:
            tweet_id: 推文ID
            is_activity: 是否为活动推文（0或1）
            activity_detail: 活动详情（JSON字符串）

        Returns:
            是否成功
        """
        try:
            table_name = self.tweet_dao.db_manager.db_config.get('tables', {}).get('tweet', 'twitter_tweet')

            sql = f"""
            UPDATE {table_name}
            SET is_activity = %s, activity_detail = %s
            WHERE id_str = %s
            """

            affected_rows = self.tweet_dao.db_manager.execute_update(
                sql, (is_activity, activity_detail, tweet_id)
            )

            return affected_rows > 0

        except Exception as e:
            self.logger.error(f"更新推文活动状态失败 {tweet_id}: {e}")
            return False

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
            'database_quotation_count': self.quotation_dao.get_quotation_count(),
            # 'topic_stats': self.topic_engine.get_topic_statistics(),  # 话题分析已移除
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
    
    def crawl_project_tweets(self, max_pages: int = None, page_size: int = None, hours_limit: int = 2) -> bool:
        """
        爬取项目推文数据（简化流程版本）
        
        Args:
            max_pages: 最大页数（不超过15页）
            page_size: 每页大小
            hours_limit: 时间限制（小时），只拉取过去N小时的推文，默认2小时
            
        Returns:
            是否成功
        """
        self.crawl_count += 1
        self.last_crawl_time = datetime.now()
        
        try:
            self.logger.info(f"开始爬取项目推文数据 (第 {self.crawl_count} 次，时间限制: {hours_limit}小时)")
            
            # 1. 从API获取数据（使用配置中的list_ids_project）
            list_ids_project = config.get('api.default_params.list_ids_project', [])
            if not list_ids_project:
                self.logger.error("配置文件中未找到list_ids_project")
                self.error_count += 1
                return False
            
            self.logger.info(f"使用项目列表IDs: {list_ids_project}")
            
            api_data_list = self._fetch_api_data(None, list_ids_project, max_pages, page_size, hours_limit)
            
            if not api_data_list:
                self.logger.warning("未获取到任何项目推文API数据")
                self.error_count += 1
                return False
            
            self.logger.info(f"从API获取到 {len(api_data_list)} 条项目推文原始数据")
            
            # 2. 数据映射和转换（简化版本）
            tweets = self._map_data_to_tweets(api_data_list)
            
            if not tweets:
                self.logger.warning("项目推文数据映射后没有有效的数据")
                self.error_count += 1
                return False
            
            self.logger.info(f"成功映射 {len(tweets)} 条项目推文数据")
            
            # 2.1 提取用户数据
            users = self._extract_users_from_api_data(api_data_list)
            self.logger.info(f"成功提取 {len(users)} 条用户数据")
            
            # 2.2 构建用户数据映射（用于推文增强）
            user_data_map = {}
            for api_data in api_data_list:
                try:
                    tweet_id = api_data.get('id_str')
                    # 兼容 'user' 和 'author' 两种字段（新接口使用 author）
                    user_data = api_data.get('user') or api_data.get('author')
                    if tweet_id and user_data and isinstance(user_data, dict):
                        user_data_map[tweet_id] = user_data
                except Exception as e:
                    self.logger.warning(f"构建用户数据映射失败: {e}")
                    continue
            
            # 2.3 项目推文极简化增强（使用专门的简化增强器，无复杂数据加载）
            self.logger.info("开始项目推文极简化增强...")
            enriched_tweets = simple_tweet_enricher.enrich_project_tweets_simple(tweets, user_data_map)
            self.logger.info(f"项目推文极简化增强完成，处理了 {len(enriched_tweets)} 条推文")
            
            # 3. 简化存储到数据库（跳过复杂的处理逻辑）
            # 先保存用户数据
            if users:
                user_saved_count = self._save_users_to_database(users)
                self.logger.info(f"成功保存 {user_saved_count} 条用户数据")
            
            # 保存项目推文数据（使用普通推文的入库逻辑）
            tweet_saved_count = self._save_tweets_to_database(enriched_tweets)
            
            # 4. 数据保存完成
            if tweet_saved_count > 0:
                self.logger.info(f"成功保存 {tweet_saved_count} 条项目推文到数据库")
                self.success_count += 1

                # 打印 API 调用统计
                api_stats = self.api_client.get_request_stats()
                self.logger.info("=" * 50)
                self.logger.info("📊 API 调用统计")
                self.logger.info("=" * 50)
                self.logger.info(f"总请求次数: {api_stats.get('total_requests', 0)}")
                self.logger.info(f"获取推文数: {api_stats.get('tweets_fetched', 0)}")
                self.logger.info(f"错误次数: {api_stats.get('error_count', 0)}")
                self.logger.info(f"成功率: {api_stats.get('success_rate', 0):.2f}%")
                if api_stats.get('total_requests', 0) > 0:
                    self.logger.info(f"平均每次请求获取推文数: {api_stats.get('avg_tweets_per_request', 0):.1f}")
                # 显示成本信息
                self.logger.info("=" * 50)
                self.logger.info("💰 API 成本统计")
                self.logger.info("=" * 50)
                self.logger.info(f"本次总成本: ${api_stats.get('total_cost_usd', 0):.6f} USD")
                self.logger.info(f"平均每次请求成本: ${api_stats.get('avg_cost_per_request', 0):.6f} USD")
                self.logger.info(f"每条推文平均成本: ${api_stats.get('total_cost_usd', 0) / max(api_stats.get('tweets_fetched', 1), 1):.6f} USD")
                self.logger.info("=" * 50)

                return True
            else:
                self.logger.error("保存项目推文到数据库失败")
                self.error_count += 1
                return False
                
        except Exception as e:
            self.logger.error(f"爬取项目推文数据异常: {e}")
            self.error_count += 1
            return False
    
    def close(self) -> None:
        """关闭爬虫，清理资源"""
        try:
            self.api_client.close()
            self.tweet_dao.db_manager.close()
            self.user_dao.db_manager.close()
            self.quotation_dao.db_manager.close()
            self.logger.info("爬虫资源已清理")
        except Exception as e:
            self.logger.error(f"清理爬虫资源时出错: {e}")


# 全局爬虫实例
crawler = TwitterCrawler() 