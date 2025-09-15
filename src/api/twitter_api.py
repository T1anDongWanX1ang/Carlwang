"""
Twitter API 客户端
用于从TweetScout API获取Twitter数据
"""
import requests
import time
import logging
from typing import Dict, Any, List, Optional, Generator

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
    
    def fetch_tweets(self, list_id: str = None, **kwargs) -> List[Dict[str, Any]]:
        """
        获取推文列表（单页）
        
        Args:
            list_id: 列表ID，如果不指定则使用默认值
            **kwargs: 其他请求参数
            
        Returns:
            推文数据列表
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
            # TweetScout API返回格式为: {"tweets": [...]}
            if isinstance(response_data, dict):
                # 首先尝试 "tweets" 字段
                tweets = response_data.get('tweets', [])
                if isinstance(tweets, list):
                    self.logger.info(f"成功获取 {len(tweets)} 条推文")
                    return tweets
                
                # 然后尝试 "data" 字段（备用）
                tweets = response_data.get('data', [])
                if isinstance(tweets, list):
                    self.logger.info(f"成功获取 {len(tweets)} 条推文")
                    return tweets
                
                # 如果都没有，记录可用字段
                self.logger.warning(f"响应格式不包含 'tweets' 或 'data' 字段，可用字段: {list(response_data.keys())}")
                return []
            elif isinstance(response_data, list):
                # 直接是推文数组
                self.logger.info(f"成功获取 {len(response_data)} 条推文")
                return response_data
        
        return []
    
    def fetch_tweets_with_pagination(self, list_id: str = None, 
                                   max_pages: int = None, 
                                   page_size: int = None) -> Generator[List[Dict[str, Any]], None, None]:
        """
        获取推文列表（支持分页）
        
        Args:
            list_id: 列表ID
            max_pages: 最大页数
            page_size: 每页大小
            
        Yields:
            每页的推文数据列表
        """
        if max_pages is None:
            max_pages = self.pagination_config.get('max_pages', 10)
        if page_size is None:
            page_size = self.pagination_config.get('page_size', 100)
        
        page = 1
        total_tweets = 0
        
        while page <= max_pages:
            self.logger.info(f"获取第 {page} 页数据，每页 {page_size} 条")
            
            # 构建分页参数
            params = {}
            if page_size:
                params['count'] = page_size
            
            # 根据TweetScout API文档，可能需要cursor而不是page
            if page > 1:
                # 这里可能需要根据实际API文档调整分页方式
                params['page'] = page
            
            tweets = self.fetch_tweets(list_id=list_id, **params)
            
            if not tweets:
                self.logger.info(f"第 {page} 页没有数据，停止分页")
                break
            
            total_tweets += len(tweets)
            self.logger.info(f"第 {page} 页获取到 {len(tweets)} 条推文，累计 {total_tweets} 条")
            
            yield tweets
            
            # 如果返回的数据少于请求的页面大小，说明已经到最后一页
            if len(tweets) < page_size:
                self.logger.info("已获取所有数据")
                break
            
            page += 1
            
            # 页面间延迟
            time.sleep(1)
        
        self.logger.info(f"分页获取完成，总共获取 {total_tweets} 条推文，共 {page-1} 页")
    
    def fetch_all_tweets(self, list_id: str = None, 
                        max_pages: int = None, 
                        page_size: int = None) -> List[Dict[str, Any]]:
        """
        获取所有推文（自动处理分页）
        
        Args:
            list_id: 列表ID
            max_pages: 最大页数
            page_size: 每页大小
            
        Returns:
            所有推文数据列表
        """
        all_tweets = []
        
        try:
            for page_tweets in self.fetch_tweets_with_pagination(
                list_id=list_id, 
                max_pages=max_pages, 
                page_size=page_size
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