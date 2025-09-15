"""
Twitter用户数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from dateutil import parser


@dataclass
class TwitterUser:
    """Twitter用户数据模型"""
    
    # 必填字段
    id_str: str
    
    # 可选字段
    screen_name: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    avatar: Optional[str] = None
    created_at: Optional[str] = None
    created_at_datetime: Optional[datetime] = None
    followers_count: Optional[int] = 0
    friends_count: Optional[int] = 0
    statuses_count: Optional[int] = 0
    can_dm: Optional[bool] = False
    language: Optional[str] = None  # 用户主要语言: "English" 或 "Chinese"
    update_time: Optional[datetime] = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """初始化后处理"""
        # 解析创建时间
        if self.created_at and not self.created_at_datetime:
            self.created_at_datetime = self._parse_datetime(self.created_at)
    
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
            print(f"解析用户创建时间失败: {date_str}, 错误: {e}")
            return None
    
    @classmethod
    def from_api_data(cls, api_data: Dict[str, Any], field_mapping: Dict[str, str]) -> 'TwitterUser':
        """
        从API数据创建TwitterUser对象
        
        Args:
            api_data: API返回的原始数据
            field_mapping: 字段映射配置
            
        Returns:
            TwitterUser对象
        """
        # 根据字段映射提取数据
        mapped_data = {}
        for api_field, db_field in field_mapping.items():
            if api_field in api_data:
                mapped_data[db_field] = api_data[api_field]
        
        # 创建TwitterUser对象
        return cls(**mapped_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，用于数据库插入
        
        Returns:
            字典格式的数据
        """
        return {
            'id_str': self.id_str,
            'screen_name': self.screen_name,
            'name': self.name,
            'description': self.description,
            'avatar': self.avatar,
            'created_at': self.created_at,
            'created_at_datetime': self.created_at_datetime,
            'followers_count': self.followers_count,
            'friends_count': self.friends_count,
            'statuses_count': self.statuses_count,
            'can_dm': self.can_dm,
            'language': getattr(self, 'language', None),  # 安全地获取language字段
            'update_time': self.update_time or datetime.now()
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
            self.followers_count, self.friends_count, self.statuses_count
        ]
        
        for value in numeric_fields:
            if value is not None and value < 0:
                return False
        
        return True
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"TwitterUser(id={self.id_str}, screen_name={self.screen_name}, name={self.name})" 