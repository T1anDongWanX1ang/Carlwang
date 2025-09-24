"""
智能分类处理器
用于判断推文是项目还是话题，并自动查找或创建相应的ID
"""
import json
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from src.models.tweet import Tweet
from src.models.topic import Topic
from src.models.project import Project
from src.database.topic_dao import topic_dao
from src.database.project_dao import ProjectDAO
from src.api.chatgpt_client import chatgpt_client


@dataclass
class ClassificationResult:
    """分类结果"""
    content_type: str  # 'project', 'topic', 'unknown'
    project_id: Optional[str] = None
    topic_id: Optional[str] = None
    entity_name: str = ""
    confidence: float = 0.0
    reason: str = ""
    is_new_created: bool = False


class SmartClassifier:
    """智能分类处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.project_dao = ProjectDAO()
        self.topic_dao = topic_dao
        
        # 分类置信度阈值
        self.confidence_threshold = 0.7
    
    def classify_tweet(self, tweet: Tweet) -> ClassificationResult:
        """
        对推文进行智能分类，判断是项目还是话题
        
        Args:
            tweet: 推文对象
            
        Returns:
            ClassificationResult: 分类结果
        """
        try:
            if not tweet.full_text or len(tweet.full_text.strip()) < 10:
                return ClassificationResult(
                    content_type='unknown',
                    reason="推文内容过短或为空"
                )
            
            # 1. 使用AI进行分类
            classification = self._ai_classify_content(tweet.full_text)
            
            if not classification or classification.get('type') == 'unknown':
                return ClassificationResult(
                    content_type='unknown',
                    reason="AI无法识别内容类型"
                )
            
            content_type = classification['type']
            entity_name = classification.get('name', '')
            confidence = classification.get('confidence', 0.0)
            
            # 2. 根据分类结果处理
            if content_type == 'project':
                return self._handle_project_classification(
                    entity_name, classification, tweet.id_str
                )
            elif content_type == 'topic':
                return self._handle_topic_classification(
                    entity_name, classification, tweet
                )
            else:
                return ClassificationResult(
                    content_type='unknown',
                    reason=f"未知内容类型: {content_type}"
                )
                
        except Exception as e:
            self.logger.error(f"分类推文失败 {tweet.id_str}: {e}")
            return ClassificationResult(
                content_type='unknown',
                reason=f"分类过程出错: {str(e)}"
            )
    
    def _ai_classify_content(self, text: str) -> Optional[Dict[str, Any]]:
        """
        使用AI分析推文内容，判断是项目还是话题
        
        Args:
            text: 推文内容
            
        Returns:
            分类结果字典
        """
        prompt = f"""
你是一个专业的加密货币内容分析师。请分析以下推文内容，判断它主要讨论的是：
1. 具体的加密货币项目/代币（如Bitcoin、Ethereum、Solana等具体项目）
2. 一般性的话题讨论（如DeFi、NFT、技术分析、市场动态等概念性话题）

## 推文内容
{text}

## 判断标准
### Project（项目）- 优先级高
- 明确提到具体的项目名称：Bitcoin、BTC、Ethereum、ETH、Solana、SOL等
- 讨论具体项目的价格变动、技术更新、合作伙伴关系
- 提及特定项目的产品发布、升级等
- **重要**：只要提到具体项目名称或代币符号，就应该归类为project

### Topic（话题）- 仅限一般性讨论
- 纯粹讨论概念、趋势、技术等，不涉及具体项目
- 行业动态、监管政策等宏观话题
- 投资策略、市场分析等一般性内容

## 常见项目名称识别
- Bitcoin/BTC → Bitcoin项目
- Ethereum/ETH → Ethereum项目  
- Solana/SOL → Solana项目
- Cardano/ADA → Cardano项目
- Polygon/MATIC → Polygon项目
- Chainlink/LINK → Chainlink项目
- Uniswap/UNI → Uniswap项目

## 输出格式
请返回JSON格式：
{{
  "type": "project" 或 "topic" 或 "unknown",
  "name": "项目名称或话题名称（标准化名称）",
  "brief": "简短描述",
  "confidence": 0.0-1.0,
  "reason": "判断理由"
}}

