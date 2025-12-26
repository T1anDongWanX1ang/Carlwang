"""
Twitter API 客户端（官方 Twitter API 列表推文接口适配版）
适配 https://docs.twitterapi.io/api-reference/endpoint/get_list_tweet
"""
import requests
import time
import logging
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime, timedelta
from dateutil import parser as date_parser

from ..utils.config_manager import config


class TwitterAPITwitterAPIClient:
    """Twitter API v2 风格的列表推文客户端"""

    def __init__(self):
        self.api_config = config.get('api_twitterapi', config.get_api_config())
        self.base_url = self.api_config.get('base_url', '')
        self.headers = self.api_config.get('headers', {})
        self.default_params = self.api_config.get('default_params', {})
        self.pagination_config = self.api_config.get('pagination', {})
        self.timeout = self.api_config.get('timeout', 30)
        self.retry_attempts = self.api_config.get('retry_attempts', 3)
        self.retry_delay = self.api_config.get('retry_delay', 5)

        self.session = requests.Session()
        # 默认沿用配置 headers；兼容新接口要求的 X-API-Key，保留旧 Authorization/Bearer 形式以便切换。
        # 如需使用新 key，请在 config 的 api_twitterapi.headers 中设置 "X-API-Key": "<new_key>"。
        self.session.headers.update(self.headers)

        self.logger = logging.getLogger(__name__)

        # 请求统计
        self.request_count = 0
        self.error_count = 0
        self.last_request_time = 0
        self.tweets_fetched = 0  # 累计获取的推文数

        # 成本追踪 (基于 TwitterAPI.io 定价: $0.15 per 1,000 tweets)
        self.total_cost = 0.0  # 累计成本（美元）
        self.cost_per_1000_tweets = 0.15  # 每1000条推文的成本

    def _make_request(self, url: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """发起 HTTP 请求，带重试"""
        if params is None:
            params = {}

        final_params = {**self.default_params, **params}

        for attempt in range(self.retry_attempts):
            try:
                # 基础限频：两次请求至少间隔 1 秒
                now = time.time()
                if self.last_request_time and now - self.last_request_time < 1:
                    time.sleep(1 - (now - self.last_request_time))

                self.logger.info(f"发起 TwitterAPI 请求 (尝试 {attempt + 1}/{self.retry_attempts}): {url}")
                self.logger.debug(f"请求参数: {final_params}")

                resp = self.session.get(url, params=final_params, timeout=self.timeout)
                self.last_request_time = time.time()
                self.request_count += 1

                # 记录请求详情
                self.logger.info(f"[API调用] 请求 #{self.request_count} | URL: {url} | 状态码: {resp.status_code}")

                if resp.status_code == 200:
                    response_data = resp.json()
                    # 调试：打印完整响应（已注释以减少日志噪音）
                    # self.logger.debug(f"完整API响应: {response_data}")
                    return response_data
                if resp.status_code == 429:
                    self.logger.warning(f"触发速率限制 429，等待 {self.retry_delay} 秒后重试")
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                if resp.status_code in [500, 502, 503, 504]:
                    self.logger.warning(f"服务器错误 {resp.status_code}，等待 {self.retry_delay} 秒后重试")
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue

                self.logger.error(f"请求失败 {resp.status_code}: {resp.text}")
                self.error_count += 1
                return None

            except requests.exceptions.Timeout:
                self.logger.warning(f"请求超时，重试 {attempt + 1}/{self.retry_attempts}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                self.error_count += 1
                return None
            except requests.exceptions.RequestException as e:
                self.logger.error(f"请求异常: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                self.error_count += 1
                return None
            except Exception as e:
                self.logger.error(f"未知错误: {e}")
                self.error_count += 1
                return None

        return None

    def _convert_twitterapi_format(self, tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将TwitterAPI的响应格式转换为系统期望的格式

        Args:
            tweet_data: TwitterAPI返回的原始推文数据

        Returns:
            转换后的推文数据
        """
        try:
            # 临时调试：打印原始推文的所有字段名（只打印一次）
            if not hasattr(self, '_debug_printed'):
                self._debug_printed = True
                self.logger.info(f"=== TwitterAPI 原始响应字段 ===")
                self.logger.info(f"所有字段: {list(tweet_data.keys())}")
                retweet_related = [k for k in tweet_data.keys() if 'retweet' in k.lower() or 'quote' in k.lower()]
                if retweet_related:
                    self.logger.info(f"转发/引用相关字段: {retweet_related}")
                    for key in retweet_related:
                        value = tweet_data[key]
                        if isinstance(value, dict):
                            self.logger.info(f"  {key}: {{...}} (字典，有 {len(value)} 个字段)")
                        elif isinstance(value, bool):
                            self.logger.info(f"  {key}: {value} (布尔)")
                        elif value is None:
                            self.logger.info(f"  {key}: None")
                        else:
                            self.logger.info(f"  {key}: {type(value).__name__} = {str(value)[:100]}")
                else:
                    self.logger.info(f"未找到转发/引用相关字段")
                self.logger.info(f"=== 调试信息结束 ===")

            converted = {}

            # 基础字段映射
            field_mapping = {
                'id': 'id_str',
                'text': 'full_text',
                'createdAt': 'created_at',
                'likeCount': 'favorite_count',
                'retweetCount': 'retweet_count',
                'replyCount': 'reply_count',
                'quoteCount': 'quote_count',
                'bookmarkCount': 'bookmark_count',
                'viewCount': 'view_count',
                'conversationId': 'conversation_id_str',
                'inReplyToId': 'in_reply_to_status_id_str',
                'url': 'tweet_url',
            }

            # 执行字段映射
            for api_field, db_field in field_mapping.items():
                if api_field in tweet_data:
                    converted[db_field] = tweet_data[api_field]

            # 处理布尔字段
            converted['is_quote_status'] = tweet_data.get('isQuote', False)

            # 判断是否为转发推文
            if 'retweeted_tweet' in tweet_data and tweet_data['retweeted_tweet']:
                converted['is_retweet'] = True
            else:
                converted['is_retweet'] = False

            # 处理author信息（用于后续的用户数据提取）
            if 'author' in tweet_data and isinstance(tweet_data['author'], dict):
                author = tweet_data['author']

                # 提取kol_id
                if 'id' in author:
                    converted['kol_id'] = str(author['id'])

                # 保留原始author数据供后续处理
                converted['author'] = {
                    'id_str': str(author.get('id', '')),
                    'screen_name': author.get('userName', ''),
                    'name': author.get('name', ''),
                    'description': author.get('description', '') or author.get('profile_bio', {}).get('description', ''),
                    'avatar': author.get('profilePicture', ''),
                    'created_at': author.get('createdAt', ''),
                    'followers_count': author.get('followers', 0),
                    'friends_count': author.get('following', 0),
                    'statuses_count': author.get('statusesCount', 0),
                }

            # 处理entities字段（提取链接）
            if 'entities' in tweet_data:
                entities = tweet_data['entities']

                # 提取URLs
                if isinstance(entities, dict) and 'urls' in entities:
                    urls = entities.get('urls', [])
                    if urls and isinstance(urls, list) and len(urls) > 0:
                        first_url = urls[0]
                        if isinstance(first_url, dict):
                            converted['link_url'] = first_url.get('expanded_url') or first_url.get('url', '')

            # 处理extendedEntities（媒体链接）
            if 'extendedEntities' in tweet_data and not converted.get('link_url'):
                ext_entities = tweet_data['extendedEntities']
                if isinstance(ext_entities, dict) and 'media' in ext_entities:
                    media_list = ext_entities.get('media', [])
                    if media_list and isinstance(media_list, list) and len(media_list) > 0:
                        first_media = media_list[0]
                        if isinstance(first_media, dict):
                            converted['link_url'] = first_media.get('expanded_url') or first_media.get('url', '')

            return converted

        except Exception as e:
            self.logger.error(f"转换TwitterAPI格式失败: {e}, 原始数据: {tweet_data}")
            return tweet_data

    def _calculate_request_cost(self, tweet_count: int) -> float:
        """
        计算单次请求的成本（美元）

        TwitterAPI.io 计费规则:
        - $0.15 per 1,000 tweets
        - 最低收费: 15 credits (0或1条推文)
        - 示例: 4条=60 credits, 2条=30 credits

        Args:
            tweet_count: 返回的推文数量

        Returns:
            成本（美元）
        """
        if tweet_count <= 0:
            # 0条推文，最低收费 15 credits
            return 0.15 * 15 / 1000
        elif tweet_count == 1:
            # 1条推文，最低收费 15 credits
            return 0.15 * 15 / 1000
        else:
            # 2条及以上，按实际推文数计费
            return (tweet_count / 1000) * self.cost_per_1000_tweets

    def _build_url(self, list_id: str = None) -> str:
        """构建请求 URL

        Args:
            list_id: 可选的 list_id，如果 endpoint 包含 {list_id} 占位符则替换

        Returns:
            完整的请求 URL
        """
        base_url = self.base_url.rstrip('/')
        endpoint_tpl = self.api_config.get('endpoints', {}).get('list_tweets', '/twitter/list/tweets')

        # 如果 endpoint 包含 {list_id} 占位符且提供了 list_id，则替换
        if list_id and '{list_id}' in endpoint_tpl:
            endpoint = endpoint_tpl.format(list_id=list_id).lstrip('/')
        else:
            endpoint = endpoint_tpl.lstrip('/')

        return f"{base_url}/{endpoint}"

    def fetch_tweets(self, list_id: Optional[str] = None, **kwargs) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """获取单页推文，返回 (tweets, next_token)"""
        target_list_id = list_id or self.default_params.get('list_id')
        if not target_list_id:
            self.logger.error("缺少 list_id，无法请求 TwitterAPI")
            return [], None

        # 检查 endpoint 是否使用路径参数还是查询参数
        endpoint_tpl = self.api_config.get('endpoints', {}).get('list_tweets', '/twitter/list/tweets')

        if '{list_id}' in endpoint_tpl:
            # 旧格式：/lists/{list_id}/tweets - list_id 在 URL 路径中
            url = self._build_url(target_list_id)
        else:
            # 新格式：/twitter/list/tweets - list_id 作为查询参数
            url = self._build_url()

        pagination_token = kwargs.pop('pagination_token', None)
        # 兼容旧的 cursor 参数
        pagination_token = kwargs.pop('cursor', pagination_token)

        max_results = kwargs.pop('max_results', None)
        if max_results is None:
            max_results = kwargs.pop('count', None)

        params: Dict[str, Any] = {}

        # 如果不是路径参数，则作为查询参数传递
        if '{list_id}' not in endpoint_tpl:
            params['listId'] = target_list_id  # 使用驼峰命名 listId

        if max_results:
            params['max_results'] = max_results
        if pagination_token:
            params['pagination_token'] = pagination_token

        params.update(kwargs)

        data = self._make_request(url, params)
        if not data:
            return [], None

        tweets = []
        next_token = None

        if isinstance(data, dict):
            # 适配不同的 API 响应格式
            # twitterapi.io 返回 'tweets' 字段
            # 其他 API 可能返回 'data' 字段
            tweets = data.get('tweets', data.get('data', []))
            if not isinstance(tweets, list):
                tweets = []

            # 转换TwitterAPI格式为系统期望格式
            if tweets:
                converted_tweets = []
                for tweet in tweets:
                    converted_tweet = self._convert_twitterapi_format(tweet)
                    converted_tweets.append(converted_tweet)
                tweets = converted_tweets
                self.logger.debug(f"已转换 {len(tweets)} 条推文格式")

            # 获取分页信息
            meta = data.get('meta', {}) if isinstance(data.get('meta'), dict) else {}
            next_token = meta.get('next_token') or data.get('next_cursor')  # 适配两种格式

            # 计算并记录成本
            request_cost = self._calculate_request_cost(len(tweets))
            self.total_cost += request_cost

            if tweets:
                self.tweets_fetched += len(tweets)
                self.logger.info(
                    f"获取 {len(tweets)} 条推文 (累计: {self.tweets_fetched}) | "
                    f"本次成本: ${request_cost:.6f} | 累计成本: ${self.total_cost:.6f}" +
                    (f" | next_token={next_token}" if next_token else " | 无更多数据")
                )
            else:
                self.logger.info(
                    f"响应成功但 tweets 为空 | "
                    f"本次成本: ${request_cost:.6f} | 累计成本: ${self.total_cost:.6f}"
                )

        return tweets, next_token

    def fetch_tweets_with_pagination(self, list_id: Optional[str] = None,
                                     max_pages: Optional[int] = None,
                                     page_size: Optional[int] = None,
                                     hours_limit: int = 2) -> Generator[List[Dict[str, Any]], None, None]:
        """分页获取推文，兼容时间过滤"""
        if max_pages is None:
            max_pages = 15
        else:
            max_pages = min(max_pages, 15)

        if page_size is None:
            page_size = self.pagination_config.get('page_size', 100)
        page_size = min(page_size or 100, 100)  # 官方接口上限 100

        time_cutoff = datetime.now() - timedelta(hours=hours_limit)
        self.logger.info(f"时间过滤: 仅保留 {time_cutoff.strftime('%Y-%m-%d %H:%M:%S')} 之后的推文")

        page = 1
        total_tweets = 0
        filtered_tweets = 0
        pagination_token = None

        while page <= max_pages:
            self.logger.info(f"获取第 {page} 页 (最多 {max_pages} 页)" + (f", pagination_token={pagination_token}" if pagination_token else ""))

            params = {'max_results': page_size}
            if pagination_token:
                params['pagination_token'] = pagination_token

            tweets, next_token = self.fetch_tweets(list_id=list_id, **params)
            if not tweets:
                self.logger.info(f"第 {page} 页无数据，停止")
                break

            # 智能时间过滤：检查最后一条推文时间，如果已超时间窗口则停止
            valid_tweets = []
            last_tweet_time = None

            for tw in tweets:
                try:
                    created_at_str = tw.get('created_at', '')
                    if created_at_str:
                        t = date_parser.parse(created_at_str)
                        if t.tzinfo:
                            t = t.astimezone().replace(tzinfo=None)

                        # 记录最后一条推文的时间
                        last_tweet_time = t

                        if t >= time_cutoff:
                            valid_tweets.append(tw)
                        else:
                            filtered_tweets += 1
                    else:
                        valid_tweets.append(tw)
                except Exception as e:
                    self.logger.warning(f"解析时间失败，保留该推文: {e}")
                    valid_tweets.append(tw)

            total_tweets += len(valid_tweets)
            self.logger.info(f"第 {page} 页过滤后 {len(valid_tweets)} 条，累计 {total_tweets} 条有效")

            # 智能早停：如果最后一条推文已经超出时间窗口，后续页肯定更老，直接停止
            if last_tweet_time and last_tweet_time < time_cutoff:
                self.logger.info(
                    f"⏱️ 智能早停触发：第 {page} 页最后一条推文时间 {last_tweet_time.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"已超出时间窗口 ({time_cutoff.strftime('%Y-%m-%d %H:%M:%S')}之后)，停止翻页以节省API成本"
                )
                # 如果这页有有效推文，先返回
                if valid_tweets:
                    yield valid_tweets
                break

            if valid_tweets:
                yield valid_tweets

            if not next_token:
                self.logger.info("无 next_token，分页结束")
                break

            pagination_token = next_token
            page += 1
            time.sleep(1)

        if page > max_pages:
            self.logger.warning(f"达到最大页数限制 {max_pages}，可能还有剩余数据")

        self.logger.info(f"分页结束，总有效 {total_tweets} 条，过滤 {filtered_tweets} 条")

    def fetch_all_tweets(self, list_id: Optional[str] = None,
                         max_pages: Optional[int] = None,
                         page_size: Optional[int] = None,
                         hours_limit: int = 2) -> List[Dict[str, Any]]:
        """拉取所有页（带时间过滤）"""
        all_tweets: List[Dict[str, Any]] = []
        try:
            for page_tweets in self.fetch_tweets_with_pagination(
                list_id=list_id,
                max_pages=max_pages,
                page_size=page_size,
                hours_limit=hours_limit
            ):
                all_tweets.extend(page_tweets)
        except Exception as e:
            self.logger.error(f"获取推文时出错: {e}")
        return all_tweets

    def get_request_stats(self) -> Dict[str, float]:
        """获取请求统计信息（包含成本）"""
        return {
            'total_requests': self.request_count,
            'tweets_fetched': self.tweets_fetched,
            'error_count': self.error_count,
            'success_rate': (self.request_count - self.error_count) / max(self.request_count, 1) * 100,
            'avg_tweets_per_request': self.tweets_fetched / max(self.request_count - self.error_count, 1),
            'total_cost_usd': self.total_cost,  # 总成本（美元）
            'avg_cost_per_request': self.total_cost / max(self.request_count - self.error_count, 1),  # 平均每次请求成本
        }

    def reset_stats(self):
        """重置统计信息"""
        self.request_count = 0
        self.error_count = 0
        self.tweets_fetched = 0
        self.total_cost = 0.0

    def close(self):
        if self.session:
            self.session.close()


# 导出单例，接口与原 twitter_api 保持一致
twitter_api = TwitterAPITwitterAPIClient()
