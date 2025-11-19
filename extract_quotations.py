#!/usr/bin/env python3
"""
推特引用关系提取专用脚本
用于快速测试引用关系功能
"""
import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.twitter_api import twitter_api
from src.database.tweet_dao import tweet_dao
from src.database.user_dao import user_dao
from src.database.quotation_dao import quotation_dao
from src.utils.data_mapper import data_mapper
from src.utils.quotation_extractor import quotation_extractor
from src.utils.logger import get_logger


class QuotationCrawler:
    """专门用于引用关系提取的简化爬虫"""
    
    def __init__(self):
        """初始化爬虫"""
        self.logger = get_logger(__name__)
        self.api_client = twitter_api
        self.tweet_dao = tweet_dao
        self.user_dao = user_dao
        self.quotation_dao = quotation_dao
        self.data_mapper = data_mapper
        self.quotation_extractor = quotation_extractor
        
        # 统计信息
        self.crawl_count = 0
        self.success_count = 0
        self.error_count = 0
        
        self.logger.info("🔍 引用关系提取爬虫初始化完成")
    
    def crawl_and_extract_quotations(self, list_id: str = None, max_pages: int = 5, 
                                   page_size: int = 20, hours_limit: int = 2) -> dict:
        """
        爬取推文并提取引用关系
        
        Args:
            list_id: 列表ID，如果不指定则使用配置中的默认值
            max_pages: 最大页数
            page_size: 每页大小
            hours_limit: 时间限制（小时）
            
        Returns:
            结果统计字典
        """
        self.crawl_count += 1
        start_time = datetime.now()
        
        try:
            self.logger.info(f"🚀 开始爬取并提取引用关系 (第 {self.crawl_count} 次，时间限制: {hours_limit}小时)")
            
            # 1. 从API获取数据
            api_data_list = self._fetch_api_data(list_id, max_pages, page_size, hours_limit)
            
            if not api_data_list:
                self.logger.warning("❌ 未获取到任何API数据")
                self.error_count += 1
                return self._get_result_stats(start_time, 0, 0, 0, 0)
            
            self.logger.info(f"📥 从API获取到 {len(api_data_list)} 条原始数据")
            
            # 2. 提取引用关系数据
            self.logger.info("🔗 开始提取引用关系数据...")
            quotations = self.quotation_extractor.extract_quotations_from_api_data(api_data_list)
            valid_quotations = self.quotation_extractor.filter_valid_quotations(quotations)
            
            quotation_count = len(valid_quotations)
            self.logger.info(f"✅ 引用关系数据提取完成，获得 {quotation_count} 条有效引用关系")
            
            # 3. 数据映射和转换（仅用于保存推文和用户数据）
            tweets = self._map_data_to_tweets(api_data_list)
            users = self._extract_users_from_api_data(api_data_list)
            
            self.logger.info(f"📄 成功映射 {len(tweets)} 条推文数据，{len(users)} 条用户数据")
            
            # 4. 保存到数据库
            # 先保存用户数据
            user_saved_count = 0
            if users:
                user_saved_count = self._save_users_to_database(users)
                self.logger.info(f"👥 成功保存 {user_saved_count} 条用户数据")
            
            # 再保存推文数据
            tweet_saved_count = self._save_tweets_to_database(tweets)
            self.logger.info(f"📝 成功保存 {tweet_saved_count} 条推文数据")
            
            # 最后保存引用关系数据
            quotation_saved_count = 0
            if valid_quotations:
                quotation_saved_count = self._save_quotations_to_database(valid_quotations)
                self.logger.info(f"🔗 成功保存 {quotation_saved_count} 条引用关系数据")
            
            # 5. 生成统计信息
            stats = self.quotation_extractor.get_quotation_statistics(valid_quotations)
            if stats['total_quotations'] > 0:
                self.logger.info(f"📊 引用关系统计:")
                self.logger.info(f"   - 总引用数: {stats['total_quotations']}")
                self.logger.info(f"   - 引用用户数: {stats['unique_quoters']}")
                self.logger.info(f"   - 被引用用户数: {stats['unique_quoted']}")
                
                if stats['top_quoters']:
                    self.logger.info(f"   - 最活跃引用者: @{stats['top_quoters'][0]['user_name']} ({stats['top_quoters'][0]['quote_count']}次)")
                
                if stats['top_quoted']:
                    self.logger.info(f"   - 最常被引用: @{stats['top_quoted'][0]['user_name']} ({stats['top_quoted'][0]['quoted_count']}次)")
            
            self.success_count += 1
            return self._get_result_stats(start_time, len(api_data_list), tweet_saved_count, 
                                        user_saved_count, quotation_saved_count)
            
        except Exception as e:
            self.logger.error(f"❌ 爬取和提取引用关系失败: {e}")
            self.error_count += 1
            return self._get_result_stats(start_time, 0, 0, 0, 0)
    
    def _fetch_api_data(self, list_id: str = None, max_pages: int = 5, 
                       page_size: int = 20, hours_limit: int = 2) -> list:
        """从API获取数据"""
        try:
            from src.utils.config_manager import config
            
            # 使用配置中的默认值
            if not list_id:
                list_id = config.get('api', {}).get('default_params', {}).get('list_id')
            if not page_size:
                page_size = config.get('api', {}).get('pagination', {}).get('page_size', 20)
            
            self.logger.info(f"📡 正在从API获取数据，list_id: {list_id}, 页数限制: {max_pages}, 时间限制: {hours_limit}小时")
            
            # 调用API获取推文数据
            api_data_generator = self.api_client.fetch_tweets_with_pagination(
                list_id=list_id,
                max_pages=max_pages,
                page_size=page_size,
                hours_limit=hours_limit
            )
            
            # 将生成器转换为列表并展开所有推文
            api_data_list = []
            for page_data in api_data_generator:
                if isinstance(page_data, list):
                    api_data_list.extend(page_data)
                elif isinstance(page_data, dict):
                    api_data_list.append(page_data)
            
            # 获取API统计信息
            api_stats = self.api_client.get_request_stats()
            self.logger.info(f"📈 API请求统计: {api_stats}")
            
            return api_data_list
            
        except Exception as e:
            self.logger.error(f"❌ API数据获取失败: {e}")
            return []
    
    def _map_data_to_tweets(self, api_data_list: list) -> list:
        """将API数据映射为推文对象"""
        try:
            tweets = []
            for api_data in api_data_list:
                try:
                    tweet = self.data_mapper.map_api_data_to_tweet(api_data)
                    if tweet and tweet.validate():
                        tweets.append(tweet)
                except Exception as e:
                    self.logger.warning(f"推文数据映射失败: {e}")
                    continue
            return tweets
        except Exception as e:
            self.logger.error(f"批量推文数据映射失败: {e}")
            return []
    
    def _extract_users_from_api_data(self, api_data_list: list) -> list:
        """从API数据中提取用户数据"""
        try:
            users = []
            seen_user_ids = set()
            
            for api_data in api_data_list:
                try:
                    user_data = api_data.get('user')
                    if user_data and isinstance(user_data, dict):
                        user_id = user_data.get('id_str')
                        if user_id and user_id not in seen_user_ids:
                            user = self.data_mapper.map_api_data_to_user(user_data)
                            if user and user.validate():
                                users.append(user)
                                seen_user_ids.add(user_id)
                    
                    # 也提取被引用推文的用户数据
                    quoted_status = api_data.get('quoted_status')
                    if quoted_status and isinstance(quoted_status, dict):
                        quoted_user_data = quoted_status.get('user')
                        if quoted_user_data and isinstance(quoted_user_data, dict):
                            quoted_user_id = quoted_user_data.get('id_str')
                            if quoted_user_id and quoted_user_id not in seen_user_ids:
                                quoted_user = self.data_mapper.map_api_data_to_user(quoted_user_data)
                                if quoted_user and quoted_user.validate():
                                    users.append(quoted_user)
                                    seen_user_ids.add(quoted_user_id)
                                    
                except Exception as e:
                    self.logger.warning(f"用户数据提取失败: {e}")
                    continue
                    
            return users
        except Exception as e:
            self.logger.error(f"批量用户数据提取失败: {e}")
            return []
    
    def _save_users_to_database(self, users: list) -> int:
        """保存用户数据到数据库"""
        try:
            if not users:
                return 0
            return self.user_dao.batch_upsert_users(users)
        except Exception as e:
            self.logger.error(f"保存用户数据失败: {e}")
            return 0
    
    def _save_tweets_to_database(self, tweets: list) -> int:
        """保存推文数据到数据库"""
        try:
            if not tweets:
                return 0
            return self.tweet_dao.batch_upsert_tweets(tweets)
        except Exception as e:
            self.logger.error(f"保存推文数据失败: {e}")
            return 0
    
    def _save_quotations_to_database(self, quotations: list) -> int:
        """保存引用关系到数据库"""
        try:
            if not quotations:
                return 0
            
            # 确保数据表存在
            if not self.quotation_dao.create_table_if_not_exists():
                self.logger.error("创建引用关系表失败")
                return 0
            
            return self.quotation_dao.batch_insert_quotations(quotations)
        except Exception as e:
            self.logger.error(f"保存引用关系数据失败: {e}")
            return 0
    
    def _get_result_stats(self, start_time, raw_count: int, tweet_count: int, 
                         user_count: int, quotation_count: int) -> dict:
        """生成结果统计"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return {
            'success': quotation_count > 0,
            'duration_seconds': round(duration, 2),
            'raw_data_count': raw_count,
            'tweets_saved': tweet_count,
            'users_saved': user_count,
            'quotations_saved': quotation_count,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'crawl_count': self.crawl_count,
            'success_count': self.success_count,
            'error_count': self.error_count
        }
    
    def get_statistics(self) -> dict:
        """获取爬虫统计信息"""
        return {
            'crawl_count': self.crawl_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': (self.success_count / max(self.crawl_count, 1)) * 100,
            'api_stats': self.api_client.get_request_stats(),
            'database_tweet_count': self.tweet_dao.get_tweet_count(),
            'database_user_count': self.user_dao.get_user_count(),
            'database_quotation_count': self.quotation_dao.get_quotation_count()
        }


def main():
    """主函数"""
    import argparse
    
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='推特引用关系提取专用脚本')
    parser.add_argument('--list-id', type=str, help='推特列表ID')
    parser.add_argument('--max-pages', type=int, default=5, help='最大页数 (默认: 5)')
    parser.add_argument('--page-size', type=int, default=20, help='每页大小 (默认: 20)')
    parser.add_argument('--hours-limit', type=int, default=2, help='时间限制小时数 (默认: 2)')
    parser.add_argument('--quiet', '-q', action='store_true', help='静默模式')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    try:
        print("🔍 推特引用关系提取脚本")
        print("=" * 50)
        
        # 创建爬虫实例
        crawler = QuotationCrawler()
        
        # 执行爬取和提取
        result = crawler.crawl_and_extract_quotations(
            list_id=args.list_id,
            max_pages=args.max_pages,
            page_size=args.page_size,
            hours_limit=args.hours_limit
        )
        
        # 输出结果
        print("\n📊 执行结果:")
        print(f"   ✅ 成功: {result['success']}")
        print(f"   ⏱️  耗时: {result['duration_seconds']} 秒")
        print(f"   📥 原始数据: {result['raw_data_count']} 条")
        print(f"   📝 推文保存: {result['tweets_saved']} 条")
        print(f"   👥 用户保存: {result['users_saved']} 条") 
        print(f"   🔗 引用关系: {result['quotations_saved']} 条")
        
        # 获取统计信息
        stats = crawler.get_statistics()
        print(f"\n📈 数据库统计:")
        print(f"   📝 总推文数: {stats['database_tweet_count']}")
        print(f"   👥 总用户数: {stats['database_user_count']}")
        print(f"   🔗 总引用关系数: {stats['database_quotation_count']}")
        
        # 输出成功率
        print(f"\n🎯 爬虫统计:")
        print(f"   总执行次数: {stats['crawl_count']}")
        print(f"   成功次数: {stats['success_count']}")
        print(f"   失败次数: {stats['error_count']}")
        print(f"   成功率: {stats['success_rate']:.1f}%")
        
        return 0 if result['success'] else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行")
        return 130
    except Exception as e:
        print(f"\n❌ 脚本执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)