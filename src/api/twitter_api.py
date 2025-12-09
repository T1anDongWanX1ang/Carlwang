"""
Twitter API 客户端
用于从TweetScout API获取Twitter数据
"""
import requests
import time
import logging
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime, timedelta
from dateutil import parser as date_parser

from ..utils.config_manager import config


class TwitterAPIClient:
    """Twitter API客户端"""
    
    def __init__(self):
        """初始化API客户端"""
        self.api_config = config.get_api_config()
        self.base_url = self.api_config.get('base_url', '')
        self.headers = self.api_config.get('headers', {})
        self.default_params = self.api_config.get('default_params', {})
        self.pagination_config = self.api_config.get('pagination', {})
        self.timeout = self.api_config.get('timeout', 30)
        self.retry_attempts = self.api_config.get('retry_attempts', 3)
        self.retry_delay = self.api_config.get('retry_delay', 5)
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        self.logger = logging.getLogger(__name__)
        
        # 请求统计
        self.request_count = 0
        self.error_count = 0
        self.last_request_time = 0
    
    def _make_request(self, url: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        发起HTTP请求，包含重试机制
        
        Args:
            url: 请求URL
            params: 请求参数
            
        Returns:
            响应数据或None
        """
        if params is None:
            params = {}
        
        # 合并默认参数
        final_params = {**self.default_params, **params}
        
        for attempt in range(self.retry_attempts):
            try:
                # 请求限制：避免请求过于频繁
                current_time = time.time()
                if self.last_request_time > 0:
                    time_diff = current_time - self.last_request_time
                    if time_diff < 1:  # 最小间隔1秒
                        time.sleep(1 - time_diff)
                
                self.logger.info(f"发起API请求 (尝试 {attempt + 1}/{self.retry_attempts}): {url}")
                self.logger.debug(f"请求参数: {final_params}")
                
                response = self.session.get(
                    url,
                    params=final_params,
                    timeout=self.timeout
                )
                
                self.last_request_time = time.time()
                self.request_count += 1
                
                # 检查响应状态
                if response.status_code == 200:
                    data = response.json()
                    self.logger.info(f"API请求成功: {url}")
                    return data
                
                elif response.status_code == 429:
                    # 速率限制
                    self.logger.warning(f"API速率限制 (429)，等待 {self.retry_delay} 秒后重试")
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                
                elif response.status_code in [500, 502, 503, 504]:
                    # 服务器错误，可重试
                    self.logger.warning(f"服务器错误 ({response.status_code})，等待 {self.retry_delay} 秒后重试")
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                
                else:
                    # 其他错误
                    self.logger.error(f"API请求失败: {response.status_code} - {response.text}")
                    self.error_count += 1
                    return None
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"请求超时，尝试 {attempt + 1}/{self.retry_attempts}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    self.logger.error("请求超时，已达到最大重试次数")
                    self.error_count += 1
                    return None
            
            except requests.exceptions.RequestException as e:
                self.logger.error(f"请求异常: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    self.logger.error("网络异常，已达到最大重试次数")
                    self.error_count += 1
                    return None
            
            except Exception as e:
                self.logger.error(f"未知错误: {e}")
                self.error_count += 1
                return None
        
        return None
    
    def fetch_tweets(self, list_id: str = None, **kwargs) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """
        获取推文列表（单页），返回推文列表和下一页游标
        
        Args:
            list_id: 列表ID，如果不指定则使用默认值
            **kwargs: 其他请求参数
            
        Returns:
            (推文数据列表, next_cursor)
        """
        endpoint = self.api_config.get('endpoints', {}).get('list_tweets', '/list-tweets')
        # 确保URL正确构建
        base_url = self.base_url.rstrip('/')
        endpoint = endpoint.lstrip('/')
        url = f"{base_url}/{endpoint}"
        
        params = {}
        if list_id:
            params['list_id'] = list_id
        
        # 添加其他参数
        params.update(kwargs)
        
        response_data = self._make_request(url, params)
        
        if response_data:
            # TweetScout API返回格式为: {"tweets": [...], "next_cursor": "..."}
            if isinstance(response_data, dict):
                # 提取 next_cursor（用于分页）
                next_cursor = response_data.get('next_cursor') or response_data.get('cursor')
                
                # 首先尝试 "tweets" 字段
                tweets = response_data.get('tweets', [])
                if isinstance(tweets, list):
                    self.logger.info(f"成功获取 {len(tweets)} 条推文" + (f", next_cursor={next_cursor[:20]}..." if next_cursor else ", 无更多数据"))
                    return tweets, next_cursor
                
                # 然后尝试 "data" 字段（备用）
                tweets = response_data.get('data', [])
                if isinstance(tweets, list):
                    self.logger.info(f"成功获取 {len(tweets)} 条推文" + (f", next_cursor={next_cursor[:20]}..." if next_cursor else ", 无更多数据"))
                    return tweets, next_cursor
                
                # 如果都没有，记录可用字段
                self.logger.warning(f"响应格式不包含 'tweets' 或 'data' 字段，可用字段: {list(response_data.keys())}")
                return [], None
            elif isinstance(response_data, list):
                # 直接是推文数组（没有cursor信息）
                self.logger.info(f"成功获取 {len(response_data)} 条推文")
                return response_data, None
        
        return [], None
    
    def fetch_tweets_with_pagination(self, list_id: str = None, 
                                   max_pages: int = None, 
                                   page_size: int = None,
                                   hours_limit: int = 2) -> Generator[List[Dict[str, Any]], None, None]:
        """
        获取推文列表（支持分页和时间过滤）
        使用 next_cursor 机制进行真正的分页
        
        Args:
            list_id: 列表ID
            max_pages: 最大页数（默认15页，用于保护）
            page_size: 每页大小（建议值，实际由API返回决定）
            hours_limit: 时间限制（小时），只拉取过去N小时的推文，默认2小时
            
        Yields:
            每页的推文数据列表
        """
        # 设置最大页数为15（作为保护机制）
        if max_pages is None:
            max_pages = 15
        else:
            max_pages = min(max_pages, 15)
            
        if page_size is None:
            page_size = self.pagination_config.get('page_size', 100)
        
        # 计算时间截止点（过去8小时）
        time_cutoff = datetime.now() - timedelta(hours=hours_limit)
        self.logger.info(f"时间过滤: 只拉取 {time_cutoff.strftime('%Y-%m-%d %H:%M:%S')} 之后的推文（使用cursor分页）")
        
        page = 1
        total_tweets = 0
        filtered_tweets = 0
        stopped_by_time = False
        cursor = None  # 使用cursor进行分页
        
        while page <= max_pages:
            self.logger.info(f"获取第 {page} 页数据（最多{max_pages}页保护）" + (f", cursor={cursor[:20]}..." if cursor else ", 首页"))
            
            # 构建分页参数
            params = {}
            if page_size:
                params['count'] = page_size
            
            # 使用cursor进行分页（这是正确的方式）
            if cursor:
                params['cursor'] = cursor
            
            tweets, next_cursor = self.fetch_tweets(list_id=list_id, **params)
            
            if not tweets:
                self.logger.info(f"第 {page} 页没有数据，停止分页")
                break
            
            # 过滤推文：只保留过去hours_limit小时内的，并跟踪每个项目的时间状态
            valid_tweets = []
            old_tweet_count = 0  # 记录超时推文数量
            
            # 跟踪每个项目/账号的最新推文时间
            project_latest_times = {}  # {user_id: latest_tweet_time}
            project_has_valid_tweets = {}  # {user_id: bool} 本页是否有有效推文
            
            for tweet in tweets:
                try:
                    # 提取用户信息
                    user_info = tweet.get('user', {})
                    user_id = user_info.get('id_str', 'unknown')
                    user_name = user_info.get('name', 'Unknown')
                    
                    # 尝试解析 created_at 字段
                    created_at_str = tweet.get('created_at', '')
                    if created_at_str:
                        # 使用 dateutil 解析各种格式的日期
                        tweet_time = date_parser.parse(created_at_str)
                        # 移除时区信息以便比较
                        if tweet_time.tzinfo:
                            tweet_time = tweet_time.replace(tzinfo=None)
                        
                        # 更新该项目的最新推文时间
                        if user_id not in project_latest_times or tweet_time > project_latest_times[user_id]:
                            project_latest_times[user_id] = tweet_time
                        
                        # 检查是否在时间范围内
                        if tweet_time >= time_cutoff:
                            valid_tweets.append(tweet)
                            project_has_valid_tweets[user_id] = True
                            self.logger.debug(f"保留推文: {user_name} ({user_id}) {tweet_time}")
                        else:
                            # 推文太旧，记录但继续处理其他推文
                            old_tweet_count += 1
                            filtered_tweets += 1
                            self.logger.debug(f"跳过超时推文: {user_name} ({user_id}) {tweet_time} < {time_cutoff}")
                    else:
                        # 如果没有 created_at 字段，保留该推文
                        valid_tweets.append(tweet)
                        project_has_valid_tweets[user_id] = True
                        self.logger.warning(f"推文缺少 created_at 字段，已保留: {tweet.get('id_str', 'unknown')}")
                        
                except Exception as e:
                    # 解析失败，保留该推文
                    self.logger.warning(f"解析推文时间失败，已保留: {e}")
                    valid_tweets.append(tweet)
            
            # 智能停止判断：检查是否所有项目都已经超时
            should_stop_by_projects = self._should_stop_by_project_times(
                project_latest_times, 
                project_has_valid_tweets, 
                time_cutoff, 
                hours_limit
            )
            
            # 如果基于项目时间分析应该停止，则设置停止标志
            if should_stop_by_projects:
                stopped_by_time = True
            
            total_tweets += len(valid_tweets)
            self.logger.info(f"第 {page} 页获取到 {len(tweets)} 条推文，过滤后 {len(valid_tweets)} 条，累计 {total_tweets} 条有效推文")
            
            if valid_tweets:
                yield valid_tweets
            
            # 如果因为时间过滤停止，直接退出
            if stopped_by_time:
                self.logger.info(f"已到达时间边界（{hours_limit}小时前），停止拉取")
                break
            
            # 如果没有 next_cursor，说明已经到最后一页
            if not next_cursor:
                self.logger.info("API返回无更多数据（无next_cursor），停止分页")
                break
            
            # 更新cursor为下一页
            cursor = next_cursor
            page += 1
            
            # 页面间延迟
            time.sleep(1)
        
        if page > max_pages:
            self.logger.warning(f"达到最大页数限制（{max_pages}页），可能还有更多数据未拉取")
        
        self.logger.info(f"分页获取完成，总共获取 {total_tweets} 条有效推文（过滤 {filtered_tweets} 条），共 {page-1} 页")
    
    def fetch_all_tweets(self, list_id: str = None, 
                        max_pages: int = None, 
                        page_size: int = None,
                        hours_limit: int = 2) -> List[Dict[str, Any]]:
        """
        获取所有推文（自动处理分页，最多15页，只拉取过去2小时）
        
        Args:
            list_id: 列表ID
            max_pages: 最大页数（不超过15页）
            page_size: 每页大小
            hours_limit: 时间限制（小时），默认12小时
            
        Returns:
            所有推文数据列表
        """
        all_tweets = []
        
        try:
            for page_tweets in self.fetch_tweets_with_pagination(
                list_id=list_id, 
                max_pages=max_pages, 
                page_size=page_size,
                hours_limit=hours_limit
            ):
                all_tweets.extend(page_tweets)
                
                # 可以在这里添加进度回调
                self.logger.debug(f"当前已收集 {len(all_tweets)} 条推文")
            
        except Exception as e:
            self.logger.error(f"获取推文数据时发生错误: {e}")
        
        return all_tweets
    
    def get_request_stats(self) -> Dict[str, int]:
        """
        获取请求统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'total_requests': self.request_count,
            'error_count': self.error_count,
            'success_rate': (self.request_count - self.error_count) / max(self.request_count, 1) * 100
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.request_count = 0
        self.error_count = 0
    
    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()
    
    def _should_stop_by_project_times(self, 
                                     project_latest_times: Dict[str, datetime], 
                                     project_has_valid_tweets: Dict[str, bool], 
                                     time_cutoff: datetime, 
                                     hours_limit: int) -> bool:
        """
        基于项目级别的时间分析判断是否应该停止拉取
        
        Args:
            project_latest_times: 每个项目的最新推文时间 {user_id: latest_time}
            project_has_valid_tweets: 每个项目本页是否有有效推文 {user_id: bool}
            time_cutoff: 时间截止点
            hours_limit: 时间限制（小时）
            
        Returns:
            是否应该停止拉取
        """
        try:
            if not project_latest_times:
                self.logger.debug("没有项目时间数据，不基于项目时间停止")
                return False
            
            # 计算有多少个项目的最新推文已经超时
            total_projects = len(project_latest_times)
            overdue_projects = 0
            active_projects_with_valid_tweets = 0  # 有有效推文的活跃项目数
            
            project_analysis = []
            
            for user_id, latest_time in project_latest_times.items():
                is_overdue = latest_time < time_cutoff
                has_valid_tweets_this_page = project_has_valid_tweets.get(user_id, False)
                
                if is_overdue:
                    overdue_projects += 1
                    
                if has_valid_tweets_this_page:
                    active_projects_with_valid_tweets += 1
                
                project_analysis.append({
                    'user_id': user_id,
                    'latest_time': latest_time,
                    'is_overdue': is_overdue,
                    'has_valid_tweets': has_valid_tweets_this_page,
                    'time_diff_hours': (datetime.now() - latest_time).total_seconds() / 3600
                })
            
            # 记录详细的项目分析
            self.logger.debug(f"项目时间分析: 总项目数={total_projects}, 超时项目数={overdue_projects}, 有效推文项目数={active_projects_with_valid_tweets}")
            for analysis in project_analysis[:5]:  # 只显示前5个项目的详情
                self.logger.debug(f"  项目 {analysis['user_id']}: 最新推文={analysis['latest_time']}, "
                                f"超时={analysis['is_overdue']}, 有效推文={analysis['has_valid_tweets']}, "
                                f"时间差={analysis['time_diff_hours']:.1f}小时")
            
            # 停止条件1: 如果所有项目的最新推文都已经超时，则停止
            if overdue_projects == total_projects:
                self.logger.info(f"所有 {total_projects} 个项目的最新推文都已超过 {hours_limit} 小时限制，停止拉取")
                return True
            
            # 停止条件2: 如果本页没有任何项目产生有效推文，且大部分项目都已超时
            if active_projects_with_valid_tweets == 0 and overdue_projects >= total_projects * 0.7:
                self.logger.info(f"本页无任何项目产生有效推文，且 {overdue_projects}/{total_projects} 个项目已超时，停止拉取")
                return True
            
            # 停止条件3: 如果超时项目比例很高（>=90%），且活跃项目很少
            overdue_ratio = overdue_projects / total_projects
            if overdue_ratio >= 0.9 and active_projects_with_valid_tweets <= 1:
                self.logger.info(f"超时项目比例过高 ({overdue_ratio:.1%})，且活跃项目数量过少 ({active_projects_with_valid_tweets})，停止拉取")
                return True
            
            self.logger.debug(f"继续拉取: 超时比例={overdue_ratio:.1%}, 活跃项目数={active_projects_with_valid_tweets}")
            return False
            
        except Exception as e:
            self.logger.error(f"项目时间分析失败: {e}")
            # 发生异常时，保守地继续拉取
            return False


# 全局API客户端实例
twitter_api = TwitterAPIClient() 