"""
数据映射和转换工具
"""
from typing import List, Dict, Any, Optional
import logging

from .config_manager import config
from ..models.tweet import Tweet
from ..models.user import TwitterUser


class DataMapper:
    """数据映射器"""
    
    def __init__(self):
        """初始化数据映射器"""
        self.field_mapping = config.get_field_mapping()
        # 为了向后兼容，如果field_mapping不是嵌套结构，则包装为tweet映射
        if self.field_mapping and 'tweet' not in self.field_mapping and 'user' not in self.field_mapping:
            self.field_mapping = {'tweet': self.field_mapping, 'user': {}}
        self.logger = logging.getLogger(__name__)
    
    def map_api_data_to_tweet(self, api_data: Dict[str, Any]) -> Optional[Tweet]:
        """
        将API数据映射为Tweet对象
        
        Args:
            api_data: API返回的原始数据
            
        Returns:
            Tweet对象或None
        """
        try:
            # 检查必填字段
            if 'id_str' not in api_data:
                self.logger.warning(f"API数据缺少必填字段 id_str: {api_data}")
                return None
            
            # 使用Tweet类的from_api_data方法
            tweet_mapping = self.field_mapping.get('tweet', {})
            tweet = Tweet.from_api_data(api_data, tweet_mapping)
            
            # 验证数据有效性
            if not tweet.validate():
                self.logger.warning(f"Tweet数据验证失败: {tweet}")
                return None
            
            return tweet
            
        except Exception as e:
            self.logger.error(f"映射API数据到Tweet失败: {e}, 数据: {api_data}")
            return None
    
    def map_api_data_list_to_tweets(self, api_data_list: List[Dict[str, Any]]) -> List[Tweet]:
        """
        将API数据列表映射为Tweet对象列表
        
        Args:
            api_data_list: API返回的数据列表
            
        Returns:
            Tweet对象列表
        """
        tweets = []
        failed_count = 0
        
        for api_data in api_data_list:
            tweet = self.map_api_data_to_tweet(api_data)
            if tweet:
                tweets.append(tweet)
            else:
                failed_count += 1
        
        if failed_count > 0:
            self.logger.warning(f"映射过程中失败 {failed_count} 条数据")
        
        self.logger.info(f"成功映射 {len(tweets)} 条推文数据")
        return tweets
    
    def map_api_data_to_user(self, api_data: Dict[str, Any]) -> Optional[TwitterUser]:
        """
        将API用户数据映射为TwitterUser对象
        
        Args:
            api_data: API返回的用户原始数据
            
        Returns:
            TwitterUser对象或None
        """
        try:
            # 检查必填字段
            if 'id_str' not in api_data:
                self.logger.warning(f"API用户数据缺少必填字段 id_str: {api_data}")
                return None
            
            # 使用TwitterUser类的from_api_data方法
            user_mapping = self.field_mapping.get('user', {})
            user = TwitterUser.from_api_data(api_data, user_mapping)
            
            # 验证数据有效性
            if not user.validate():
                self.logger.warning(f"TwitterUser数据验证失败: {user}")
                return None
            
            return user
            
        except Exception as e:
            self.logger.error(f"映射API用户数据到TwitterUser失败: {e}, 数据: {api_data}")
            return None
    
    def map_api_data_list_to_users(self, api_data_list: List[Dict[str, Any]]) -> List[TwitterUser]:
        """
        将API用户数据列表映射为TwitterUser对象列表
        
        Args:
            api_data_list: API返回的用户数据列表
            
        Returns:
            TwitterUser对象列表
        """
        users = []
        failed_count = 0
        
        for api_data in api_data_list:
            user = self.map_api_data_to_user(api_data)
            if user:
                users.append(user)
            else:
                failed_count += 1
        
        if failed_count > 0:
            self.logger.warning(f"用户映射过程中失败 {failed_count} 条数据")
        
        self.logger.info(f"成功映射 {len(users)} 条用户数据")
        return users
    
    def extract_users_from_tweets(self, tweets_api_data: List[Dict[str, Any]]) -> List[TwitterUser]:
        """
        从推文API数据中提取用户信息

        Args:
            tweets_api_data: 包含用户信息的推文API数据列表

        Returns:
            用户对象列表
        """
        users = []
        user_ids_seen = set()

        for tweet_data in tweets_api_data:
            # 检查是否包含用户信息（兼容 'user' 和 'author' 两种字段）
            user_data = None
            if 'user' in tweet_data and isinstance(tweet_data['user'], dict):
                user_data = tweet_data['user']
            elif 'author' in tweet_data and isinstance(tweet_data['author'], dict):
                user_data = tweet_data['author']

            if user_data:
                # 避免重复用户
                user_id = user_data.get('id_str')
                if user_id and user_id not in user_ids_seen:
                    user = self.map_api_data_to_user(user_data)
                    if user:
                        users.append(user)
                        user_ids_seen.add(user_id)

        self.logger.info(f"从 {len(tweets_api_data)} 条推文中提取到 {len(users)} 个唯一用户")
        return users
    
    def extract_mapped_fields(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据字段映射配置提取API数据中的字段
        
        Args:
            api_data: API原始数据
            
        Returns:
            映射后的字段数据
        """
        mapped_data = {}
        
        for api_field, db_field in field_mapping.items():
            if api_field in api_data:
                value = api_data[api_field]
                
                # 数据类型转换和清理
                cleaned_value = self._clean_field_value(api_field, value)
                mapped_data[db_field] = cleaned_value
            else:
                # 处理缺失字段的默认值
                default_value = self._get_default_value(db_field)
                if default_value is not None:
                    mapped_data[db_field] = default_value
        
        return mapped_data
    
    def _clean_field_value(self, field_name: str, value: Any) -> Any:
        """
        清理和转换字段值
        
        Args:
            field_name: 字段名
            value: 原始值
            
        Returns:
            清理后的值
        """
        if value is None:
            return None
        
        # 字符串字段处理
        if field_name in ['id_str', 'conversation_id_str', 'in_reply_to_status_id_str', 
                         'full_text', 'created_at']:
            if isinstance(value, str):
                return value.strip() if value.strip() else None
            else:
                return str(value) if value else None
        
        # 布尔字段处理
        elif field_name in ['is_quote_status', 'is_retweet']:
            if isinstance(value, bool):
                return value
            elif isinstance(value, str):
                return value.lower() in ['true', '1', 'yes']
            else:
                return bool(value)
        
        # 数值字段处理
        elif field_name in ['bookmark_count', 'favorite_count', 'quote_count', 
                           'reply_count', 'retweet_count', 'view_count']:
            try:
                if value is None or value == '':
                    return 0
                return int(value)
            except (ValueError, TypeError):
                self.logger.warning(f"无法转换数值字段 {field_name}: {value}")
                return 0
        
        # 默认返回原值
        return value
    
    def _get_default_value(self, db_field: str) -> Any:
        """
        获取数据库字段的默认值
        
        Args:
            db_field: 数据库字段名
            
        Returns:
            默认值
        """
        defaults = {
            'is_quote_status': False,
            'is_retweet': False,
            'bookmark_count': 0,
            'favorite_count': 0,
            'quote_count': 0,
            'reply_count': 0,
            'retweet_count': 0,
            'view_count': 0,
        }
        
        return defaults.get(db_field)
    
    def validate_api_data_structure(self, api_data: Dict[str, Any]) -> bool:
        """
        验证API数据结构是否符合预期
        
        Args:
            api_data: API数据
            
        Returns:
            是否符合预期结构
        """
        # 检查必填字段
        required_fields = ['id_str']
        for field in required_fields:
            if field not in api_data:
                self.logger.error(f"API数据缺少必填字段: {field}")
                return False
        
        # 检查字段类型
        type_checks = {
            'id_str': (str, int),  # 可以是字符串或数字
            'bookmark_count': (int, type(None)),
            'favorite_count': (int, type(None)),
            'quote_count': (int, type(None)),
            'reply_count': (int, type(None)),
            'retweet_count': (int, type(None)),
            'view_count': (int, type(None)),
            'is_quote_status': (bool, type(None)),
            'is_retweet': (bool, type(None)),
        }
        
        for field, expected_types in type_checks.items():
            if field in api_data:
                value = api_data[field]
                if value is not None and not isinstance(value, expected_types):
                    self.logger.warning(f"字段 {field} 类型不匹配，期望 {expected_types}，实际 {type(value)}")
        
        return True
    
    def get_field_mapping_info(self) -> Dict[str, Any]:
        """
        获取字段映射信息
        
        Returns:
            字段映射信息
        """
        return {
            'field_mapping': self.field_mapping,
            'mapped_field_count': len(self.field_mapping),
            'api_fields': list(self.field_mapping.keys()),
            'db_fields': list(self.field_mapping.values())
        }
    
    def update_field_mapping(self, new_mapping: Dict[str, str]) -> None:
        """
        更新字段映射配置
        
        Args:
            new_mapping: 新的字段映射配置
        """
        self.field_mapping.update(new_mapping)
        self.logger.info(f"字段映射已更新: {new_mapping}")


# 全局数据映射器实例
data_mapper = DataMapper() 