注意：
- 优先识别为project：如果推文提到任何具体项目名称或代币符号
- 项目名称使用标准名称（如Bitcoin、Ethereum等）
- 话题名称应简洁明了（如DeFi、NFT、技术分析等）
- 如果无法明确判断，返回"unknown"
"""
        
        try:
            # 使用正确的方法调用ChatGPT API
            messages = [
                {"role": "system", "content": "你是一个专业的加密货币内容分析师，擅长识别推文中讨论的项目和话题。"},
                {"role": "user", "content": prompt}
            ]
            
            response = chatgpt_client._make_request(messages, temperature=0.1, max_tokens=300)
            
            if not response:
                self.logger.warning("ChatGPT API返回空响应")
                return None
            
            # 提取JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                
                # 验证返回格式
                if result.get('type') in ['project', 'topic', 'unknown'] and result.get('name'):
                    return result
            
            self.logger.warning(f"AI分类返回格式无效: {response}")
            return None
            
        except Exception as e:
            self.logger.error(f"AI分类失败: {e}")
            return None
    
    def _handle_project_classification(
        self, 
        project_name: str, 
        classification: Dict[str, Any],
        tweet_id: str
    ) -> ClassificationResult:
        """
        处理项目分类结果
        
        Args:
            project_name: 项目名称
            classification: 分类结果
            tweet_id: 推文ID
            
        Returns:
            ClassificationResult
        """
        try:
            # 标准化项目名称
            normalized_name = self._normalize_project_name(project_name)
            
            # 查找现有项目
            existing_project = self.project_dao.get_project_by_name(normalized_name)
            
            if existing_project:
                # 找到现有项目
                self.logger.debug(f"推文 {tweet_id} 匹配到现有项目: {normalized_name}")
                return ClassificationResult(
                    content_type='project',
                    project_id=existing_project.project_id,
                    entity_name=normalized_name,
                    confidence=classification.get('confidence', 0.8),
                    reason=f"匹配到现有项目: {normalized_name}",
                    is_new_created=False
                )
            else:
                # 创建新项目
                new_project_id = self._create_new_project(
                    normalized_name, 
                    classification.get('brief', '')
                )
                
                if new_project_id:
                    self.logger.info(f"推文 {tweet_id} 创建新项目: {normalized_name}")
                    return ClassificationResult(
                        content_type='project',
                        project_id=new_project_id,
                        entity_name=normalized_name,
                        confidence=classification.get('confidence', 0.8),
                        reason=f"创建新项目: {normalized_name}",
                        is_new_created=True
                    )
                else:
                    self.logger.error(f"创建新项目失败: {normalized_name}")
                    return ClassificationResult(
                        content_type='unknown',
                        reason=f"创建新项目失败: {normalized_name}"
                    )
                    
        except Exception as e:
            self.logger.error(f"处理项目分类失败: {e}")
            return ClassificationResult(
                content_type='unknown',
                reason=f"处理项目分类出错: {str(e)}"
            )
    
    def _handle_topic_classification(
        self, 
        topic_name: str, 
        classification: Dict[str, Any],
        tweet
    ) -> ClassificationResult:
        """
        处理话题分类结果，优化识别TopicEngine生成的话题
        
        Args:
            topic_name: 话题名称
            classification: 分类结果
            tweet: 推文对象
            
        Returns:
            ClassificationResult
        """
        try:
            # 标准化话题名称
            normalized_name = self._normalize_topic_name(topic_name)
            
            # 智能查找现有话题（包括模糊匹配）
            existing_topic = self._find_best_matching_topic(normalized_name, tweet.full_text)
            
            if existing_topic:
                # 找到现有话题 - 更新其热度
                current_popularity = self._calculate_initial_popularity(tweet)
                
                # 如果新计算的热度更高，更新现有话题的热度
                if current_popularity > (existing_topic.popularity or 0):
                    try:
                        existing_topic.popularity = current_popularity
                        existing_topic.update_time = datetime.now()
                        
                        # 更新数据库中的热度
                        success = self.topic_dao.update_topic_popularity(
                            existing_topic.topic_id, 
                            current_popularity
                        )
                        
                        if success:
                            self.logger.info(f"推文 {tweet.id_str} 更新现有话题热度: {normalized_name} (热度: {existing_topic.popularity or 0} -> {current_popularity})")
                        else:
                            self.logger.warning(f"更新话题热度失败: {normalized_name}")
                            
                    except Exception as e:
                        self.logger.error(f"更新现有话题热度时出错: {e}")
                
                self.logger.debug(f"推文 {tweet.id_str} 匹配到现有话题: {normalized_name}")
                return ClassificationResult(
                    content_type='topic',
                    topic_id=existing_topic.topic_id,
                    entity_name=normalized_name,
                    confidence=classification.get('confidence', 0.8),
                    reason=f"匹配到现有话题: {normalized_name}",
                    is_new_created=False
                )
            else:
                # 计算初始热度
                initial_popularity = self._calculate_initial_popularity(tweet)
                
                # 创建新话题
                new_topic_id = self._create_new_topic(
                    normalized_name,
                    classification.get('brief', ''),
                    initial_popularity,
                    tweet
                )
                
                if new_topic_id:
                    self.logger.info(f"推文 {tweet.id_str} 创建新话题: {normalized_name} (热度={initial_popularity})")
                    return ClassificationResult(
                        content_type='topic',
                        topic_id=new_topic_id,
                        entity_name=normalized_name,
                        confidence=classification.get('confidence', 0.8),
                        reason=f"创建新话题: {normalized_name}",
                        is_new_created=True
                    )
                else:
                    self.logger.error(f"创建新话题失败: {normalized_name}")
                    return ClassificationResult(
                        content_type='unknown',
                        reason=f"创建新话题失败: {normalized_name}"
                    )
                    
        except Exception as e:
            self.logger.error(f"处理话题分类失败: {e}")
            return ClassificationResult(
                content_type='unknown',
                reason=f"处理话题分类出错: {str(e)}"
            )
    
    def _normalize_project_name(self, name: str) -> str:
        """
        标准化项目名称
        
        Args:
            name: 原始项目名称
            
        Returns:
            标准化后的项目名称
        """
        if not name:
            return ""
        
        # 常见项目名称标准化映射
        project_mapping = {
            'btc': 'Bitcoin',
            'bitcoin': 'Bitcoin',
            'eth': 'Ethereum',
            'ethereum': 'Ethereum',
            'sol': 'Solana',
            'solana': 'Solana',
            'ada': 'Cardano',
            'cardano': 'Cardano',
            'matic': 'Polygon',
            'polygon': 'Polygon',
            'avax': 'Avalanche',
            'avalanche': 'Avalanche',
            'dot': 'Polkadot',
            'polkadot': 'Polkadot',
            'link': 'Chainlink',
            'chainlink': 'Chainlink',
            'uni': 'Uniswap',
            'uniswap': 'Uniswap',
            'aave': 'Aave',
            'comp': 'Compound',
            'compound': 'Compound'
        }
        
        normalized = name.strip().lower()
        return project_mapping.get(normalized, name.strip().title())
    
    def _normalize_topic_name(self, name: str) -> str:
        """
        标准化话题名称
        
        Args:
            name: 原始话题名称
            
        Returns:
            标准化后的话题名称
        """
        if not name:
            return ""
        
        # 常见话题名称标准化映射
        topic_mapping = {
            'defi': 'DeFi',
            'decentralized finance': 'DeFi',
            'nft': 'NFT',
            'non-fungible token': 'NFT',
            'layer2': 'Layer 2',
            'layer 2': 'Layer 2',
            'l2': 'Layer 2',
            'dao': 'DAO',
            'web3': 'Web3',
            'web 3': 'Web3',
            'metaverse': 'Metaverse',
            'gamefi': 'GameFi',
            'yield farming': 'Yield Farming',
            'liquidity mining': 'Liquidity Mining',
            'technical analysis': 'Technical Analysis',
            'market analysis': 'Market Analysis',
            'price prediction': 'Price Prediction',
            'trading': 'Trading',
            'hodl': 'HODL Strategy',
            'bull market': 'Bull Market',
            'bear market': 'Bear Market',
            'regulation': 'Regulation',
            'sec': 'SEC Regulation',
            'etf': 'ETF'
        }
        
        normalized = name.strip().lower()
        return topic_mapping.get(normalized, name.strip().title())
    
    def _find_best_matching_topic(self, topic_name: str, tweet_text: str) -> Optional:
        """
        智能查找最佳匹配的话题，包括精确匹配和模糊匹配
        
        Args:
            topic_name: 话题名称
            tweet_text: 推文内容
            
        Returns:
            匹配的话题对象或None
        """
        try:
            # 1. 精确匹配话题名称
            exact_match = self.topic_dao.get_topic_by_name(topic_name)
            if exact_match:
                self.logger.debug(f"精确匹配到话题: {topic_name}")
                return exact_match
            
            # 2. 搜索相似话题（关键词匹配）
            similar_topics = self.topic_dao.search_topics(topic_name, limit=5)
            if similar_topics:
                # 选择最相似的话题
                best_match = self._select_best_topic_match(similar_topics, topic_name, tweet_text)
                if best_match:
                    self.logger.info(f"模糊匹配到话题: {topic_name} -> {best_match.topic_name}")
                    return best_match
            
            # 3. 基于推文内容关键词搜索话题
            tweet_keywords = self._extract_keywords_from_text(tweet_text)
            for keyword in tweet_keywords:
                keyword_topics = self.topic_dao.search_topics(keyword, limit=3)
                if keyword_topics:
                    best_match = self._select_best_topic_match(keyword_topics, topic_name, tweet_text)
                    if best_match:
                        self.logger.info(f"基于关键词'{keyword}'匹配到话题: {best_match.topic_name}")
                        return best_match
            
            return None
            
        except Exception as e:
            self.logger.error(f"智能话题匹配失败: {e}")
            return None
    
    def _select_best_topic_match(self, topics: list, target_name: str, tweet_text: str):
        """
        从候选话题列表中选择最佳匹配
        
        Args:
            topics: 候选话题列表
            target_name: 目标话题名称
            tweet_text: 推文内容
            
        Returns:
            最佳匹配的话题或None
        """
        if not topics:
            return None
        
        try:
            best_topic = None
            best_score = 0.0
            
            target_words = set(target_name.lower().split())
            tweet_words = set(tweet_text.lower().split())
            
            for topic in topics:
                score = 0.0
                topic_words = set(topic.topic_name.lower().split())
                
                # 计算话题名称相似度
                name_intersection = target_words.intersection(topic_words)
                if name_intersection:
                    score += len(name_intersection) / max(len(target_words), len(topic_words)) * 0.6
                
                # 计算推文内容相关度
                if topic.key_entities:
                    entity_words = set(topic.key_entities.lower().split())
                    content_intersection = tweet_words.intersection(entity_words)
                    if content_intersection:
                        score += len(content_intersection) / len(entity_words) * 0.4
                
                # 选择得分最高的话题（需要达到最低阈值）
                if score > best_score and score >= 0.3:
                    best_score = score
                    best_topic = topic
            
            if best_topic:
                self.logger.debug(f"最佳匹配话题: {best_topic.topic_name} (得分: {best_score:.2f})")
            
            return best_topic
            
        except Exception as e:
            self.logger.error(f"选择最佳话题匹配失败: {e}")
            return None
    
    def _extract_keywords_from_text(self, text: str) -> list:
        """
        从文本中提取关键词
        
        Args:
            text: 文本内容
            
        Returns:
            关键词列表
        """
        if not text:
            return []
        
        # 简单的关键词提取（可以后续改进为更复杂的NLP方法）
        import re
        
        # 移除URL、@用户名、#标签符号
        cleaned_text = re.sub(r'http[s]?://\S+|@\w+|#', '', text.lower())
        
        # 提取有意义的词汇（长度大于2的词）
        words = re.findall(r'\b\w{3,}\b', cleaned_text)
        
        # 过滤停用词（简化版本）
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
        
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # 返回前5个关键词
        return keywords[:5]
    
    def _create_new_project(self, project_name: str, brief: str) -> Optional[str]:
        """
        创建新项目
        
        Args:
            project_name: 项目名称
            brief: 项目描述
            
        Returns:
            项目ID或None
        """
        try:
            # 生成项目ID
            project_id = Project.generate_project_id()
            
            # 推断代币符号
            symbol = self._infer_symbol_from_name(project_name)
            
            # 创建项目对象
            project = Project(
                project_id=project_id,
                name=project_name,
                symbol=symbol,
                summary=brief or f"{project_name} cryptocurrency project",
                created_at=datetime.now(),
                update_time=datetime.now()
            )
            
            # 保存到数据库
            success = self.project_dao.insert_project(project)
            if success:
                return project_id
            else:
                self.logger.error(f"保存新项目到数据库失败: {project_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"创建新项目失败 {project_name}: {e}")
            return None
    
    def _create_new_topic(self, topic_name: str, brief: str, initial_popularity: int = 1, tweet=None) -> Optional[str]:
        """
        创建新话题
        
        Args:
            topic_name: 话题名称
            brief: 话题描述
            initial_popularity: 初始热度值
            tweet: 相关推文对象（可选）
            
        Returns:
            话题ID或None
        """
        try:
            # 生成话题ID
            topic_id = Topic.generate_topic_id()
            
            # 生成基础的summary（JSON格式以保持一致性）
            basic_summary = self._generate_basic_topic_summary(topic_id, topic_name, brief, tweet)
            
            # 创建话题对象
            topic = Topic(
                topic_id=topic_id,
                topic_name=topic_name,
                brief=brief or f"{topic_name} 相关讨论话题",
                created_at=datetime.now(),
                popularity=initial_popularity,
                summary=basic_summary,
                update_time=datetime.now()
            )
            
            # 保存到数据库
            success = self.topic_dao.insert(topic)
            if success:
                return topic_id
            else:
                self.logger.error(f"保存新话题到数据库失败: {topic_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"创建新话题失败 {topic_name}: {e}")
            return None
    
    def _generate_basic_topic_summary(self, topic_id: str, topic_name: str, brief: str, tweet=None) -> str:
        """
        生成基础的话题summary（避免单个推文时调用ChatGPT API）
        
        Args:
            topic_id: 话题ID
            topic_name: 话题名称
            brief: 话题描述
            tweet: 相关推文对象（可选）
            
        Returns:
            JSON格式的基础summary
        """
        import json
        
        # 基于话题名称和描述生成基础观点
        viewpoint = brief or f"关于{topic_name}的初步讨论和观点分析"
        
        # 获取相关推文ID
        related_tweets = []
        if tweet and hasattr(tweet, 'id_str') and tweet.id_str:
            related_tweets = [tweet.id_str]
        
        basic_summary = {
            "topic_id": topic_id,
            "summary": [
                {
                    "viewpoint": viewpoint,
                    "related_tweets": related_tweets
                }
            ]
        }
        
        return json.dumps(basic_summary, ensure_ascii=False)
    
    def _infer_symbol_from_name(self, project_name: str) -> str:
        """
        从项目名称推断代币符号
        
        Args:
            project_name: 项目名称
            
        Returns:
            代币符号
        """
        symbol_mapping = {
            'Bitcoin': 'BTC',
            'Ethereum': 'ETH',
            'Solana': 'SOL',
            'Cardano': 'ADA',
            'Polygon': 'MATIC',
            'Avalanche': 'AVAX',
            'Polkadot': 'DOT',
            'Chainlink': 'LINK',
            'Uniswap': 'UNI',
            'Aave': 'AAVE',
            'Compound': 'COMP'
        }
        
        return symbol_mapping.get(project_name, project_name.upper()[:4])
    
    def _calculate_initial_popularity(self, tweet) -> int:
        """
        根据推文的互动数据计算初始热度
        
        Args:
            tweet: 推文对象
            
        Returns:
            热度值 (1-10)
        """
        try:
            # 获取推文的各种互动数据
            engagement_total = getattr(tweet, 'engagement_total', 0) or 0
            favorite_count = getattr(tweet, 'favorite_count', 0) or 0
            retweet_count = getattr(tweet, 'retweet_count', 0) or 0
            reply_count = getattr(tweet, 'reply_count', 0) or 0
            view_count = getattr(tweet, 'view_count', 0) or 0
            
            # 权重计算热度
            # 使用对数缩放避免极值影响
            import math
            
            popularity = 1  # 基础热度
            
            # 根据总互动量增加热度
            if engagement_total > 0:
                popularity += min(3, math.log10(engagement_total + 1))
            
            # 根据点赞数增加热度  
            if favorite_count > 10:
                popularity += min(2, math.log10(favorite_count / 10 + 1))
            
            # 根据转发数增加热度（权重较高）
            if retweet_count > 5:
                popularity += min(3, math.log10(retweet_count / 5 + 1))
            
            # 根据回复数增加热度
            if reply_count > 3:
                popularity += min(2, math.log10(reply_count / 3 + 1))
            
            # 确保热度在1-10范围内
            popularity = max(1, min(10, int(popularity)))
            
            return popularity
            
        except Exception as e:
            self.logger.warning(f"计算初始热度失败，使用默认值: {e}")
            return 1


# 全局实例
smart_classifier = SmartClassifier()