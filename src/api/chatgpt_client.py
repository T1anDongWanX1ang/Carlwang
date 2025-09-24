"""
ChatGPT API 客户端
用于话题分析、内容生成和情感分析
"""
import openai
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import time

from ..utils.config_manager import config


class ChatGPTClient:
    """ChatGPT API客户端"""
    
    def __init__(self):
        """初始化ChatGPT客户端"""
        self.chatgpt_config = config.get('chatgpt', {})
        self.api_key = self.chatgpt_config.get('api_key', '')
        self.model = self.chatgpt_config.get('model', 'gpt-3.5-turbo')
        self.timeout = self.chatgpt_config.get('timeout', 30)
        self.max_retries = self.chatgpt_config.get('max_retries', 3)
        self.retry_delay = self.chatgpt_config.get('retry_delay', 2)
        
        # 初始化OpenAI客户端
        openai.api_key = self.api_key
        
        self.logger = logging.getLogger(__name__)
        
        # 请求统计
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
    
    def _make_request(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """
        发起ChatGPT API请求，包含重试机制
        
        Args:
            messages: 对话消息列表
            **kwargs: 其他参数
            
        Returns:
            生成的文本内容或None
        """
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"发起ChatGPT请求 (尝试 {attempt + 1}/{self.max_retries})")
                
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    timeout=self.timeout,
                    **kwargs
                )
                
                self.request_count += 1
                self.success_count += 1
                
                # 提取生成的内容
                content = response.choices[0].message.content
                self.logger.debug(f"ChatGPT请求成功，生成内容长度: {len(content)}")
                
                return content
                
            except openai.error.RateLimitError:
                self.logger.warning(f"ChatGPT速率限制，等待 {self.retry_delay} 秒后重试")
                time.sleep(self.retry_delay * (attempt + 1))
                continue
                
            except openai.error.APIError as e:
                self.logger.error(f"ChatGPT API错误: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    break
                    
            except Exception as e:
                self.logger.error(f"ChatGPT请求异常: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    break
        
        self.request_count += 1
        self.error_count += 1
        return None
    
    def extract_topic_from_tweet(self, tweet_content: str) -> Optional[Dict[str, str]]:
        """
        从推文中提取话题信息
        
        Args:
            tweet_content: 推文内容
            
        Returns:
            话题信息字典 {"topic_name": "...", "brief": "..."}
        """
        try:
            prompt = f"""
            Please analyze the following cryptocurrency-related tweet and extract the main topic:

            Tweet content: {tweet_content}

            Please provide:
            1. topic_name: Concise topic name (5-15 words, highlighting the core theme)
            2. brief: Brief topic description (20-50 words, explaining topic content and background)

            Notes:
            - If the tweet is pure advertising or spam content, return "Invalid Topic"
            - Focus on cryptocurrency, blockchain, DeFi, NFT and related themes
            - Topic name should be specific and meaningful

            Please return in JSON format:
            {{"topic_name": "Topic Name", "brief": "Topic Description"}}
            """
            
            messages = [
                {"role": "system", "content": "You are a professional cryptocurrency market analyst skilled in identifying and analyzing cryptocurrency-related topics."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._make_request(
                messages=messages,
                temperature=0.3,
                max_tokens=200
            )
            
            if response:
                try:
                    # 尝试解析JSON响应
                    result = json.loads(response.strip())
                    
                    # 验证返回的数据
                    if isinstance(result, dict) and 'topic_name' in result and 'brief' in result:
                        topic_name = result['topic_name'].strip()
                        brief = result['brief'].strip()
                        
                        # 过滤无效话题
                        if topic_name == "Invalid Topic" or not topic_name:
                            return None
                            
                        return {
                            "topic_name": topic_name,
                            "brief": brief
                        }
                        
                except json.JSONDecodeError:
                    self.logger.warning(f"ChatGPT返回的不是有效JSON: {response}")
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"提取话题失败: {e}")
            return None
    
    def analyze_sentiment(self, text: str) -> Optional[Dict[str, Any]]:
        """
        分析文本情感
        
        Args:
            text: 文本内容
            
        Returns:
            情感分析结果 {"sentiment": "positive/negative/neutral", "confidence": 0.0-1.0, "score": 0-100}
        """
        try:
            prompt = f"""
            Please analyze the sentiment tendency of the following cryptocurrency-related text:

            Text content: {text}

            Please evaluate:
            1. sentiment: Sentiment direction (positive/negative/neutral)
            2. confidence: Confidence level (0.0-1.0, indicating certainty of judgment)
            3. reasoning: Reasoning for judgment (brief explanation)

            Notes:
            - Focus on cryptocurrency market sentiment
            - Consider the meaning of technical terms and slang
            - positive: bullish, optimistic, supportive
            - negative: bearish, pessimistic, critical
            - neutral: neutral, objective analysis

            Please return in JSON format:
            {{"sentiment": "positive", "confidence": 0.8, "reasoning": "Reasoning"}}
            """
            
            messages = [
                {"role": "system", "content": "You are a professional cryptocurrency sentiment analyst skilled in understanding market sentiment and investor psychology."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._make_request(
                messages=messages,
                temperature=0.2,
                max_tokens=150
            )
            
            if response:
                try:
                    result = json.loads(response.strip())
                    
                    if isinstance(result, dict) and 'sentiment' in result and 'confidence' in result:
                        sentiment = result['sentiment']
                        confidence = float(result['confidence'])
                        
                        # 计算0-100分数
                        if sentiment == "positive":
                            score = 50 + (confidence * 50)
                        elif sentiment == "negative":
                            score = 50 - (confidence * 50)
                        else:  # neutral
                            score = 50
                        
                        return {
                            "sentiment": sentiment,
                            "confidence": confidence,
                            "score": round(score, 1),
                            "reasoning": result.get("reasoning", "")
                        }
                        
                except (json.JSONDecodeError, ValueError, TypeError):
                    self.logger.warning(f"ChatGPT情感分析返回格式错误: {response}")
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"情感分析失败: {e}")
            return None
    
    def generate_topic_summary(self, topic_name: str, related_tweets: List[str], 
                              existing_summary: str = None) -> Optional[str]:
        """
        生成话题总结（使用新的KOL观点分析格式）
        
        Args:
            topic_name: 话题名称
            related_tweets: 相关推文列表
            existing_summary: 已有的总结（用于增量更新）
            
        Returns:
            生成的话题总结（JSON格式的KOL观点分析）
        """
        try:
            # 限制推文数量以控制token使用
            tweets_sample = related_tweets[:15]  # 增加样本数量以获得更好的观点分析
            
            # 构建推文数据（需要更多信息来支持新格式）
            # 注意：这里需要重构调用方法来传递更多数据
            return self._generate_kol_viewpoints_summary(topic_name, tweets_sample, existing_summary)
            
        except Exception as e:
            self.logger.error(f"生成话题总结失败: {e}")
            return None
    
    def _generate_kol_viewpoints_summary(self, topic_name: str, tweets: List[str], existing_summary: str = None) -> Optional[str]:
        """
        使用新的KOL观点分析prompt生成话题总结
        """
        try:
            # 构建推文内容
            tweets_text = "\n".join([f"- {tweet}" for tweet in tweets])
            
            # 使用新的专业prompt
            system_prompt = "You are an experienced web3 media editor, skilled at quickly organizing and summarizing KOL opinions from crypto-related trending topics."
            
            if existing_summary:
                user_prompt = f"""
Please update the KOL opinion summary for topic "{topic_name}", combining new tweet content:

Existing Summary:
{existing_summary}

New Tweet Content:
{tweets_text}

Please update the KOL consensus opinions in the following JSON format (sorted by number of KOLs holding the same opinion, output top 3 opinions):
{{
  "topic_id": "{topic_name}",
  "summary": [
    {{
      "viewpoint": "Opinion summary",
      "related_tweets": ["Tweet content excerpts reflecting this opinion"]
    }}
  ]
}}

Output only the above JSON without additional explanation.
                """
            else:
                user_prompt = f"""
You will receive multiple tweets about topic "{topic_name}" in the following format:

Related Tweets:
{tweets_text}

Please summarize the consensus opinions of KOLs on this event (sorted by number of KOLs holding the same opinion, output top 3 opinions, can be less than 3), in the following JSON format:
{{
  "topic_id": "{topic_name}",
  "summary": [
    {{
      "viewpoint": "Opinion summary",
      "related_tweets": ["Tweet content excerpts reflecting this opinion"]
    }}
  ]
}}

Output only the above JSON without additional explanation.
                """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self._make_request(
                messages=messages,
                temperature=0.3,  # 降低temperature以获得更一致的JSON输出
                max_tokens=500   # 增加token限制以支持更详细的分析
            )
            
            if response:
                return response.strip()
            
            return None
            
        except Exception as e:
            self.logger.error(f"生成KOL观点分析失败: {e}")
            return None
    
    def generate_kol_consensus_summary(self, topic_data: Dict[str, Any]) -> Optional[str]:
        """
        根据完整的话题数据生成KOL共识观点总结
        
        Args:
            topic_data: 包含话题和相关推文的完整数据
            
        Returns:
            KOL观点共识JSON格式的总结
        """
        try:
            import json
            
            system_prompt = "你是一个资深的web3媒体编辑，擅长快速从Crypto相关的热门话题中梳理并总结清楚KOL们发表的观点。"
            
            # 构建输入数据结构
            input_data = {
                "topic_id": topic_data.get('topic_id', ''),
                "topic_name": topic_data.get('topic_name', ''),
                "category": topic_data.get('category', 'crypto'),
                "key_entities": topic_data.get('key_entities', []),
                "timestamp": topic_data.get('timestamp', ''),
                "brief": topic_data.get('brief', ''),
                "related_tweets": []
            }
            
            # 限制推文数量并构建推文数据
            related_tweets = topic_data.get('related_tweets', [])[:20]
            for tweet in related_tweets:
                input_data["related_tweets"].append({
                    "id_str": tweet.get('id_str', ''),
                    "kol_id": tweet.get('kol_id', ''),
                    "full_text": tweet.get('full_text', '')
                })
            
            # 使用JSON序列化构建用户提示
            user_prompt = f"""You will receive multiple KOL tweets about an event in the following format:
{json.dumps(input_data, ensure_ascii=False, indent=2)}

Please summarize the consensus opinions of KOLs on this event (sorted by number of KOLs holding the same opinion, output top 3 opinions, can be less than 3), in the following JSON format:
{{
  "topic_id": Event ID,
  "summary": [
    {{
      "viewpoint": Opinion summary,
      "related_tweets": [Tweet IDs reflecting this opinion, may be multiple],
    }}
  ]
}}

Output only the above JSON without additional explanation."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self._make_request(
                messages=messages,
                temperature=0.2,
                max_tokens=800
            )
            
            return response.strip() if response else None
            
        except Exception as e:
            self.logger.error(f"生成KOL共识观点总结失败: {e}")
            return None
    
    def analyze_mob_opinion_direction(self, tweets: List[str]) -> Optional[str]:
        """
        分析散户整体观点方向
        
        Args:
            tweets: 推文列表
            
        Returns:
            观点方向 positive/negative/neutral
        """
        try:
            # 限制推文数量
            tweets_sample = tweets[:20]
            tweets_text = "\n".join([f"- {tweet}" for tweet in tweets_sample])
            
            prompt = f"""
            Please analyze the overall opinion direction of retail investors in the following tweets:

            Tweet content:
            {tweets_text}

            Please evaluate the overall sentiment tendency of retail investors:
            - positive: Overall optimistic, bullish, supportive
            - negative: Overall pessimistic, bearish, critical
            - neutral: Divided opinions or neutral

            Return only one word: positive, negative or neutral
            """
            
            messages = [
                {"role": "system", "content": "You are a professional market sentiment analyst skilled in analyzing collective emotions of retail investors."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._make_request(
                messages=messages,
                temperature=0.1,
                max_tokens=10
            )
            
            if response:
                direction = response.strip().lower()
                if direction in ['positive', 'negative', 'neutral']:
                    return direction
            
            return 'neutral'  # 默认返回中性
            
        except Exception as e:
            self.logger.error(f"分析散户观点方向失败: {e}")
            return 'neutral'
    
    def batch_analyze_tweets(self, tweets: List[str]) -> List[Dict[str, Any]]:
        """
        批量分析推文
        
        Args:
            tweets: 推文列表
            
        Returns:
            分析结果列表
        """
        results = []
        
        for i, tweet in enumerate(tweets):
            self.logger.info(f"分析推文 {i+1}/{len(tweets)}")
            
            # 提取话题
            topic_info = self.extract_topic_from_tweet(tweet)
            
            # 分析情感
            sentiment_info = self.analyze_sentiment(tweet)
            
            result = {
                "tweet_content": tweet,
                "topic_info": topic_info,
                "sentiment_info": sentiment_info
            }
            
            results.append(result)
            
            # 避免请求过于频繁
            time.sleep(0.5)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取请求统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'total_requests': self.request_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': (self.success_count / max(self.request_count, 1)) * 100
        }
    
    def analyze_kol_profile(self, user_info: Dict[str, Any], recent_tweets: List[str]) -> Optional[Dict[str, Any]]:
        """
        分析用户的KOL特征
        
        Args:
            user_info: 用户基本信息
            recent_tweets: 最近推文列表
            
        Returns:
            KOL分析结果
        """
        try:
            # 限制推文数量
            tweets_sample = recent_tweets[:10]
            tweets_text = "\n".join([f"- {tweet}" for tweet in tweets_sample])
            
            # 检测推文主要语言
            language_tag = self._detect_primary_language(tweets_text)
            
            prompt = f"""
            请分析以下Twitter用户是否为加密货币KOL，并提供详细分析：

            用户信息:
            - 用户名: @{user_info.get('screen_name', 'unknown')}
            - 显示名: {user_info.get('name', 'unknown')}
            - 粉丝数: {user_info.get('followers_count', 0):,}
            - 关注数: {user_info.get('friends_count', 0):,}
            - 推文数: {user_info.get('statuses_count', 0):,}
            - 简介: {user_info.get('description', 'N/A')}

            最近推文内容:
            {tweets_text}

            请提供以下分析：
            1. type: KOL类型（founder/influencer/investor/trader/analyst 或 "not_kol"）
            2. tags: 多个标签列表，必须包含语言标签，格式要求：
               - 语言标签：根据推文主要语言选择"English"或"Chinese"（必须包含）
               - 专业标签：基于推文内容的专业领域，如BTC/ETH/DeFi/NFT/Meme/AI/Gaming/Layer2/RWA等
               - 可以有2-5个标签
            3. sentiment: 市场情感倾向（bullish/bearish/neutral）
            4. summary: 简要总结（50-100字，描述其观点特点和影响力）
            5. trust_rating: 可信度评级（1-10，基于专业度和一致性）

            注意：
            - 如果不是加密货币相关KOL，type返回 "not_kol"
            - tags必须是数组格式，第一个标签必须是语言标签
            - 专注于加密货币、区块链领域的影响力
            - 考虑粉丝数、互动质量和内容专业度

            请以JSON格式返回：
            {{
                "type": "influencer",
                "tags": ["{language_tag}", "DeFi", "BTC"],
                "sentiment": "bullish",
                "summary": "专业的DeFi分析师，经常分享技术分析...",
                "trust_rating": 8
            }}
            """
            
            messages = [
                {"role": "system", "content": "你是一个专业的加密货币KOL识别和分析专家，擅长评估影响力和专业度。"},
                {"role": "user", "content": prompt}
            ]
            
            response = self._make_request(
                messages=messages,
                temperature=0.3,
                max_tokens=300
            )
            
            if response:
                try:
                    # 尝试解析JSON响应
                    result = json.loads(response.strip())
                    
                    # 验证返回的数据
                    if isinstance(result, dict) and 'type' in result:
                        # 过滤非KOL用户
                        if result['type'] == 'not_kol':
                            return None
                        
                        # 处理tags字段：确保语言标签存在且格式正确
                        tags = self._process_kol_tags(result.get('tags', []), language_tag)
                        
                        return {
                            "type": result.get('type'),
                            "tag": tags,  # 注意：这里返回的是拼接后的字符串
                            "sentiment": result.get('sentiment'),
                            "summary": result.get('summary'),
                            "trust_rating": result.get('trust_rating', 5)
                        }
                        
                except json.JSONDecodeError:
                    self.logger.warning(f"ChatGPT KOL分析返回格式错误: {response}")
                    # 使用备用逻辑
                    return self._fallback_kol_analysis(user_info, recent_tweets, language_tag)
            
            # ChatGPT分析失败时，使用备用逻辑
            return self._fallback_kol_analysis(user_info, recent_tweets, language_tag)
            
        except Exception as e:
            self.logger.error(f"KOL分析失败: {e}")
            return self._fallback_kol_analysis(user_info, recent_tweets, "English")
    
    def _detect_primary_language(self, text: str) -> str:
        """
        检测文本主要语言
        
        Args:
            text: 文本内容
            
        Returns:
            语言标签："Chinese"或"English"
        """
        try:
            if not text:
                return "English"
            
            # 简单的中文字符检测
            import re
            chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
            total_chars = len(re.findall(r'[\w\u4e00-\u9fff]', text))
            
            if total_chars == 0:
                return "English"
            
            chinese_ratio = len(chinese_chars) / total_chars
            
            # 如果中文字符占比超过30%，认为是中文内容
            if chinese_ratio > 0.3:
                return "Chinese"
            else:
                return "English"
                
        except Exception as e:
            self.logger.warning(f"语言检测失败: {e}")
            return "English"
    
    def _process_kol_tags(self, raw_tags: List[str], language_tag: str) -> str:
        """
        处理KOL标签：确保语言标签存在，并拼接成字符串
        
        Args:
            raw_tags: 原始标签列表
            language_tag: 检测到的语言标签
            
        Returns:
            拼接后的标签字符串
        """
        try:
            processed_tags = []
            
            # 1. 首先添加语言标签（必须的）
            if language_tag in ["English", "Chinese"]:
                processed_tags.append(language_tag)
            else:
                processed_tags.append("English")  # 默认英文
            
            # 2. 添加专业标签（去重且过滤语言标签）
            if isinstance(raw_tags, list):
                for tag in raw_tags:
                    tag = str(tag).strip()
                    # 跳过语言标签（避免重复）和无效标签
                    if tag not in ["English", "Chinese", "", "Unknown"] and tag not in processed_tags:
                        processed_tags.append(tag)
            
            # 3. 如果没有专业标签，添加默认标签
            if len(processed_tags) == 1:  # 只有语言标签
                processed_tags.append("Crypto")  # 默认加密货币标签
            
            # 4. 限制标签数量（语言标签 + 最多4个专业标签）
            if len(processed_tags) > 5:
                processed_tags = processed_tags[:5]
            
            # 5. 拼接成字符串
            tag_string = ",".join(processed_tags)
            
            self.logger.debug(f"处理标签: {raw_tags} → {tag_string}")
            return tag_string
            
        except Exception as e:
            self.logger.error(f"处理KOL标签失败: {e}")
            return f"{language_tag},Crypto"  # 默认返回语言标签+加密货币标签
    
    def _fallback_kol_analysis(self, user_info: Dict[str, Any], 
                              recent_tweets: List[str], language_tag: str) -> Dict[str, Any]:
        """
        备用KOL分析（当ChatGPT不可用时）
        
        Args:
            user_info: 用户信息
            recent_tweets: 最近推文
            language_tag: 语言标签
            
        Returns:
            KOL分析结果
        """
        try:
            # 基于推文内容进行简单分类
            all_text = " ".join(recent_tweets).lower()
            
            # 识别专业标签
            tag_keywords = {
                "Bitcoin": ["bitcoin", "btc", "比特币"],
                "Ethereum": ["ethereum", "eth", "以太坊", "evm"],
                "DeFi": ["defi", "uniswap", "aave", "compound", "yield", "liquidity"],
                "NFT": ["nft", "opensea", "art", "collection", "mint"],
                "AI": ["ai", "artificial intelligence", "chatgpt", "machine learning"],
                "Gaming": ["gaming", "gamefi", "play to earn", "p2e"],
                "Layer2": ["layer2", "arbitrum", "optimism", "polygon", "scaling"],
                "Meme": ["meme", "doge", "shib", "pepe", "fun"],
                "Trading": ["trading", "chart", "technical analysis", "ta"],
                "RWA": ["rwa", "real world assets", "tokenization"]
            }
            
            detected_tags = [language_tag]  # 语言标签必须包含
            
            for tag_name, keywords in tag_keywords.items():
                if any(keyword in all_text for keyword in keywords):
                    detected_tags.append(tag_name)
            
            # 如果没有检测到专业标签，添加通用标签
            if len(detected_tags) == 1:
                detected_tags.append("Crypto")
            
            # 限制标签数量
            if len(detected_tags) > 5:
                detected_tags = detected_tags[:5]
            
            # 简单的情绪检测
            sentiment = "neutral"
            if any(word in all_text for word in ["bullish", "moon", "pump", "buy", "牛市", "看涨"]):
                sentiment = "bullish"
            elif any(word in all_text for word in ["bearish", "dump", "crash", "sell", "熊市", "看跌"]):
                sentiment = "bearish"
            
            return {
                "type": "influencer",  # 默认类型
                "tag": ",".join(detected_tags),
                "sentiment": sentiment,
                "summary": f"加密货币KOL，主要关注{detected_tags[1] if len(detected_tags) > 1 else 'Crypto'}领域",
                "trust_rating": 6
            }
            
        except Exception as e:
            self.logger.error(f"备用KOL分析失败: {e}")
            return {
                "type": "influencer",
                "tag": f"{language_tag},Crypto",
                "sentiment": "neutral",
                "summary": "加密货币相关KOL",
                "trust_rating": 5
            }
    
    def generate_kol_summary(self, user_info: Dict[str, Any], recent_tweets: List[str], 
                            kol_type: str = None) -> Optional[str]:
        """
        生成KOL总结
        
        Args:
            user_info: 用户信息
            recent_tweets: 最近推文
            kol_type: KOL类型
            
        Returns:
            KOL总结文本
        """
        try:
            tweets_sample = recent_tweets[:15]
            tweets_text = "\n".join([f"- {tweet}" for tweet in tweets_sample])
            
            prompt = f"""
            请为以下加密货币KOL生成专业总结：

            KOL信息:
            - 用户名: @{user_info.get('screen_name', 'unknown')}
            - 类型: {kol_type or '未知'}
            - 粉丝数: {user_info.get('followers_count', 0):,}

            最近推文:
            {tweets_text}

            请提供KOL的观点总结，包括：
            1. 主要关注的项目和赛道
            2. 市场观点和预测倾向
            3. 影响力和专业特点
            4. 近期重要观点

            要求：
            - 客观专业的语调
            - 100-200字以内
            - 突出其独特观点和影响力

            请直接返回总结文本。
            """
            
            messages = [
                {"role": "system", "content": "你是一个专业的加密货币市场分析师，擅长分析KOL的观点和影响力。"},
                {"role": "user", "content": prompt}
            ]
            
            response = self._make_request(
                messages=messages,
                temperature=0.4,
                max_tokens=250
            )
            
            if response:
                return response.strip()
            
            return None
            
        except Exception as e:
            self.logger.error(f"生成KOL总结失败: {e}")
            return None
    
    def analyze_projects_in_tweets(self, tweets_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        从推文中识别和分析加密货币项目
        
        Args:
            tweets_data: 推文数据列表
            
        Returns:
            项目分析结果
        """
        try:
            # 限制推文数量
            tweets_sample = tweets_data[:20]
            
            # 构建推文内容
            tweets_text = []
            for i, tweet in enumerate(tweets_sample, 1):
                content = tweet.get('content', '') or tweet.get('full_text', '')
                user = tweet.get('user_screen_name', '') or tweet.get('screen_name', '')
                engagement = tweet.get('engagement_total', 0)
                
                tweets_text.append(f"{i}. @{user}: {content[:200]}... (互动数: {engagement})")
            
            tweets_content = "\n".join(tweets_text)
            
            prompt = f"""
            You are a professional cryptocurrency project analysis expert. Please identify, analyze and classify cryptocurrency projects from the following tweets.

            Tweet content:
            {tweets_content}

            Please analyze according to the following rules:

            1. **Project Identification Rules**:
            - Identify complete project names (e.g., "Ethereum", "Uniswap")
            - Identify token symbols (e.g., "ETH", "UNI", "BTC")
            - Identify aliases (e.g., "Ethereum", "Bitcoin", "ETH")
            - Confirm genuine cryptocurrency project discussions

            2. **Project Classification System**:
            - Layer1: Bitcoin, Ethereum, Solana, Cardano
            - Layer2: Arbitrum, Optimism, Polygon, Base  
            - DeFi: Uniswap, AAVE, Compound, MakerDAO
            - GameFi: Axie Infinity, The Sandbox
            - NFT: OpenSea, Blur, LooksRare
            - Infrastructure: Chainlink, The Graph
            - Meme: Dogecoin, Shiba Inu, PEPE
            - AI: Fetch.ai, SingularityNET
            - Privacy: Monero, Zcash

            3. **Narrative Tag System**:
            - Technical narratives: "Scalability", "Interoperability", "Privacy"
            - Application narratives: "DeFi Summer", "NFT Boom", "GameFi", "RWA"
            - Ecosystem narratives: "Ethereum Killers", "Multi-chain"
            - Emerging narratives: "AI+Crypto", "DePin", "Liquid Staking"

            4. **Sentiment Analysis Framework**:
            - Positive sentiment (70-100 points): bullish, recommendation, technical breakthrough
            - Neutral sentiment (30-70 points): objective analysis, technical discussion
            - Negative sentiment (0-30 points): bearish, risk warning

            Please return analysis results in JSON format:
            {{
                "projects": [
                    {{
                        "project_id": "ethereum_eth",
                        "name": "Ethereum", 
                        "symbol": "ETH",
                        "category": "Layer1",
                        "narratives": ["Smart Contract Platform", "DeFi"],
                        "sentiment_index": 75.5,
                        "popularity_score": 850,
                        "summary": "Ethereum discussions mainly focus on technical upgrades...",
                        "confidence_score": 0.95,
                        "total_mentions": 5
                    }}
                ],
                "analysis_summary": {{
                    "total_projects_identified": 3,
                    "dominant_narratives": ["DeFi", "Layer2"],
                    "overall_market_sentiment": "bullish"
                }}
            }}
            """
            
            messages = [
                {"role": "system", "content": "You are a professional cryptocurrency project analysis expert skilled in identifying projects from tweets and conducting in-depth analysis."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._make_request(
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )
            
            if response:
                try:
                    # 尝试解析JSON响应
                    result = json.loads(response.strip())
                    
                    # 验证返回的数据
                    if isinstance(result, dict) and 'projects' in result:
                        return result
                        
                except json.JSONDecodeError:
                    self.logger.warning(f"ChatGPT项目分析返回格式错误: {response[:200]}...")
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"项目分析失败: {e}")
            return None
    
    def generate_project_summary(self, project_info: Dict[str, Any], 
                                related_tweets: List[str]) -> Optional[str]:
        """
        生成项目总结
        
        Args:
            project_info: 项目基本信息
            related_tweets: 相关推文列表
            
        Returns:
            项目总结文本
        """
        try:
            tweets_sample = related_tweets[:10]
            tweets_text = "\n".join([f"- {tweet}" for tweet in tweets_sample])
            
            prompt = f"""
            Please generate a professional summary for the cryptocurrency project:

            Project Information:
            - Name: {project_info.get('name', 'Unknown')}
            - Symbol: {project_info.get('symbol', 'Unknown')}
            - Category: {project_info.get('category', 'Unknown')}
            - Narratives: {', '.join(project_info.get('narratives', []))}

            Related Tweet Discussions:
            {tweets_text}

            Please provide a community discussion summary for the project, including:
            1. Main discussion focus and trending topics
            2. Community sentiment and market expectations
            3. KOL opinions and professional analysis
            4. Project development updates and technical progress
            5. Risk factors and concerns

            Requirements:
            - Objective and professional tone
            - 120-150 words
            - Highlight the project's unique value and market position
            - Reflect latest community discussion trends

            Please return the summary text directly.
            """
            
            messages = [
                {"role": "system", "content": "You are a professional cryptocurrency project analyst skilled in analyzing project community sentiment and market performance."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._make_request(
                messages=messages,
                temperature=0.4,
                max_tokens=350
            )
            
            if response:
                return response.strip()
            
            return None
            
        except Exception as e:
            self.logger.error(f"生成项目总结失败: {e}")
            return None
    
    def calculate_project_sentiment(self, project_tweets: List[str]) -> Optional[float]:
        """
        计算项目情感指数
        
        Args:
            project_tweets: 项目相关推文列表
            
        Returns:
            情感指数 (0-100)
        """
        try:
            if not project_tweets:
                return None
            
            tweets_sample = project_tweets[:15]
            tweets_text = "\n".join([f"- {tweet}" for tweet in tweets_sample])
            
            prompt = f"""
            Please analyze the overall sentiment tendency of the following tweets toward the cryptocurrency project:

            Tweet Content:
            {tweets_text}

            Analysis Framework:
            - Positive sentiment (70-100 points): bullish predictions, technical breakthroughs, partnership news, institutional adoption
            - Neutral sentiment (30-70 points): objective analysis, technical discussion, neutral reporting
            - Negative sentiment (0-30 points): bearish predictions, risk warnings, technical issues, negative news

            Please consider comprehensively:
            1. Emotional tone and language of tweets
            2. Price predictions and market expectations
            3. Technical development and project progress
            4. Risk factors and concerns
            5. Community activity and engagement

            Please return a sentiment index score from 0-100 with a brief explanation of the rating.

            Format:
            {{
                "sentiment_index": 75.5,
                "reasoning": "Overall sentiment is positive, mainly based on technical progress and market expectations..."
            }}
            """
            
            messages = [
                {"role": "system", "content": "You are a professional cryptocurrency sentiment analysis expert skilled in quantifying community sentiment."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._make_request(
                messages=messages,
                temperature=0.2,
                max_tokens=200
            )
            
            if response:
                try:
                    result = json.loads(response.strip())
                    return result.get('sentiment_index')
                except json.JSONDecodeError:
                    # 尝试提取数字
                    import re
                    match = re.search(r'(\d+\.?\d*)', response)
                    if match:
                        return float(match.group(1))
            
            return None
            
        except Exception as e:
            self.logger.error(f"计算项目情感失败: {e}")
            return None
    
    def analyze_projects_in_tweets(self, tweets_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        从推文中识别和分析加密货币项目
        
        Args:
            tweets_data: 推文数据列表
            
        Returns:
            项目分析结果
        """
        try:
            # 限制推文数量
            tweets_sample = tweets_data[:20]
            
            # 构建推文内容
            tweets_text = []
            for i, tweet in enumerate(tweets_sample, 1):
                content = tweet.get('content', '') or tweet.get('full_text', '')
                user = tweet.get('user_screen_name', '') or tweet.get('screen_name', '')
                engagement = tweet.get('engagement_total', 0)
                
                tweets_text.append(f"{i}. @{user}: {content[:200]}... (互动数: {engagement})")
            
            tweets_content = "\n".join(tweets_text)
            
            prompt = f"""
            You are a professional cryptocurrency project analysis expert. Please identify, analyze and classify cryptocurrency projects from the following tweets.

            Tweet content:
            {tweets_content}

            Please analyze according to the following rules:

            1. **Project Identification Rules**:
            - Identify complete project names (e.g., "Ethereum", "Uniswap")
            - Identify token symbols (e.g., "ETH", "UNI", "BTC")
            - Identify aliases (e.g., "Ethereum", "Bitcoin", "ETH")
            - Confirm genuine cryptocurrency project discussions

            2. **Project Classification System**:
            - Layer1: Bitcoin, Ethereum, Solana, Cardano
            - Layer2: Arbitrum, Optimism, Polygon, Base  
            - DeFi: Uniswap, AAVE, Compound, MakerDAO
            - GameFi: Axie Infinity, The Sandbox
            - NFT: OpenSea, Blur, LooksRare
            - Infrastructure: Chainlink, The Graph
            - Meme: Dogecoin, Shiba Inu, PEPE
            - AI: Fetch.ai, SingularityNET
            - Privacy: Monero, Zcash

            3. **Narrative Tag System**:
            - Technical narratives: "Scalability", "Interoperability", "Privacy"
            - Application narratives: "DeFi Summer", "NFT Boom", "GameFi", "RWA"
            - Ecosystem narratives: "Ethereum Killers", "Multi-chain"
            - Emerging narratives: "AI+Crypto", "DePin", "Liquid Staking"

            4. **Sentiment Analysis Framework**:
            - Positive sentiment (70-100 points): bullish, recommendation, technical breakthrough
            - Neutral sentiment (30-70 points): objective analysis, technical discussion
            - Negative sentiment (0-30 points): bearish, risk warning

            Please return analysis results in JSON format:
            {{
                "projects": [
                    {{
                        "project_id": "ethereum_eth",
                        "name": "Ethereum", 
                        "symbol": "ETH",
                        "category": "Layer1",
                        "narratives": ["Smart Contract Platform", "DeFi"],
                        "sentiment_index": 75.5,
                        "popularity_score": 850,
                        "summary": "Ethereum discussions mainly focus on technical upgrades...",
                        "confidence_score": 0.95,
                        "total_mentions": 5
                    }}
                ],
                "analysis_summary": {{
                    "total_projects_identified": 3,
                    "dominant_narratives": ["DeFi", "Layer2"],
                    "overall_market_sentiment": "bullish"
                }}
            }}
            """
            
            messages = [
                {"role": "system", "content": "You are a professional cryptocurrency project analysis expert skilled in identifying projects from tweets and conducting in-depth analysis."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._make_request(
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )
            
            if response:
                try:
                    # 尝试解析JSON响应
                    result = json.loads(response.strip())
                    
                    # 验证返回的数据
                    if isinstance(result, dict) and 'projects' in result:
                        return result
                        
                except json.JSONDecodeError:
                    self.logger.warning(f"ChatGPT项目分析返回格式错误: {response[:200]}...")
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"项目分析失败: {e}")
            return None
    
    def generate_project_summary(self, project_info: Dict[str, Any], 
                                related_tweets: List[str]) -> Optional[str]:
        """
        生成项目总结
        
        Args:
            project_info: 项目基本信息
            related_tweets: 相关推文列表
            
        Returns:
            项目总结文本
        """
        try:
            tweets_sample = related_tweets[:10]
            tweets_text = "\n".join([f"- {tweet}" for tweet in tweets_sample])
            
            prompt = f"""
            Please generate a professional summary for the cryptocurrency project:

            Project Information:
            - Name: {project_info.get('name', 'Unknown')}
            - Symbol: {project_info.get('symbol', 'Unknown')}
            - Category: {project_info.get('category', 'Unknown')}
            - Narratives: {', '.join(project_info.get('narratives', []))}

            Related Tweet Discussions:
            {tweets_text}

            Please provide a community discussion summary for the project, including:
            1. Main discussion focus and trending topics
            2. Community sentiment and market expectations
            3. KOL opinions and professional analysis
            4. Project development updates and technical progress
            5. Risk factors and concerns

            Requirements:
            - Objective and professional tone
            - 120-150 words
            - Highlight the project's unique value and market position
            - Reflect latest community discussion trends

            Please return the summary text directly.
            """
            
            messages = [
                {"role": "system", "content": "You are a professional cryptocurrency project analyst skilled in analyzing project community sentiment and market performance."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._make_request(
                messages=messages,
                temperature=0.4,
                max_tokens=350
            )
            
            if response:
                return response.strip()
            
            return None
            
        except Exception as e:
            self.logger.error(f"生成项目总结失败: {e}")
            return None
    
    def calculate_project_sentiment(self, project_tweets: List[str]) -> Optional[float]:
        """
        计算项目情感指数
        
        Args:
            project_tweets: 项目相关推文列表
            
        Returns:
            情感指数 (0-100)
        """
        try:
            if not project_tweets:
                return None
            
            tweets_sample = project_tweets[:15]
            tweets_text = "\n".join([f"- {tweet}" for tweet in tweets_sample])
            
            prompt = f"""
            Please analyze the overall sentiment tendency of the following tweets toward the cryptocurrency project:

            Tweet Content:
            {tweets_text}

            Analysis Framework:
            - Positive sentiment (70-100 points): bullish predictions, technical breakthroughs, partnership news, institutional adoption
            - Neutral sentiment (30-70 points): objective analysis, technical discussion, neutral reporting
            - Negative sentiment (0-30 points): bearish predictions, risk warnings, technical issues, negative news

            Please consider comprehensively:
            1. Emotional tone and language of tweets
            2. Price predictions and market expectations
            3. Technical development and project progress
            4. Risk factors and concerns
            5. Community activity and engagement

            Please return a sentiment index score from 0-100 with a brief explanation of the rating.

            Format:
            {{
                "sentiment_index": 75.5,
                "reasoning": "Overall sentiment is positive, mainly based on technical progress and market expectations..."
            }}
            """
            
            messages = [
                {"role": "system", "content": "You are a professional cryptocurrency sentiment analysis expert skilled in quantifying community sentiment."},
                {"role": "user", "content": prompt}
            ]
            
            response = self._make_request(
                messages=messages,
                temperature=0.2,
                max_tokens=200
            )
            
            if response:
                try:
                    result = json.loads(response.strip())
                    return result.get('sentiment_index')
                except json.JSONDecodeError:
                    # 尝试提取数字
                    import re
                    match = re.search(r'(\d+\.?\d*)', response)
                    if match:
                        return float(match.group(1))
            
            return None
            
        except Exception as e:
            self.logger.error(f"计算项目情感失败: {e}")
            return None
    
    def reset_statistics(self):
        """重置统计信息"""
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0


# 全局ChatGPT客户端实例
chatgpt_client = ChatGPTClient() 