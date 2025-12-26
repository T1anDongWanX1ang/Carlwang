#!/usr/bin/env python3
"""
推特历史数据回测脚本
用于指定handle的推文数据入库
"""
import json
import logging
import requests
import argparse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.tweet import Tweet
from src.database.connection import db_manager


class BackTestTweetCrawler:
    """推特历史数据回测爬虫"""
    
    def __init__(self, config_path: str = "config/config.json", start_time: str = None, end_time: str = None, target_handle: str = None):
        """
        初始化爬虫
        
        Args:
            config_path: 配置文件路径
            start_time: 开始时间 (ISO格式字符串，如 "2025-11-07T16:18:00Z")，可覆盖配置文件
            end_time: 结束时间 (ISO格式字符串，如 "2025-11-08T16:18:00Z")，可覆盖配置文件
            target_handle: 目标用户handle，可覆盖配置文件
        """
        self.config = self._load_config(config_path)
        self.api_key = self.config['api']['headers']['ApiKey']
        self.base_url = "https://api.tweetscout.io/v2"
        self.logger = self._setup_logger()
        
        # 从配置文件或参数中获取目标handle（单个handle模式）
        self.target_handle = target_handle or self._get_default_handle()
        
        # 从配置文件或参数中获取时间范围
        self.start_time, self.end_time = self._parse_time_range(start_time, end_time)
        
        # 线程锁，用于并发控制
        self._request_lock = threading.Lock()
        self._last_request_time = 0
        
        self.logger.info(f"初始化完成 - 目标用户: {self.target_handle}, 时间范围: {self.start_time} ~ {self.end_time}")
    
    def _get_default_handle(self) -> str:
        """获取默认handle"""
        # 优先从targets中获取第一个enabled的handle
        targets = self.config.get('back_test', {}).get('targets', [])
        for target in targets:
            if target.get('enabled', False):
                return target.get('handle')
        
        # 如果没有enabled的target，使用default_config或默认值
        default_config = self.config.get('back_test', {}).get('default_config', {})
        return default_config.get('default_handle', 'ArweaveEco')
    
    def _get_target_config(self, handle: str = None) -> Dict[str, Any]:
        """
        获取目标handle的配置信息
        
        Args:
            handle: 目标handle
            
        Returns:
            目标配置字典
        """
        if not handle:
            handle = self.target_handle
            
        targets = self.config.get('back_test', {}).get('targets', [])
        for target in targets:
            if target.get('handle', '').lower() == handle.lower():
                return target
        
        # 如果没找到目标配置，返回默认配置
        return self.config.get('back_test', {}).get('default_config', {})
    
    def _rate_limit_request(self):
        """API请求频率限制"""
        concurrent_config = self.config.get('back_test', {}).get('concurrent', {})
        delay = concurrent_config.get('delay_between_requests', 1.0)
        
        with self._request_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            if time_since_last < delay:
                sleep_time = delay - time_since_last
                time.sleep(sleep_time)
            self._last_request_time = time.time()
    
    def _parse_time_range(self, start_time_param: str = None, end_time_param: str = None) -> tuple[datetime, datetime]:
        """
        解析时间范围
        
        Args:
            start_time_param: 参数传入的开始时间
            end_time_param: 参数传入的结束时间
            
        Returns:
            (开始时间, 结束时间) 的datetime对象元组
        """
        start_time = None
        end_time = None
        
        # 优先使用参数传入的时间
        if start_time_param:
            try:
                if start_time_param.endswith('Z'):
                    start_time = datetime.fromisoformat(start_time_param[:-1]).replace(tzinfo=timezone.utc)
                else:
                    start_time = datetime.fromisoformat(start_time_param).replace(tzinfo=timezone.utc)
            except ValueError as e:
                self.logger.warning(f"解析参数开始时间失败: {start_time_param}, 错误: {e}, 使用配置文件时间")
        
        if end_time_param:
            try:
                if end_time_param.endswith('Z'):
                    end_time = datetime.fromisoformat(end_time_param[:-1]).replace(tzinfo=timezone.utc)
                else:
                    end_time = datetime.fromisoformat(end_time_param).replace(tzinfo=timezone.utc)
            except ValueError as e:
                self.logger.warning(f"解析参数结束时间失败: {end_time_param}, 错误: {e}, 使用配置文件时间")
        
        # 如果参数没有提供时间，从目标特定配置或默认配置获取
        if not start_time or not end_time:
            # 首先尝试获取目标特定的配置
            target_config = self._get_target_config(self.target_handle)
            
            if not start_time:
                config_start = target_config.get('start_time')
                if config_start:
                    try:
                        if config_start.endswith('Z'):
                            start_time = datetime.fromisoformat(config_start[:-1]).replace(tzinfo=timezone.utc)
                        else:
                            start_time = datetime.fromisoformat(config_start).replace(tzinfo=timezone.utc)
                    except ValueError as e:
                        self.logger.warning(f"解析目标配置开始时间失败: {config_start}, 错误: {e}")
                
                # 如果目标配置没有时间，使用默认配置
                if not start_time:
                    default_config = self.config.get('back_test', {}).get('default_config', {})
                    default_start = default_config.get('start_time')
                    if default_start:
                        try:
                            if default_start.endswith('Z'):
                                start_time = datetime.fromisoformat(default_start[:-1]).replace(tzinfo=timezone.utc)
                            else:
                                start_time = datetime.fromisoformat(default_start).replace(tzinfo=timezone.utc)
                        except ValueError as e:
                            self.logger.warning(f"解析默认配置开始时间失败: {default_start}, 错误: {e}")
            
            if not end_time:
                config_end = target_config.get('end_time')
                if config_end:
                    try:
                        if config_end.endswith('Z'):
                            end_time = datetime.fromisoformat(config_end[:-1]).replace(tzinfo=timezone.utc)
                        else:
                            end_time = datetime.fromisoformat(config_end).replace(tzinfo=timezone.utc)
                    except ValueError as e:
                        self.logger.warning(f"解析目标配置结束时间失败: {config_end}, 错误: {e}")
                
                # 如果目标配置没有时间，使用默认配置
                if not end_time:
                    default_config = self.config.get('back_test', {}).get('default_config', {})
                    default_end = default_config.get('end_time')
                    if default_end:
                        try:
                            if default_end.endswith('Z'):
                                end_time = datetime.fromisoformat(default_end[:-1]).replace(tzinfo=timezone.utc)
                            else:
                                end_time = datetime.fromisoformat(default_end).replace(tzinfo=timezone.utc)
                        except ValueError as e:
                            self.logger.warning(f"解析默认配置结束时间失败: {default_end}, 错误: {e}")
        
        # 默认时间范围（如果还没有设置）
        if not start_time:
            start_time = datetime(2025, 11, 7, 16, 18, tzinfo=timezone.utc)
        if not end_time:
            end_time = datetime(2025, 11, 8, 16, 18, tzinfo=timezone.utc)
        
        # 确保开始时间早于结束时间
        if start_time >= end_time:
            self.logger.warning(f"开始时间 {start_time} 晚于或等于结束时间 {end_time}，调整结束时间")
            end_time = start_time + timedelta(hours=24)  # 默认时间范围为24小时
        
        return start_time, end_time
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            raise
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger('back_test_tweet')
        logger.setLevel(logging.INFO)  # 改为INFO级别
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def search_tweets(self, query: str, next_cursor: str = "") -> Dict[str, Any]:
        """
        获取用户推文（带频率限制）
        
        Args:
            query: 用户handle（如 KAVA_CHAIN）
            next_cursor: 分页游标
            
        Returns:
            API响应数据
        """
        # 执行频率限制
        self._rate_limit_request()
        
        url = f"{self.base_url}/user-tweets"
        headers = {
            'Accept': 'application/json',
            'ApiKey': self.api_key,
            'Content-Type': 'application/json'
        }
        data = {
            "cursor": next_cursor,
            "link": f"https://twitter.com/{query}",
            "user_id": ""
        }
        
        try:
            self.logger.info(f"获取用户推文: handle={query}, cursor={next_cursor}")
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            # 记录响应内容以供调试（仅在需要时启用）
            response_data = response.json()
            # self.logger.debug(f"API响应: {response_data}")  # 注释掉详细日志
            return response_data
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API请求失败: {e}")
            # 记录更详细的错误信息
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_content = e.response.text
                    self.logger.error(f"API错误响应: {error_content}")
                except:
                    self.logger.error(f"无法解析错误响应内容")
            raise
    
    def _parse_tweet_time(self, created_at: str) -> Optional[datetime]:
        """
        解析推文时间
        
        Args:
            created_at: 推文创建时间字符串
            
        Returns:
            解析后的datetime对象
        """
        if not created_at:
            return None
            
        try:
            # Twitter API时间格式: "Wed Oct 10 20:19:24 +0000 2018"
            dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
            return dt
        except ValueError:
            try:
                # 尝试ISO格式
                if created_at.endswith('Z'):
                    dt = datetime.fromisoformat(created_at[:-1]).replace(tzinfo=timezone.utc)
                else:
                    dt = datetime.fromisoformat(created_at)
                    # 如果没有时区信息，假设是UTC
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                try:
                    # 尝试其他常见格式
                    for fmt in [
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%d %H:%M:%S.%f",
                        "%Y-%m-%dT%H:%M:%S.%f"
                    ]:
                        try:
                            dt = datetime.strptime(created_at, fmt)
                            # 没有时区信息，假设是UTC
                            return dt.replace(tzinfo=timezone.utc)
                        except ValueError:
                            continue
                    
                    self.logger.warning(f"无法解析时间格式: {created_at}")
                    return None
                except Exception as e:
                    self.logger.warning(f"解析时间时发生异常: {created_at}, 错误: {e}")
                    return None
    
    def _is_tweet_in_time_range(self, tweet: Dict[str, Any]) -> bool:
        """
        检查推文是否在时间范围内
        
        Args:
            tweet: 推文数据
            
        Returns:
            是否在时间范围内
        """
        created_at = tweet.get('created_at')
        if not created_at:
            return False
        
        tweet_time = self._parse_tweet_time(created_at)
        if not tweet_time:
            return False
        
        return self.start_time <= tweet_time <= self.end_time
    
    def _filter_tweets_by_author_and_retweets(self, tweets: List[Dict[str, Any]], target_screen_name: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """
        过滤推文，只保留指定作者自己发布的推文：1) 原创推文，2) 转发推文
        
        Args:
            tweets: 推文列表
            target_screen_name: 目标用户screen_name
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            过滤后的推文列表
        """
        filtered_tweets = []
        
        for tweet in tweets:
            # 检查顶层推文的作者是否匹配
            user = tweet.get('user', {})
            screen_name = user.get('screen_name', '')
            
            if screen_name.lower() == target_screen_name.lower():
                # 检查时间是否在时间范围内
                tweet_time = self._parse_tweet_time(tweet.get('created_at', ''))
                if tweet_time:
                    # 确保时间对象都是datetime类型并且时区一致
                    if tweet_time.tzinfo is None:
                        # 如果tweet_time没有时区信息，假设是UTC
                        tweet_time = tweet_time.replace(tzinfo=timezone.utc)
                    
                    # 确保start_time和end_time是datetime对象且有时区信息
                    if isinstance(start_time, str):
                        try:
                            if start_time.endswith('Z'):
                                start_time = datetime.fromisoformat(start_time[:-1]).replace(tzinfo=timezone.utc)
                            else:
                                start_time = datetime.fromisoformat(start_time).replace(tzinfo=timezone.utc)
                        except:
                            self.logger.warning(f"无法解析start_time: {start_time}")
                            continue
                    elif start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=timezone.utc)
                    
                    if isinstance(end_time, str):
                        try:
                            if end_time.endswith('Z'):
                                end_time = datetime.fromisoformat(end_time[:-1]).replace(tzinfo=timezone.utc)
                            else:
                                end_time = datetime.fromisoformat(end_time).replace(tzinfo=timezone.utc)
                        except:
                            self.logger.warning(f"无法解析end_time: {end_time}")
                            continue
                    elif end_time.tzinfo is None:
                        end_time = end_time.replace(tzinfo=timezone.utc)
                    
                    if start_time <= tweet_time <= end_time:
                        # 检查是否为原创推文或转发推文
                        retweeted_status = tweet.get('retweeted_status')
                        
                        if retweeted_status is not None:
                            # 这是一条转发推文
                            filtered_tweets.append(tweet)
                            # self.logger.debug(f"保留转发推文: {tweet.get('id_str')} - {screen_name}")
                        else:
                            # 这是一条原创推文（不是转发）
                            filtered_tweets.append(tweet)
                            # self.logger.debug(f"保留原创推文: {tweet.get('id_str')} - {screen_name}")
                    else:
                        # self.logger.debug(f"推文时间超出范围，跳过: {tweet.get('id_str')} - {tweet.get('created_at')} (解析为: {tweet_time})")
                        pass
                else:
                    # self.logger.debug(f"推文时间解析失败，跳过: {tweet.get('id_str')} - {tweet.get('created_at')}")
                    pass
            else:
                # self.logger.debug(f"推文作者不匹配，跳过: {screen_name} != {target_screen_name}")
                pass
        
        return filtered_tweets
    
    def _convert_to_tweet_object(self, tweet_data: Dict[str, Any], user_id: str) -> Tweet:
        """
        将API数据转换为Tweet对象
        
        Args:
            tweet_data: API返回的推文数据
            user_id: 用户ID（从screen_name映射）
            
        Returns:
            Tweet对象
        """
        # 构建推文URL
        user_screen_name = tweet_data.get('user', {}).get('screen_name', '')
        tweet_url = f"https://twitter.com/{user_screen_name}/status/{tweet_data['id_str']}"
        
        # 提取链接URL
        link_url = self._extract_link_from_entities(tweet_data.get('entities', []))
        
        # 创建Tweet对象，注意user_id字段在Tweet模型中没有直接定义，需要通过其他方式处理
        tweet = Tweet(
            id_str=tweet_data['id_str'],
            conversation_id_str=tweet_data.get('conversation_id_str'),
            in_reply_to_status_id_str=tweet_data.get('in_reply_to_status_id_str'),
            full_text=tweet_data.get('full_text'),
            created_at=tweet_data.get('created_at'),
            bookmark_count=tweet_data.get('bookmark_count', 0),
            favorite_count=tweet_data.get('favorite_count', 0),
            quote_count=tweet_data.get('quote_count', 0),
            reply_count=tweet_data.get('reply_count', 0),
            retweet_count=tweet_data.get('retweet_count', 0),
            view_count=tweet_data.get('view_count', 0),
            tweet_url=tweet_url,
            link_url=link_url,
            is_valid=1  # 默认设为有效
        )
        
        # 手动添加user_id和user_name字段到Tweet对象
        setattr(tweet, 'user_id', user_id)
        setattr(tweet, 'user_name', user_screen_name)
        
        return tweet
    
    def _extract_link_from_entities(self, entities: List[Dict[str, Any]]) -> Optional[str]:
        """
        从entities数组中提取第一个type为photo的link数据
        
        Args:
            entities: API返回的entities数组
            
        Returns:
            提取的链接URL或None
        """
        try:
            if not entities or not isinstance(entities, list):
                return None
            
            for entity in entities:
                if isinstance(entity, dict):
                    entity_type = entity.get('type')
                    if entity_type == 'photo':
                        link = entity.get('link')
                        if link and isinstance(link, str):
                            return link.strip()
            
            return None
            
        except Exception as e:
            self.logger.warning(f"提取entities链接失败: {e}")
            return None
    
    def _save_to_database(self, tweets: List[Tweet]) -> int:
        """
        保存推文到数据库
        
        Args:
            tweets: 推文列表
            
        Returns:
            成功保存的数量
        """
        if not tweets:
            return 0
        
        success_count = 0
        table_name = "twitter_tweet_back_test_10_percent"
        
        for tweet in tweets:
            try:
                # 构建插入SQL - 只包含数据库表中实际存在的字段
                sql = f"""
                INSERT INTO {table_name} (
                    id_str, in_reply_to_status_id_str,
                    full_text, created_at_datetime,
                    bookmark_count, favorite_count, quote_count, reply_count,
                    retweet_count, view_count, update_time,
                    user_id, tweet_url, user_name
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """
                
                tweet_data = tweet.to_dict()
                params = (
                    tweet_data['id_str'],
                    tweet_data['in_reply_to_status_id_str'],
                    tweet_data['full_text'],
                    tweet_data['created_at_datetime'],
                    tweet_data['bookmark_count'],
                    tweet_data['favorite_count'],
                    tweet_data['quote_count'],
                    tweet_data['reply_count'],
                    tweet_data['retweet_count'],
                    tweet_data['view_count'],
                    tweet_data['update_time'],
                    getattr(tweet, 'user_id', None),
                    tweet_data['tweet_url'],
                    getattr(tweet, 'user_name', None)  # user.screen_name映射到user_name
                )
                
                affected_rows = db_manager.execute_update(sql, params)
                if affected_rows > 0:
                    success_count += 1
                    self.logger.info(f"推文保存成功: {tweet.id_str}")
                else:
                    self.logger.warning(f"推文保存失败: {tweet.id_str}")
                    
            except Exception as e:
                self.logger.error(f"保存推文失败: {tweet.id_str}, 错误: {e}")
                continue
        
        return success_count
    
    def crawl_tweets_for_handle(self, handle: str = None, max_pages: int = None, start_time: datetime = None, end_time: datetime = None) -> int:
        """
        爬取指定handle的推文
        
        Args:
            handle: Twitter用户名（screen_name），如不提供则使用类初始化时的target_handle
            max_pages: 最大分页数，仅用作保护机制，如不提供则无限制（基于时间停止）
            start_time: 开始时间，如不提供则使用类初始化时的start_time
            end_time: 结束时间，如不提供则使用类初始化时的end_time
            
        Returns:
            保存成功的推文数量
        """
        # 使用参数或类属性中的值
        actual_handle = handle or self.target_handle
        actual_start_time = start_time or self.start_time
        actual_end_time = end_time or self.end_time
        
        # max_pages仅作为保护机制，防止无限循环，默认为None（无限制）
        if max_pages is None:
            max_pages = 1000  # 设置一个很大的数字作为保护机制
        
        self.logger.info(f"开始爬取用户 {actual_handle} 的推文数据，基于时间范围自动停止：{actual_start_time} ~ {actual_end_time}")
        
        total_saved = 0
        next_cursor = ""
        page = 0
        should_continue = True
        
        while should_continue and page < max_pages:
            try:
                # 搜索推文
                response = self.search_tweets(actual_handle, next_cursor)
                
                # 检查响应是否包含tweets数据
                if 'tweets' not in response:
                    error_message = response.get('message', response.get('error', 'API响应中没有tweets字段'))
                    error_code = response.get('error_code', response.get('code', 'N/A'))
                    self.logger.error(f"API响应异常: {error_message} (错误码: {error_code})")
                    self.logger.error(f"完整响应: {response}")
                    break
                
                # 获取推文数据
                tweets = response.get('tweets', [])
                next_cursor_from_response = response.get('next_cursor', "")
                
                if not tweets:
                    self.logger.info("没有找到更多推文，结束爬取")
                    break
                
                self.logger.info(f"第 {page + 1} 页: 获取到 {len(tweets)} 条推文")
                
                # 过滤推文（只保留指定作者自己发布的原创推文和转发推文）
                filtered_tweets = self._filter_tweets_by_author_and_retweets(tweets, actual_handle, actual_start_time, actual_end_time)
                self.logger.info(f"过滤后保留 {len(filtered_tweets)} 条推文")
                
                if not filtered_tweets:
                    self.logger.info("过滤后没有符合条件的推文")
                    # 检查是否还有下一页
                    if not next_cursor_from_response:
                        break
                    next_cursor = next_cursor_from_response
                    page += 1
                    continue
                
                # 检查时间范围条件 - 修改逻辑：只有当所有推文都晚于结束时间才停止
                earliest_tweet_time = None
                latest_tweet_time = None
                has_tweets_in_range = False  # 添加标记，检查本页是否有目标时间范围内的推文
                
                for tweet in tweets:  # 检查所有推文而不只是过滤后的
                    tweet_time = self._parse_tweet_time(tweet.get('created_at', ''))
                    if tweet_time:
                        # 确保tweet_time是datetime对象且有时区信息
                        if tweet_time.tzinfo is None:
                            tweet_time = tweet_time.replace(tzinfo=timezone.utc)
                        
                        if earliest_tweet_time is None or tweet_time < earliest_tweet_time:
                            earliest_tweet_time = tweet_time
                        if latest_tweet_time is None or tweet_time > latest_tweet_time:
                            latest_tweet_time = tweet_time
                        
                        # 检查是否有推文在目标时间范围内
                        if actual_start_time <= tweet_time <= actual_end_time:
                            has_tweets_in_range = True
                
                # 确保actual_start_time和actual_end_time是datetime对象
                if isinstance(actual_start_time, str):
                    try:
                        if actual_start_time.endswith('Z'):
                            actual_start_time = datetime.fromisoformat(actual_start_time[:-1]).replace(tzinfo=timezone.utc)
                        else:
                            actual_start_time = datetime.fromisoformat(actual_start_time).replace(tzinfo=timezone.utc)
                    except:
                        self.logger.warning(f"无法解析actual_start_time: {actual_start_time}")
                        continue
                elif actual_start_time.tzinfo is None:
                    actual_start_time = actual_start_time.replace(tzinfo=timezone.utc)
                
                if isinstance(actual_end_time, str):
                    try:
                        if actual_end_time.endswith('Z'):
                            actual_end_time = datetime.fromisoformat(actual_end_time[:-1]).replace(tzinfo=timezone.utc)
                        else:
                            actual_end_time = datetime.fromisoformat(actual_end_time).replace(tzinfo=timezone.utc)
                    except:
                        self.logger.warning(f"无法解析actual_end_time: {actual_end_time}")
                        continue
                elif actual_end_time.tzinfo is None:
                    actual_end_time = actual_end_time.replace(tzinfo=timezone.utc)
                
                # 正确的停止条件：当本页最早的推文都早于开始时间时停止
                # 因为推文是按时间倒序排列的，earliest_tweet_time是本页最早的推文时间
                if earliest_tweet_time and earliest_tweet_time < actual_start_time:
                    self.logger.info(f"本页最早推文时间 {earliest_tweet_time} 早于开始时间 {actual_start_time}，已超出目标时间范围，停止分页")
                    should_continue = False
                
                # 如果本页有目标时间范围内的推文，记录日志
                if has_tweets_in_range:
                    self.logger.info(f"本页发现目标时间范围内的推文，时间范围：{earliest_tweet_time} ~ {latest_tweet_time}")
                else:
                    self.logger.info(f"本页暂无目标时间范围内推文，时间范围：{earliest_tweet_time} ~ {latest_tweet_time}，继续下一页")
                    
                    # 如果本页所有推文都早于开始时间，且时间跨度过大，可能是数据异常
                    if earliest_tweet_time and earliest_tweet_time < actual_start_time:
                        time_diff = actual_start_time - earliest_tweet_time
                        if time_diff.days > 30:  # 如果时间差超过30天，可能遗漏了目标数据
                            self.logger.warning(f"检测到时间跳跃过大：最早推文时间 {earliest_tweet_time}，目标开始时间 {actual_start_time}，时间差 {time_diff.days} 天")
                            self.logger.warning(f"可能在目标时间范围内没有推文数据，或API分页存在跳跃")
                
                # 转换为Tweet对象
                tweet_objects = []
                for tweet_data in filtered_tweets:
                    user_id = tweet_data.get('user', {}).get('id_str', '')
                    tweet_obj = self._convert_to_tweet_object(tweet_data, user_id)
                    tweet_objects.append(tweet_obj)
                
                # 保存到数据库
                saved_count = self._save_to_database(tweet_objects)
                total_saved += saved_count
                self.logger.info(f"本页保存成功: {saved_count} 条推文")
                
                # 获取下一页游标
                next_cursor = next_cursor_from_response
                if not next_cursor:
                    self.logger.info("没有更多分页，结束爬取")
                    break
                
                page += 1
                
            except Exception as e:
                self.logger.error(f"第 {page + 1} 页爬取失败: {e}")
                break
        
        self.logger.info(f"爬取完成: 总共保存 {total_saved} 条推文")
        return total_saved
    
    def crawl_multiple_handles(self) -> Dict[str, int]:
        """
        爬取配置文件中所有启用的handle
        
        Returns:
            每个handle的保存成功数量
        """
        targets = self.config.get('back_test', {}).get('targets', [])
        enabled_targets = [target for target in targets if target.get('enabled', False)]
        
        if not enabled_targets:
            self.logger.warning("没有找到启用的目标handle")
            return {}
        
        concurrent_config = self.config.get('back_test', {}).get('concurrent', {})
        concurrent_enabled = concurrent_config.get('enabled', True)
        max_workers = concurrent_config.get('max_workers', 3)
        
        results = {}
        
        if concurrent_enabled and len(enabled_targets) > 1:
            # 并发执行
            self.logger.info(f"开始并发爬取 {len(enabled_targets)} 个目标，最大并发数: {max_workers}")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交任务
                future_to_target = {}
                for target in enabled_targets:
                    handle = target.get('handle')
                    start_time, end_time = self._parse_target_time_range(target)
                    
                    future = executor.submit(
                        self.crawl_tweets_for_handle,
                        handle=handle,
                        max_pages=None,
                        start_time=start_time,
                        end_time=end_time
                    )
                    future_to_target[future] = target
                
                # 收集结果
                for future in as_completed(future_to_target):
                    target = future_to_target[future]
                    handle = target.get('handle')
                    try:
                        saved_count = future.result()
                        results[handle] = saved_count
                        self.logger.info(f"用户 {handle} 爬取完成: {saved_count} 条推文")
                    except Exception as e:
                        self.logger.error(f"用户 {handle} 爬取失败: {e}")
                        results[handle] = 0
        else:
            # 顺序执行
            self.logger.info(f"开始顺序爬取 {len(enabled_targets)} 个目标")
            
            for target in enabled_targets:
                handle = target.get('handle')
                start_time, end_time = self._parse_target_time_range(target)
                
                try:
                    saved_count = self.crawl_tweets_for_handle(
                        handle=handle,
                        max_pages=None,
                        start_time=start_time,
                        end_time=end_time
                    )
                    results[handle] = saved_count
                    self.logger.info(f"用户 {handle} 爬取完成: {saved_count} 条推文")
                except Exception as e:
                    self.logger.error(f"用户 {handle} 爬取失败: {e}")
                    results[handle] = 0
        
        return results
    
    def _parse_target_time_range(self, target: Dict[str, Any]) -> tuple[datetime, datetime]:
        """
        解析目标配置中的时间范围
        
        Args:
            target: 目标配置字典
            
        Returns:
            (开始时间, 结束时间) 的datetime对象元组
        """
        start_time = None
        end_time = None
        
        # 从目标配置中获取时间范围
        start_time_str = target.get('start_time')
        end_time_str = target.get('end_time')
        
        if start_time_str:
            try:
                if start_time_str.endswith('Z'):
                    start_time = datetime.fromisoformat(start_time_str[:-1]).replace(tzinfo=timezone.utc)
                else:
                    start_time = datetime.fromisoformat(start_time_str).replace(tzinfo=timezone.utc)
            except ValueError as e:
                self.logger.warning(f"解析目标开始时间失败: {start_time_str}, 错误: {e}")
        
        if end_time_str:
            try:
                if end_time_str.endswith('Z'):
                    end_time = datetime.fromisoformat(end_time_str[:-1]).replace(tzinfo=timezone.utc)
                else:
                    end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=timezone.utc)
            except ValueError as e:
                self.logger.warning(f"解析目标结束时间失败: {end_time_str}, 错误: {e}")
        
        # 如果解析失败，使用默认配置
        if not start_time or not end_time:
            default_config = self.config.get('back_test', {}).get('default_config', {})
            
            if not start_time:
                default_start = default_config.get('start_time', '2025-11-07T16:18:00Z')
                try:
                    if default_start.endswith('Z'):
                        start_time = datetime.fromisoformat(default_start[:-1]).replace(tzinfo=timezone.utc)
                    else:
                        start_time = datetime.fromisoformat(default_start).replace(tzinfo=timezone.utc)
                except ValueError:
                    start_time = datetime(2025, 11, 7, 16, 18, tzinfo=timezone.utc)
            
            if not end_time:
                default_end = default_config.get('end_time', '2025-11-08T16:18:00Z')
                try:
                    if default_end.endswith('Z'):
                        end_time = datetime.fromisoformat(default_end[:-1]).replace(tzinfo=timezone.utc)
                    else:
                        end_time = datetime.fromisoformat(default_end).replace(tzinfo=timezone.utc)
                except ValueError:
                    end_time = datetime(2025, 11, 8, 16, 18, tzinfo=timezone.utc)
        
        # 确保时间范围合理
        if start_time >= end_time:
            self.logger.warning(f"目标 {target.get('handle')} 的开始时间晚于结束时间，调整为24小时范围")
            end_time = start_time + timedelta(hours=24)
        
        return start_time, end_time


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='推特历史数据回测爬虫')
    parser.add_argument('--handle', '-u', help='Twitter用户名(screen_name)，覆盖配置文件设置')
    parser.add_argument('--max-pages', '-p', type=int, help='最大分页数（仅作保护机制，正常情况下基于时间自动停止）')
    parser.add_argument('--start-time', '-s', help='开始时间 (ISO格式，如 "2025-11-07T16:18:00Z")，覆盖配置文件设置')
    parser.add_argument('--end-time', '-e', help='结束时间 (ISO格式，如 "2025-11-08T16:18:00Z")，覆盖配置文件设置')
    parser.add_argument('--config', '-c', default='config/config.json', help='配置文件路径')
    parser.add_argument('--batch', '-b', action='store_true', help='批量模式：爬取配置文件中所有启用的handle')
    
    args = parser.parse_args()
    
    try:
        crawler = BackTestTweetCrawler(
            config_path=args.config, 
            start_time=args.start_time,
            end_time=args.end_time,
            target_handle=args.handle
        )
        
        if args.batch:
            # 批量模式
            results = crawler.crawl_multiple_handles()
            total_saved = sum(results.values())
            print(f"批量爬取完成:")
            for handle, count in results.items():
                print(f"  {handle}: {count} 条推文")
            print(f"总计: {total_saved} 条推文")
        else:
            # 单个handle模式
            saved_count = crawler.crawl_tweets_for_handle(
                handle=args.handle, 
                max_pages=args.max_pages,
                start_time=args.start_time,
                end_time=args.end_time
            )
            print(f"成功保存 {saved_count} 条推文到数据库")
            
    except Exception as e:
        print(f"爬虫执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()