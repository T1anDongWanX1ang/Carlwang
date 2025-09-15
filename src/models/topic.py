"""
话题数据模型 - 基于新的topic识别和去重逻辑
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import json
import uuid


@dataclass
class Topic:
    """话题数据模型 - 新版本使用UUID作为主键"""
    
    # 主键字段 - 使用UUID格式：topic_xxx
    topic_id: Optional[str] = None
    topic_name: Optional[str] = None
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    brief: Optional[str] = None
    key_entities: Optional[str] = None  # 新增：相关项目/人物/交易所等
    popularity: Optional[int] = 0
    propagation_speed_5m: Optional[float] = None
    propagation_speed_1h: Optional[float] = None
    propagation_speed_4h: Optional[float] = None
    kol_opinions: Optional[List[Dict[str, Any]]] = field(default_factory=list)
    mob_opinion_direction: Optional[str] = None  # positive/negative/neutral
    summary: Optional[str] = None
    popularity_history: Optional[List[Dict[str, Any]]] = field(default_factory=list)
    update_time: Optional[datetime] = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """后初始化处理 - 自动生成topic_id如果未提供"""
        if self.topic_id is None:
            self.topic_id = self.generate_topic_id()
    
    @classmethod
    def generate_topic_id(cls) -> str:
        """生成新的topic ID，格式：topic_随机UUID"""
        return f"topic_{str(uuid.uuid4()).replace('-', '')}"
    
    def add_kol_opinion(self, kol_id: str, opinion: str, direction: str, influence_score: float = None):
        """
        添加KOL观点
        
        Args:
            kol_id: KOL ID
            opinion: 观点内容
            direction: 观点方向 (positive/negative/neutral)
            influence_score: 影响力评分
        """
        if self.kol_opinions is None:
            self.kol_opinions = []
            
        opinion_data = {
            "kol_id": kol_id,
            "opinion": opinion,
            "direction": direction,
            "influence_score": influence_score,
            "timestamp": datetime.now().isoformat()
        }
        
        self.kol_opinions.append(opinion_data)
    
    def add_popularity_history(self, popularity_value: int, timestamp: datetime = None):
        """
        添加热度历史记录
        
        Args:
            popularity_value: 热度值
            timestamp: 时间戳
        """
        if self.popularity_history is None:
            self.popularity_history = []
            
        if timestamp is None:
            timestamp = datetime.now()
            
        history_data = {
            "popularity": popularity_value,
            "timestamp": timestamp.isoformat()
        }
        
        self.popularity_history.append(history_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，用于数据库插入
        
        Returns:
            字典格式的数据
        """
        return {
            'topic_id': self.topic_id,
            'topic_name': self.topic_name,
            'created_at': self.created_at or datetime.now(),
            'brief': self.brief,
            'key_entities': self.key_entities,  # 新增字段
            'popularity': self.popularity or 0,
            'propagation_speed_5m': self.propagation_speed_5m,
            'propagation_speed_1h': self.propagation_speed_1h,
            'propagation_speed_4h': self.propagation_speed_4h,
            'kol_opinions': json.dumps(self.kol_opinions or [], ensure_ascii=False),
            'mob_opinion_direction': self.mob_opinion_direction,
            'summary': self.summary,
            'popularity_history': json.dumps(self.popularity_history or [], ensure_ascii=False),
            'update_time': self.update_time or datetime.now()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Topic':
        """
        从字典创建Topic对象
        
        Args:
            data: 字典数据
            
        Returns:
            Topic对象
        """
        # 解析JSON字段
        kol_opinions = []
        if data.get('kol_opinions'):
            try:
                kol_opinions = json.loads(data['kol_opinions'])
            except (json.JSONDecodeError, TypeError):
                pass
        
        popularity_history = []
        if data.get('popularity_history'):
            try:
                popularity_history = json.loads(data['popularity_history'])
            except (json.JSONDecodeError, TypeError):
                pass
        
        return cls(
            topic_id=data.get('topic_id'),
            topic_name=data.get('topic_name'),
            created_at=data.get('created_at'),
            brief=data.get('brief'),
            key_entities=data.get('key_entities'),  # 新增字段
            popularity=data.get('popularity', 0),
            propagation_speed_5m=data.get('propagation_speed_5m'),
            propagation_speed_1h=data.get('propagation_speed_1h'),
            propagation_speed_4h=data.get('propagation_speed_4h'),
            kol_opinions=kol_opinions,
            mob_opinion_direction=data.get('mob_opinion_direction'),
            summary=data.get('summary'),
            popularity_history=popularity_history,
            update_time=data.get('update_time')
        )
    
    def validate(self) -> bool:
        """
        验证数据的有效性
        
        Returns:
            是否有效
        """
        # 检查必填字段
        if not self.topic_name:
            return False
        
        # 检查观点方向有效性
        if self.mob_opinion_direction and self.mob_opinion_direction not in ['positive', 'negative', 'neutral']:
            return False
        
        # 检查热度值范围
        if self.popularity is not None and self.popularity < 0:
            return False
        
        return True
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Topic(id={self.topic_id}, name={self.topic_name}, popularity={self.popularity})" 