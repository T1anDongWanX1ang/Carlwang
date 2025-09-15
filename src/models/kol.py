"""
KOL数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import json


@dataclass
class KOL:
    """KOL数据模型"""
    
    # 必填字段
    kol_id: str  # 推特账号ID
    
    # 可选字段
    type: Optional[str] = None  # founder/influencer/investor
    tag: Optional[str] = None  # BNB/Meme/AI等标签
    influence_score: Optional[int] = 0
    influence_score_history: Optional[List[Dict[str, Any]]] = field(default_factory=list)
    call_increase_1h: Optional[float] = None
    call_increase_24h: Optional[float] = None
    call_increase_3d: Optional[float] = None
    call_increase_7d: Optional[float] = None
    sentiment: Optional[str] = None  # bullish/bearish/neutral
    sentiment_history: Optional[List[Dict[str, Any]]] = field(default_factory=list)
    summary: Optional[str] = None
    trust_rating: Optional[int] = 0
    is_kol100: Optional[int] = 0
    last_updated: Optional[datetime] = field(default_factory=datetime.now)
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    
    def add_influence_history(self, score: int, timestamp: datetime = None):
        """
        添加影响力历史记录
        
        Args:
            score: 影响力分数
            timestamp: 时间戳
        """
        if self.influence_score_history is None:
            self.influence_score_history = []
            
        if timestamp is None:
            timestamp = datetime.now()
            
        history_data = {
            "score": score,
            "timestamp": timestamp.isoformat()
        }
        
        self.influence_score_history.append(history_data)
    
    def add_sentiment_history(self, sentiment: str, timestamp: datetime = None):
        """
        添加情感历史记录
        
        Args:
            sentiment: 情感方向
            timestamp: 时间戳
        """
        if self.sentiment_history is None:
            self.sentiment_history = []
            
        if timestamp is None:
            timestamp = datetime.now()
            
        history_data = {
            "sentiment": sentiment,
            "timestamp": timestamp.isoformat()
        }
        
        self.sentiment_history.append(history_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，用于数据库插入
        
        Returns:
            字典格式的数据
        """
        return {
            'kol_id': self.kol_id,
            'type': self.type,
            'tag': self.tag,
            'influence_score': self.influence_score,
            'influence_score_history': json.dumps(self.influence_score_history or [], ensure_ascii=False),
            'call_increase_1h': self.call_increase_1h,
            'call_increase_24h': self.call_increase_24h,
            'call_increase_3d': self.call_increase_3d,
            'call_increase_7d': self.call_increase_7d,
            'sentiment': self.sentiment,
            'sentiment_history': json.dumps(self.sentiment_history or [], ensure_ascii=False),
            'summary': self.summary,
            'trust_rating': self.trust_rating,
            'is_kol100': self.is_kol100,
            'last_updated': self.last_updated or datetime.now(),
            'created_at': self.created_at or datetime.now()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KOL':
        """
        从字典创建KOL对象
        
        Args:
            data: 字典数据
            
        Returns:
            KOL对象
        """
        # 解析JSON字段
        influence_score_history = []
        if data.get('influence_score_history'):
            try:
                influence_score_history = json.loads(data['influence_score_history'])
            except (json.JSONDecodeError, TypeError):
                pass
        
        sentiment_history = []
        if data.get('sentiment_history'):
            try:
                sentiment_history = json.loads(data['sentiment_history'])
            except (json.JSONDecodeError, TypeError):
                pass
        
        return cls(
            kol_id=data['kol_id'],
            type=data.get('type'),
            tag=data.get('tag'),
            influence_score=data.get('influence_score', 0),
            influence_score_history=influence_score_history,
            call_increase_1h=data.get('call_increase_1h'),
            call_increase_24h=data.get('call_increase_24h'),
            call_increase_3d=data.get('call_increase_3d'),
            call_increase_7d=data.get('call_increase_7d'),
            sentiment=data.get('sentiment'),
            sentiment_history=sentiment_history,
            summary=data.get('summary'),
            trust_rating=data.get('trust_rating', 0),
            is_kol100=data.get('is_kol100', 0),
            last_updated=data.get('last_updated'),
            created_at=data.get('created_at')
        )
    
    def validate(self) -> bool:
        """
        验证数据的有效性
        
        Returns:
            是否有效
        """
        # 检查必填字段
        if not self.kol_id:
            return False
        
        # 检查KOL类型有效性
        if self.type and self.type not in ['founder', 'influencer', 'investor', 'trader', 'analyst']:
            return False
        
        # 检查情感方向有效性
        if self.sentiment and self.sentiment not in ['bullish', 'bearish', 'neutral']:
            return False
        
        # 检查影响力评分范围
        if self.influence_score is not None and (self.influence_score < 0 or self.influence_score > 100):
            return False
        
        # 检查信任评级范围
        if self.trust_rating is not None and (self.trust_rating < 0 or self.trust_rating > 10):
            return False
        
        return True
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"KOL(id={self.kol_id}, type={self.type}, influence={self.influence_score})" 