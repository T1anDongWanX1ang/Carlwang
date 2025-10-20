"""
高级topic提取和去重处理器
基于新的topic识别和去重逻辑
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

from src.models.topic import Topic
from src.database.topic_dao import topic_dao
from src.api.chatgpt_client import chatgpt_client


@dataclass
class TopicAnalysisResult:
    """Topic分析结果"""
    has_topic: bool = False
    is_reuse: bool = False
    topic_id: Optional[str] = None
    topic_data: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    reason: str = ""


class AdvancedTopicProcessor:
    """高级topic提取和去重处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # topic识别标准
        self.topic_criteria = [
            "项目发布/更新（新币上线、协议升级、产品发布等）",
            "重大合作伙伴关系或投资",
            "监管政策变化",
            "技术突破或漏洞",
            "市场重大波动及其原因",
            "重要人物动态（CEO离职、知名投资者表态等）",
            "交易所上币/下架",
            "黑客攻击或安全事件"
        ]
        
        # 相似度阈值
        self.similarity_threshold = 0.7
        
        # 时间窗口（48小时）
        self.time_window_hours = 48
    
    def process_tweet_for_topic(self, tweet_data: Dict[str, Any]) -> TopicAnalysisResult:
        """
        处理推文，提取topic或复用已有topic
        
        Args:
            tweet_data: 推文数据，包含author, content, created_at
            
        Returns:
            TopicAnalysisResult: 分析结果
        """
        try:
            # 1. 分析推文内容，判断是否包含topic
            topic_analysis = self._analyze_tweet_content(tweet_data)
            
            if not topic_analysis.get('has_topic', False):
                return TopicAnalysisResult(
                    has_topic=False,
                    reason="推文内容不包含符合标准的topic"
                )
            
            # 2. 获取最近48小时的已有topics用于去重比较
            cutoff_time = datetime.now() - timedelta(hours=self.time_window_hours)
            recent_topics = topic_dao.get_topics_since(cutoff_time)
            
            # 3. 检查是否与已有topic重复
            duplicate_check = self._check_topic_duplication(
                topic_analysis, recent_topics, tweet_data
            )
            
            if duplicate_check['is_duplicate']:
                # 复用已有topic
                return TopicAnalysisResult(
                    has_topic=True,
                    is_reuse=True,
                    topic_id=duplicate_check['existing_topic_id'],
                    confidence=duplicate_check['confidence'],
                    reason=f"复用已有topic: {duplicate_check['reason']}"
                )
            
            # 4. 创建新topic
            new_topic_data = self._create_new_topic_data(topic_analysis, tweet_data)
            
            return TopicAnalysisResult(
                has_topic=True,
                is_reuse=False,
                topic_data=new_topic_data,
                confidence=topic_analysis.get('confidence', 0.8),
                reason="创建新topic"
            )
            
        except Exception as e:
            self.logger.error(f"处理推文topic时出错: {e}")
            return TopicAnalysisResult(
                has_topic=False,
                reason=f"处理出错: {str(e)}"
            )
    
    def _analyze_tweet_content(self, tweet_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用AI分析推文内容，判断是否包含重要topic
        
        Args:
            tweet_data: 推文数据
            
        Returns:
            分析结果字典
        """
        content = tweet_data.get('content', '')
        author = tweet_data.get('author', '')
        
        prompt = f"""
You are a professional cryptocurrency topic extraction assistant. Please analyze the following KOL tweet to determine if it contains important topics.

## Topic Identification Standards
The following types of content should be identified as topics:
- Project launches/updates (new coin listings, protocol upgrades, product releases, etc.)
- Major partnerships or investments
- Regulatory policy changes
- Technical breakthroughs or vulnerabilities
- Major market volatility and its causes
- Important personnel dynamics (CEO departures, prominent investor statements, etc.)
- Exchange listings/delistings
- Hacking attacks or security incidents

## Tweet Information
Author: {author}
Content: {content}

## Output Requirements
Please return in JSON format with the following fields:
- has_topic: Whether it contains important topics (true/false)
- topic_name: Topic name (if has_topic is true) - must be in English
- brief: Topic brief description (if has_topic is true) - must be in English
- key_entities: Related projects/people/exchanges etc., comma-separated (if has_topic is true)
- topic_type: Topic type (corresponding to one of the 8 standards above)
- confidence: Confidence level (between 0-1)
- reason: Reasoning for judgment

Example:
{{
  "has_topic": true,
  "topic_name": "Bitcoin Breaks Through $65,000",
  "brief": "Bitcoin price reaches new high, breaking through the $65,000 threshold",
  "key_entities": "Bitcoin, BTC, price breakthrough",
  "topic_type": "Major market volatility and its causes",
  "confidence": 0.9,
  "reason": "Clear price breakthrough event with significant market impact"
}}

IMPORTANT: All output must be in English, including topic_name and brief fields.
"""
        
        try:
            response = chatgpt_client.chat(prompt)
            return json.loads(response)
            
        except Exception as e:
            self.logger.error(f"AI分析推文内容失败: {e}")
            return {"has_topic": False, "reason": f"AI分析失败: {str(e)}"}
    
    def _check_topic_duplication(
        self, 
        topic_analysis: Dict[str, Any], 
        recent_topics: List[Topic],
        tweet_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        检查topic是否与已有topic重复
        
        Args:
            topic_analysis: 当前topic分析结果
            recent_topics: 最近的topic列表
            tweet_data: 推文数据
            
        Returns:
            去重检查结果
        """
        if not recent_topics:
            return {"is_duplicate": False}
        
        current_topic_name = topic_analysis.get('topic_name', '')
        current_entities = topic_analysis.get('key_entities', '')
        current_type = topic_analysis.get('topic_type', '')
        tweet_time = datetime.fromisoformat(tweet_data.get('created_at', ''))
        
        for existing_topic in recent_topics:
            # 检查时间接近性（48小时内）
            time_diff = abs((tweet_time - existing_topic.created_at).total_seconds() / 3600)
            if time_diff <= self.time_window_hours:
                
                # 使用AI进行相似度比较
                similarity_result = self._calculate_topic_similarity(
                    current_topic_name, current_entities, current_type,
                    existing_topic.topic_name, existing_topic.key_entities or '',
                    existing_topic.brief or ''
                )
                
                if similarity_result['is_similar']:
                    return {
                        "is_duplicate": True,
                        "existing_topic_id": existing_topic.topic_id,
                        "confidence": similarity_result['confidence'],
                        "reason": similarity_result['reason']
                    }
        
        return {"is_duplicate": False}
    
    def _calculate_topic_similarity(
        self, 
        topic1_name: str, topic1_entities: str, topic1_type: str,
        topic2_name: str, topic2_entities: str, topic2_brief: str
    ) -> Dict[str, Any]:
        """
        使用AI计算两个topic的相似度
        
        Args:
            topic1_*: 第一个topic的信息
            topic2_*: 第二个topic的信息
            
        Returns:
            相似度计算结果
        """
        prompt = f"""
You are a professional topic similarity assessment assistant. Please determine if the following two topics refer to the same event.

## Assessment Criteria
The topics are considered the same if any of the following conditions are met:
- Same subject + same topic type + close timing (time proximity already confirmed at outer level)
- Core keyword overlap ≥ 70%
- Topics are essentially the same, just expressed differently

## Topic 1
Name: {topic1_name}
Related entities: {topic1_entities}
Type: {topic1_type}

## Topic 2
Name: {topic2_name}
Related entities: {topic2_entities}
Brief: {topic2_brief}

## Output Requirements
Please return in JSON format:
{{
  "is_similar": true/false,
  "confidence": 0.0-1.0,
  "reason": "Assessment reasoning"
}}
"""
        
        try:
            response = chatgpt_client.chat(prompt)
            result = json.loads(response)
            
            # 应用阈值
            if result.get('confidence', 0) >= self.similarity_threshold:
                result['is_similar'] = True
            else:
                result['is_similar'] = False
                
            return result
            
        except Exception as e:
            self.logger.error(f"AI计算topic相似度失败: {e}")
            return {
                "is_similar": False,
                "confidence": 0.0,
                "reason": f"相似度计算失败: {str(e)}"
            }
    
    def _create_new_topic_data(
        self, 
        topic_analysis: Dict[str, Any], 
        tweet_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        创建新topic的完整数据
        
        Args:
            topic_analysis: topic分析结果
            tweet_data: 推文数据
            
        Returns:
            新topic数据字典
        """
        # 生成新的topic ID
        topic_id = Topic.generate_topic_id()
        
        # 创建基础topic数据
        topic_data = {
            'topic_id': topic_id,
            'topic_name': topic_analysis.get('topic_name', ''),
            'created_at': datetime.now(),
            'brief': topic_analysis.get('brief', ''),
            'key_entities': topic_analysis.get('key_entities', ''),
            'popularity': 1,  # 初始热度为1
            'propagation_speed_5m': 0.0,
            'propagation_speed_1h': 0.0,
            'propagation_speed_4h': 0.0,
            'kol_opinions': [],
            'mob_opinion_direction': 'neutral',
            'summary': topic_analysis.get('brief', ''),
            'popularity_history': [],
            'update_time': datetime.now()
        }
        
        # 添加初始KOL观点
        author = tweet_data.get('author', '')
        if author:
            kol_opinion = {
                'kol_id': author,
                'opinion': tweet_data.get('content', '')[:200],  # 截取前200字符
                'direction': 'neutral',  # 可以后续通过情感分析确定
                'timestamp': tweet_data.get('created_at', datetime.now().isoformat())
            }
            topic_data['kol_opinions'] = [kol_opinion]
        
        return topic_data
    
    def save_or_update_topic(self, analysis_result: TopicAnalysisResult) -> bool:
        """
        保存或更新topic数据
        
        Args:
            analysis_result: topic分析结果
            
        Returns:
            是否成功
        """
        try:
            if analysis_result.is_reuse:
                # 更新已有topic的热度等信息
                return self._update_existing_topic(analysis_result.topic_id)
            else:
                # 保存新topic
                if analysis_result.topic_data:
                    topic = Topic(**analysis_result.topic_data)
                    return topic_dao.insert(topic)
                    
            return False
            
        except Exception as e:
            self.logger.error(f"保存或更新topic失败: {e}")
            return False
    
    def _update_existing_topic(self, topic_id: str) -> bool:
        """
        更新已有topic的热度等信息
        
        Args:
            topic_id: topic ID
            
        Returns:
            是否成功
        """
        try:
            # 获取现有topic
            existing_topic = topic_dao.get_by_id(topic_id)
            if not existing_topic:
                return False
            
            # 更新热度
            existing_topic.popularity = (existing_topic.popularity or 0) + 1
            existing_topic.update_time = datetime.now()
            
            # 添加热度历史记录
            existing_topic.add_popularity_history(existing_topic.popularity)
            
            # 保存更新
            return topic_dao.update(existing_topic)
            
        except Exception as e:
            self.logger.error(f"更新已有topic失败: {e}")
            return False


# 全局实例
advanced_topic_processor = AdvancedTopicProcessor()