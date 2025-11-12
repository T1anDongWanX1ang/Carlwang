"""
Project数据模型
基于twitter_projects表结构
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import uuid


@dataclass
class Project:
    """加密货币项目数据模型"""
    
    # 必填字段
    project_id: str  # 项目标识（主键）
    name: str        # 项目名称
    symbol: str      # 代币符号
    
    # 可选字段
    token_address: Optional[str] = None           # 代币地址
    twitter_id: Optional[str] = None              # 官方推特账号ID
    category: Optional[str] = None                # 项目分类（如DEX、L2）
    narratives: Optional[List[str]] = field(default_factory=list)  # 项目叙事列表
    sentiment_index: Optional[float] = None       # 情绪分 [0, 100]
    sentiment_history: Optional[List[Dict[str, Any]]] = field(default_factory=list)  # 情绪历史
    popularity: Optional[int] = 0                 # 项目热度
    popularity_history: Optional[List[Dict[str, Any]]] = field(default_factory=list)  # 热度历史
    summary: Optional[str] = None                 # AI总结
    is_announce: Optional[int] = 0                # 是否为活动公告 (0=否, 1=是)
    announce_summary: Optional[str] = None        # 活动摘要（当is_announce=1时）
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    last_updated: Optional[datetime] = field(default_factory=datetime.now)
    update_time: Optional[datetime] = field(default_factory=datetime.now)
    
    @classmethod
    def generate_project_id(cls) -> str:
        """生成新的project ID，格式：project_随机UUID"""
        return f"project_{str(uuid.uuid4()).replace('-', '')}"
    
    def add_sentiment_history(self, sentiment: float, timestamp: datetime = None):
        """
        添加情感历史记录
        
        Args:
            sentiment: 情感分数
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
    
    def add_popularity_history(self, popularity: int, timestamp: datetime = None):
        """
        添加热度历史记录
        
        Args:
            popularity: 热度分数
            timestamp: 时间戳
        """
        if self.popularity_history is None:
            self.popularity_history = []
            
        if timestamp is None:
            timestamp = datetime.now()
            
        history_data = {
            "popularity": popularity,
            "timestamp": timestamp.isoformat()
        }
        
        self.popularity_history.append(history_data)
    
    def add_narrative(self, narrative: str):
        """
        添加项目叙事
        
        Args:
            narrative: 叙事标签
        """
        if self.narratives is None:
            self.narratives = []
        
        if narrative not in self.narratives:
            self.narratives.append(narrative)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，用于数据库插入

        Returns:
            字典格式的数据
        """
        return {
            'project_id': self.project_id,
            'name': self.name,
            'symbol': self.symbol,
            'token_address': self.token_address,
            'twitter_id': self.twitter_id,
            'category': self.category,
            'narratives': json.dumps(self.narratives or [], ensure_ascii=False),
            'sentiment_index': self.sentiment_index,
            'sentiment_history': json.dumps(self.sentiment_history or [], ensure_ascii=False),
            'popularity': self.popularity,
            'popularity_history': json.dumps(self.popularity_history or [], ensure_ascii=False),
            'summary': self.summary,
            'is_announce': self.is_announce or 0,
            'announce_summary': self.announce_summary,
            'created_at': self.created_at or datetime.now(),
            'last_updated': self.last_updated or datetime.now(),
            'update_time': self.update_time or datetime.now()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """
        从字典创建Project对象
        
        Args:
            data: 字典数据
            
        Returns:
            Project对象
        """
        # 解析JSON字段
        narratives = []
        if data.get('narratives'):
            try:
                narratives = json.loads(data['narratives'])
            except (json.JSONDecodeError, TypeError):
                pass
        
        sentiment_history = []
        if data.get('sentiment_history'):
            try:
                sentiment_history = json.loads(data['sentiment_history'])
            except (json.JSONDecodeError, TypeError):
                pass
        
        popularity_history = []
        if data.get('popularity_history'):
            try:
                popularity_history = json.loads(data['popularity_history'])
            except (json.JSONDecodeError, TypeError):
                pass
        
        return cls(
            project_id=data['project_id'],
            name=data['name'],
            symbol=data['symbol'],
            token_address=data.get('token_address'),
            twitter_id=data.get('twitter_id'),
            category=data.get('category'),
            narratives=narratives,
            sentiment_index=data.get('sentiment_index'),
            sentiment_history=sentiment_history,
            popularity=data.get('popularity', 0),
            popularity_history=popularity_history,
            summary=data.get('summary'),
            is_announce=data.get('is_announce', 0),
            announce_summary=data.get('announce_summary'),
            created_at=data.get('created_at'),
            last_updated=data.get('last_updated'),
            update_time=data.get('update_time')
        )
    
    def validate(self) -> bool:
        """
        验证数据的有效性
        
        Returns:
            是否有效
        """
        # 检查必填字段
        if not self.project_id or not self.name or not self.symbol:
            return False
        
        # 检查情感指数范围
        if self.sentiment_index is not None and (self.sentiment_index < 0 or self.sentiment_index > 100):
            return False
        
        # 检查热度值
        if self.popularity is not None and self.popularity < 0:
            return False
        
        return True
    
    def get_dominant_narrative(self) -> Optional[str]:
        """
        获取主要叙事标签
        
        Returns:
            主要叙事或None
        """
        if self.narratives and len(self.narratives) > 0:
            return self.narratives[0]
        return None
    
    def get_sentiment_trend(self) -> str:
        """
        获取情感趋势
        
        Returns:
            趋势描述: 'rising', 'falling', 'stable', 'unknown'
        """
        if not self.sentiment_history or len(self.sentiment_history) < 2:
            return 'unknown'
        
        recent_sentiments = [h.get('sentiment', 0) for h in self.sentiment_history[-5:]]
        
        if len(recent_sentiments) >= 2:
            trend = recent_sentiments[-1] - recent_sentiments[0]
            if trend > 5:
                return 'rising'
            elif trend < -5:
                return 'falling'
            else:
                return 'stable'
        
        return 'unknown'
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Project(id={self.project_id}, name={self.name}, symbol={self.symbol}, category={self.category})" 