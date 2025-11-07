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
                                   hours_limit: int = 12) -> Generator[List[Dict[str, Any]], None, None]:
        """
        获取推文列表（支持分页和时间过滤）
        使用 next_cursor 机制进行真正的分页
        
        Args:
            list_id: 列表ID
            max_pages: 最大页数（默认15页，用于保护）
            page_size: 每页大小（建议值，实际由API返回决定）
            hours_limit: 时间限制（小时），只拉取过去N小时的推文，默认12小时
            
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
            
            # 过滤推文：只保留过去8小时内的
            valid_tweets = []
            for tweet in tweets:
                try:
                    # 尝试解析 created_at 字段
                    created_at_str = tweet.get('created_at', '')
                    if created_at_str:
                        # 使用 dateutil 解析各种格式的日期
                        tweet_time = date_parser.parse(created_at_str)
                        # 移除时区信息以便比较
                        if tweet_time.tzinfo:
                            tweet_time = tweet_time.replace(tzinfo=None)
                        
                        # 检查是否在时间范围内
                        if tweet_time >= time_cutoff:
                            valid_tweets.append(tweet)
                        else:
                            # 推文太旧，停止拉取
                            filtered_tweets += 1
                            self.logger.debug(f"推文时间 {tweet_time} 超过{hours_limit}小时限制，停止拉取")
                            stopped_by_time = True
                            break
                    else:
                        # 如果没有 created_at 字段，保留该推文
                        valid_tweets.append(tweet)
                        self.logger.warning(f"推文缺少 created_at 字段，已保留: {tweet.get('id_str', 'unknown')}")
                        
                except Exception as e:
                    # 解析失败，保留该推文
                    self.logger.warning(f"解析推文时间失败，已保留: {e}")
                    valid_tweets.append(tweet)
            
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
                        hours_limit: int = 12) -> List[Dict[str, Any]]:
        """
        获取所有推文（自动处理分页，最多15页，只拉取过去12小时）
        
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


# 全局API客户端实例
twitter_api = TwitterAPIClient() 