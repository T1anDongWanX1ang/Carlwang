"""
Marco数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import uuid


@dataclass
class MarcoData:
    """Marco数据模型"""
    
    # 必填字段
    id: str
    timestamp: datetime
    
    # 可选字段
    sentiment_index: Optional[float] = None
    summary: Optional[str] = None
    update_time: Optional[datetime] = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """初始化后处理"""
        # 如果没有提供ID，生成一个唯一ID
        if not self.id:
            self.id = self.generate_unique_id()
        
        # 验证sentiment_index范围
        if self.sentiment_index is not None:
            self.sentiment_index = max(0.0, min(100.0, self.sentiment_index))
    
    @staticmethod
    def generate_unique_id() -> str:
        """
        生成唯一标识符
        
        Returns:
            唯一标识符字符串
        """
        # 使用时间戳 + UUID的一部分生成唯一ID
        timestamp_str = datetime.now().strftime('%Y%m%d%H%M%S')
        uuid_suffix = str(uuid.uuid4()).split('-')[0]  # 取UUID的前8位
        return f"marco_{timestamp_str}_{uuid_suffix}"
    
    @classmethod
    def create_for_timestamp(cls, timestamp: datetime, 
                           sentiment_index: Optional[float] = None,
                           summary: Optional[str] = None) -> 'MarcoData':
        """
        为指定时间戳创建Marco数据
        
        Args:
            timestamp: 时间戳
            sentiment_index: 情感指数
            summary: AI总结
            
        Returns:
            MarcoData对象
        """
        return cls(
            id=cls.generate_unique_id(),
            timestamp=timestamp,
            sentiment_index=sentiment_index,
            summary=summary
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，用于数据库插入
        
        Returns:
            字典格式的数据
        """
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'sentiment_index': self.sentiment_index,
            'summary': self.summary,
            'update_time': self.update_time or datetime.now()
        }
    
    def validate(self) -> bool:
        """
        验证数据的有效性
        
        Returns:
            是否有效
        """
        # 必填字段检查
        if not self.id or not self.timestamp:
            return False
        
        # 情感指数范围检查
        if self.sentiment_index is not None:
            if not (0.0 <= self.sentiment_index <= 100.0):
                return False
        
        return True
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"MarcoData(id={self.id}, timestamp={self.timestamp}, sentiment={self.sentiment_index})" 