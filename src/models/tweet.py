"""
推文数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import re
from dateutil import parser


@dataclass
class Tweet:
    """推文数据模型"""
    
    # 必填字段
    id_str: str
    
    # 可选字段
    conversation_id_str: Optional[str] = None
    in_reply_to_status_id_str: Optional[str] = None
    full_text: Optional[str] = None
    is_quote_status: Optional[bool] = False
    created_at: Optional[str] = None
    created_at_datetime: Optional[datetime] = None
    bookmark_count: Optional[int] = 0
    favorite_count: Optional[int] = 0
    quote_count: Optional[int] = 0
    reply_count: Optional[int] = 0
    retweet_count: Optional[int] = 0
    view_count: Optional[int] = 0
    engagement_total: Optional[int] = None
    update_time: Optional[datetime] = field(default_factory=datetime.now)
    
    # 新增字段
    kol_id: Optional[str] = None  # KOL用户ID
    entity_id: Optional[str] = None  # 实体ID（如话题ID）- 保留兼容性
    project_id: Optional[str] = None  # 项目ID（project_xxx格式）
    topic_id: Optional[str] = None  # 话题ID（topic_xxx格式）
    is_valid: Optional[bool] = None  # 是否为有效的加密货币相关内容
    sentiment: Optional[str] = None  # 情绪倾向：Positive/Negative/Neutral
    tweet_url: Optional[str] = None  # 推文URL
    link_url: Optional[str] = None  # 提取的链接URL（来自entities字段）
    token_tag: Optional[str] = None  # Token符号标签（如BTC,ETH，多个用逗号分隔）
    project_tag: Optional[str] = None  # 项目标签（匹配RootData的项目名称）
    is_announce: Optional[int] = 0  # 是否为重要公告（0=否，1=是）
    
    def __post_init__(self):
        """初始化后处理"""
        # 解析创建时间
        if self.created_at and not self.created_at_datetime:
            self.created_at_datetime = self._parse_datetime(self.created_at)
        
        # 计算互动总量
        if self.engagement_total is None:
            self.engagement_total = self._calculate_engagement_total()
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """
        解析日期时间字符串
        
        Args:
            date_str: 日期时间字符串
            
        Returns:
            解析后的datetime对象
        """
        if not date_str:
            return None
            
        try:
            # 尝试多种日期格式
            formats = [
                '%a %b %d %H:%M:%S %z %Y',  # Twitter标准格式
                '%Y-%m-%dT%H:%M:%S.%fZ',     # ISO格式
                '%Y-%m-%d %H:%M:%S',         # 标准格式
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # 如果都失败了，尝试使用dateutil解析
            return parser.parse(date_str)
            
        except Exception as e:
            print(f"解析日期时间失败: {date_str}, 错误: {e}")
            return None
    
    def _calculate_engagement_total(self) -> int:
        """
        计算互动总量
        
        Returns:
            互动总量
        """
        counts = [
            self.bookmark_count or 0,
            self.favorite_count or 0,
            self.quote_count or 0,
            self.reply_count or 0,
            self.retweet_count or 0
        ]
        return sum(counts)
    
    @classmethod
    def from_api_data(cls, api_data: Dict[str, Any], field_mapping: Dict[str, str]) -> 'Tweet':
        """
        从API数据创建Tweet对象
        
        Args:
            api_data: API返回的原始数据
            field_mapping: 字段映射配置
            
        Returns:
            Tweet对象
        """
        # 根据字段映射提取数据
        mapped_data = {}
        for api_field, db_field in field_mapping.items():
            if api_field in api_data:
                mapped_data[db_field] = api_data[api_field]
        
        # 处理entities字段，提取链接URL
        link_url = cls._extract_link_from_entities(api_data.get('entities', []))
        if link_url:
            mapped_data['link_url'] = link_url
        
        # 创建Tweet对象
        return cls(**mapped_data)
    
    @staticmethod
    def _extract_link_from_entities(entities) -> Optional[str]:
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
            
            # 查找第一个type为photo的实体
            for entity in entities:
                if isinstance(entity, dict):
                    entity_type = entity.get('type')
                    if entity_type == 'photo':
                        # 提取link字段
                        link = entity.get('link')
                        if link and isinstance(link, str):
                            return link.strip()
            
            return None
            
        except Exception as e:
            # 静默处理异常，避免影响主流程
            print(f"提取entities链接失败: {e}")
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，用于数据库插入

        Returns:
            字典格式的数据
        """
        return {
            'id_str': self.id_str,
            'conversation_id_str': self.conversation_id_str,
            'in_reply_to_status_id_str': self.in_reply_to_status_id_str,
            'full_text': self.full_text,
            'is_quote_status': self.is_quote_status,
            'created_at': self.created_at,
            'created_at_datetime': self.created_at_datetime,
            'bookmark_count': self.bookmark_count,
            'favorite_count': self.favorite_count,
            'quote_count': self.quote_count,
            'reply_count': self.reply_count,
            'retweet_count': self.retweet_count,
            'view_count': self.view_count,
            'engagement_total': self.engagement_total,
            'update_time': self.update_time or datetime.now(),
            'kol_id': self.kol_id,
            'entity_id': self.entity_id,
            'project_id': self.project_id,
            'topic_id': self.topic_id,
            'is_valid': self.is_valid,
            'sentiment': self.sentiment,
            'tweet_url': self.tweet_url,
            'link_url': getattr(self, 'link_url', None),  # 安全地获取link_url字段
            'token_tag': self.token_tag,
            'project_tag': self.project_tag,
            'is_announce': self.is_announce
        }
    
    def validate(self) -> bool:
        """
        验证数据的有效性
        
        Returns:
            是否有效
        """
        # 必填字段检查
        if not self.id_str:
            return False
        
        # 数值字段检查
        numeric_fields = [
            self.bookmark_count, self.favorite_count, self.quote_count,
            self.reply_count, self.retweet_count, self.view_count
        ]
        
        for value in numeric_fields:
            if value is not None and value < 0:
                return False
        
        return True
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Tweet(id={self.id_str}, text={self.full_text[:50] if self.full_text else 'None'}...)" 