"""
Gemini API 客户端
用于话题分析、内容生成和情感分析
"""
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import time

from google import genai

from ..utils.config_manager import config


class ChatGPTClient:
    """Gemini API客户端"""
    
    def __init__(self):
        """初始化Gemini客户端"""
        self.chatgpt_config = config.get('chatgpt', {})
        self.api_key = self.chatgpt_config.get('api_key', '')
        self.model = self.chatgpt_config.get('model', 'gemini-2.5-flash-lite')
        self.timeout = self.chatgpt_config.get('timeout', 30)
        self.max_retries = self.chatgpt_config.get('max_retries', 3)
        self.retry_delay = self.chatgpt_config.get('retry_delay', 2)
        
        # 延迟初始化客户端，避免模块导入时的问题
        self.client = None
        
        self.logger = logging.getLogger(__name__)
        
        # 请求统计
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        
        # 批处理优化配置
        batch_config = self.chatgpt_config.get('batch_processing', {})
        opt_config = self.chatgpt_config.get('optimization', {})
        
        self.enable_batch_consolidation = opt_config.get('enable_batch_consolidation', True)
        self.max_prompt_tokens = opt_config.get('max_prompt_tokens', 3000)
        self.content_merge_threshold = batch_config.get('content_merge_threshold', 2000)
        
        # 响应缓存
        self.enable_response_caching = opt_config.get('enable_response_caching', True)
        self.response_cache = {} if self.enable_response_caching else None
        self.cache_ttl_hours = opt_config.get('cache_ttl_hours', 24)
        
        # 打印模型配置信息
        self.logger.info(f"🤖 Gemini客户端初始化完成")
        self.logger.info(f"📋 使用模型: {self.model}")
        self.logger.info(f"🔑 API密钥: {self.api_key[:10]}...{self.api_key[-4:] if len(self.api_key) > 14 else '*' * 4}")
        self.logger.info(f"⚙️  超时设置: {self.timeout}秒，最大重试: {self.max_retries}次")
    
    def _get_client(self):
        """获取Gemini客户端（延迟初始化）"""
        if self.client is None:
            self.client = genai.Client(api_key=self.api_key)
        return self.client
    
    def _make_request(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """
        发起Gemini API请求，包含重试机制
        
        Args:
            messages: 对话消息列表
            **kwargs: 其他参数（temperature, max_tokens等，Gemini可能不支持所有参数）
            
        Returns:
            生成的文本内容或None
        """
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"发起Gemini请求 (尝试 {attempt + 1}/{self.max_retries})")
                
                # Gemini API调用
                client = self._get_client()
                chat = client.chats.create(model=self.model)
                
                # 将messages转换为Gemini格式
                # Gemini使用单条消息，需要合并system和user消息
                system_content = ""
                user_content = ""
                for msg in messages:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    if role == 'system':
                        system_content = content
                    elif role == 'user':
                        if user_content:
                            user_content += "\n\n" + content
                        else:
                            user_content = content
                
                # 合并system和user内容
                if system_content:
                    prompt = f"{system_content}\n\n{user_content}"
                else:
                    prompt = user_content
                
                response = chat.send_message(prompt)
                content = response.text
                
                self.request_count += 1
                self.success_count += 1
                
                self.logger.debug(f"Gemini请求成功，生成内容长度: {len(content)}")
                
                return content
                
            except Exception as e:
                error_type = type(e).__name__
                error_str = str(e).lower()
                
                # 处理速率限制错误
                if 'RateLimitError' in error_type or 'rate_limit' in error_str or '429' in error_str or 'quota' in error_str:
                    self.logger.warning(f"Gemini速率限制，等待 {self.retry_delay} 秒后重试")
                    self.logger.error(f"RateLimitError详情: {str(e)}")
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                
                # 处理API错误
                if 'APIError' in error_type or 'api' in error_str or '400' in error_str or '500' in error_str:
                    self.logger.error(f"Gemini API错误: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        break
                
                # 其他异常
                self.logger.error(f"Gemini请求异常: {e}")
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
                    # 清理响应内容，移除代码块标记
                    cleaned_response = response.strip()
                    if cleaned_response.startswith('```json'):
                        cleaned_response = cleaned_response[7:]  # 移除 ```json
                    if cleaned_response.startswith('```'):
                        cleaned_response = cleaned_response[3:]  # 移除 ```
                    if cleaned_response.endswith('```'):
                        cleaned_response = cleaned_response[:-3]  # 移除结尾的 ```
                    cleaned_response = cleaned_response.strip()

                    # 尝试解析JSON响应
                    result = json.loads(cleaned_response)

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
                    # 清理响应内容，移除代码块标记
                    cleaned_response = response.strip()
                    if cleaned_response.startswith('```json'):
                        cleaned_response = cleaned_response[7:]  # 移除 ```json
                    if cleaned_response.startswith('```'):
                        cleaned_response = cleaned_response[3:]  # 移除 ```
                    if cleaned_response.endswith('```'):
                        cleaned_response = cleaned_response[:-3]  # 移除结尾的 ```
                    cleaned_response = cleaned_response.strip()

                    # 尝试解析JSON响应
                    result = json.loads(cleaned_response)

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
    
    def batch_extract_topics_from_tweets(self, tweets: List[str]) -> List[Optional[Dict[str, str]]]:
        """
        智能批量话题提取，优化token使用
        
        Args:
            tweets: 推文内容列表
            
        Returns:
            话题信息列表，每个元素对应输入推文的话题信息
        """
        if not tweets:
            return []
            
        # 1. 检查缓存
        cached_results = []
        uncached_tweets = []
        uncached_indices = []
        
        for i, tweet in enumerate(tweets):
            cached_result = self._get_cached_response(tweet, 'topic_extraction')
            if cached_result:
                cached_results.append((i, cached_result))
            else:
                uncached_tweets.append(tweet)
                uncached_indices.append(i)
        
        # 2. 如果没有未缓存的推文，直接返回
        if not uncached_tweets:
            results = [None] * len(tweets)
            for idx, result in cached_results:
                results[idx] = result
            return results
        
        # 3. 内容去重和合并
        if self.enable_batch_consolidation and len(uncached_tweets) > 1:
            batch_results = self._batch_extract_topics_consolidated(uncached_tweets)
        else:
            # 逐个处理（旧方式）
            batch_results = []
            for tweet in uncached_tweets:
                result = self.extract_topic_from_tweet(tweet)
                batch_results.append(result)
        
        # 4. 缓存结果
        for i, result in enumerate(batch_results):
            if result and self.enable_response_caching:
                self._cache_response(uncached_tweets[i], 'topic_extraction', result)
        
        # 5. 合并缓存和新结果
        final_results = [None] * len(tweets)
        for idx, result in cached_results:
            final_results[idx] = result
        for i, idx in enumerate(uncached_indices):
            final_results[idx] = batch_results[i] if i < len(batch_results) else None
            
        return final_results
    
    def _batch_extract_topics_consolidated(self, tweets: List[str]) -> List[Optional[Dict[str, str]]]:
        """
        合并内容进行批量话题提取，减少API调用
        """
        try:
            # 合并相似内容
            content_groups = self._group_similar_content(tweets)
            
            results = [None] * len(tweets)
            
            for group_indices, group_tweets in content_groups:
                if len(group_tweets) == 1:
                    # 单条推文
                    result = self.extract_topic_from_tweet(group_tweets[0])
                    results[group_indices[0]] = result
                else:
                    # 批量处理
                    batch_result = self._extract_topics_from_merged_content(group_tweets)
                    # 将结果分配给组内所有推文
                    for idx in group_indices:
                        results[idx] = batch_result
            
            return results
            
        except Exception as e:
            self.logger.error(f"批量话题提取失败: {e}")
            # 回退到逐个处理
            return [self.extract_topic_from_tweet(tweet) for tweet in tweets]
    
    def _group_similar_content(self, tweets: List[str]) -> List[Tuple[List[int], List[str]]]:
        """
        基于内容相似度将推文分组
        """
        import hashlib
        
        groups = []
        processed = set()
        
        for i, tweet in enumerate(tweets):
            if i in processed:
                continue
                
            # 简单的相似度检查 - 基于关键词
            current_group_indices = [i]
            current_group_tweets = [tweet]
            processed.add(i)
            
            tweet_keywords = set(tweet.lower().split())
            
            # 查找相似推文
            for j, other_tweet in enumerate(tweets[i+1:], i+1):
                if j in processed:
                    continue
                    
                other_keywords = set(other_tweet.lower().split())
                # 计算Jaccard相似度
                intersection = tweet_keywords & other_keywords
                union = tweet_keywords | other_keywords
                similarity = len(intersection) / len(union) if union else 0
                
                if similarity > 0.3:  # 30%相似度阈值
                    current_group_indices.append(j)
                    current_group_tweets.append(other_tweet)
                    processed.add(j)
            
            groups.append((current_group_indices, current_group_tweets))
        
        return groups
    
    def _extract_topics_from_merged_content(self, tweets: List[str]) -> Optional[Dict[str, str]]:
        """
        从合并的推文内容中提取主要话题
        """
        try:
            # 合并内容，限制长度
            merged_content = "\n---\n".join(tweets[:5])  # 最多5条推文
            if len(merged_content) > self.content_merge_threshold:
                merged_content = merged_content[:self.content_merge_threshold] + "..."

            prompt = f"""
Analyze the following related tweets and extract the main topic being discussed:

Tweet content:
{merged_content}

Please identify:
1. topic_name: Main topic name (5-15 words, highlighting the core theme)
2. brief: Brief topic description (20-50 words, explaining topic content and background in English)

IMPORTANT: Both topic_name and brief MUST be in English.

Return format:
{{
  "topic_name": "Topic Name",
  "brief": "Brief Description"
}}
            """

            messages = [
                {"role": "system", "content": "You are a professional social media content analyst skilled in extracting core topics from multiple tweets. Always respond in English."},
                {"role": "user", "content": prompt}
            ]

            response = self._make_request(messages, temperature=0.3, max_tokens=200)

            if response:
                # 解析JSON响应
                import json
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    result = json.loads(json_str)
                    return result

            return None

        except Exception as e:
            self.logger.error(f"合并内容话题提取失败: {e}")
            return None
    
    def _get_cached_response(self, content: str, operation: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的响应
        """
        if not self.enable_response_caching or not self.response_cache:
            return None
            
        cache_key = f"{operation}:{hash(content)}"
        cached_item = self.response_cache.get(cache_key)
        
        if cached_item:
            # 检查是否过期
            from datetime import datetime, timedelta
            if datetime.now() - cached_item['timestamp'] < timedelta(hours=self.cache_ttl_hours):
                return cached_item['result']
            else:
                # 删除过期缓存
                del self.response_cache[cache_key]
        
        return None
    
    def _cache_response(self, content: str, operation: str, result: Dict[str, Any]):
        """
        缓存响应结果
        """
        if not self.enable_response_caching or not self.response_cache:
            return
            
        from datetime import datetime
        cache_key = f"{operation}:{hash(content)}"
        self.response_cache[cache_key] = {
            'result': result,
            'timestamp': datetime.now()
        }
        
        # 限制缓存大小，避免内存溢出
        if len(self.response_cache) > 1000:
            # 删除最旧的20%缓存项
            oldest_keys = sorted(self.response_cache.keys(), 
                               key=lambda k: self.response_cache[k]['timestamp'])[:200]
            for key in oldest_keys:
                del self.response_cache[key]
    
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
                    # 清理响应内容，移除代码块标记
                    cleaned_response = response.strip()
                    if cleaned_response.startswith('```json'):
                        cleaned_response = cleaned_response[7:]  # 移除 ```json
                    if cleaned_response.startswith('```'):
                        cleaned_response = cleaned_response[3:]  # 移除 ```
                    if cleaned_response.endswith('```'):
                        cleaned_response = cleaned_response[:-3]  # 移除结尾的 ```
                    cleaned_response = cleaned_response.strip()

                    # 尝试解析JSON响应
                    result = json.loads(cleaned_response)

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
                    # 清理响应内容，移除代码块标记
                    cleaned_response = response.strip()
                    if cleaned_response.startswith('```json'):
                        cleaned_response = cleaned_response[7:]  # 移除 ```json
                    if cleaned_response.startswith('```'):
                        cleaned_response = cleaned_response[3:]  # 移除 ```
                    if cleaned_response.endswith('```'):
                        cleaned_response = cleaned_response[:-3]  # 移除结尾的 ```
                    cleaned_response = cleaned_response.strip()
                    
                    # 尝试解析JSON响应
                    result = json.loads(cleaned_response)
                    
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
                    # 清理响应内容，移除代码块标记
                    cleaned_response = response.strip()
                    if cleaned_response.startswith('```json'):
                        cleaned_response = cleaned_response[7:]  # 移除 ```json
                    if cleaned_response.startswith('```'):
                        cleaned_response = cleaned_response[3:]  # 移除 ```
                    if cleaned_response.endswith('```'):
                        cleaned_response = cleaned_response[:-3]  # 移除结尾的 ```
                    cleaned_response = cleaned_response.strip()

                    result = json.loads(cleaned_response)
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
                    # 清理响应内容，移除代码块标记
                    cleaned_response = response.strip()
                    if cleaned_response.startswith('```json'):
                        cleaned_response = cleaned_response[7:]  # 移除 ```json
                    if cleaned_response.startswith('```'):
                        cleaned_response = cleaned_response[3:]  # 移除 ```
                    if cleaned_response.endswith('```'):
                        cleaned_response = cleaned_response[:-3]  # 移除结尾的 ```
                    cleaned_response = cleaned_response.strip()
                    
                    # 尝试解析JSON响应
                    result = json.loads(cleaned_response)
                    
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
                    # 清理响应内容，移除代码块标记
                    cleaned_response = response.strip()
                    if cleaned_response.startswith('```json'):
                        cleaned_response = cleaned_response[7:]  # 移除 ```json
                    if cleaned_response.startswith('```'):
                        cleaned_response = cleaned_response[3:]  # 移除 ```
                    if cleaned_response.endswith('```'):
                        cleaned_response = cleaned_response[:-3]  # 移除结尾的 ```
                    cleaned_response = cleaned_response.strip()

                    result = json.loads(cleaned_response)
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

    def extract_token_symbols_from_tweet(self, tweet_content: str) -> Optional[List[str]]:
        """
        从推文中提取加密货币token symbols

        Args:
            tweet_content: 推文内容

        Returns:
            提取的token symbol列表（如["BTC", "ETH"]），如果无法提取则返回None
        """
        try:
            prompt = f"""
            Please analyze the following cryptocurrency-related tweet and extract all mentioned token symbols.

            Tweet content: {tweet_content}

            Please identify:
            1. All cryptocurrency token symbols mentioned (e.g., BTC, ETH, SOL, USDT)
            2. Include symbols with $ prefix (e.g., $BTC, $ETH)
            3. Include full names that can be mapped to symbols (e.g., "Bitcoin" -> BTC, "Ethereum" -> ETH)

            Requirements:
            - Only extract valid cryptocurrency token symbols (2-10 uppercase letters)
            - Exclude common words that look like symbols but are not (e.g., "TO", "FOR", "AND")
            - Return empty list if no valid symbols found
            - Return at most 10 symbols

            Please return in JSON format:
            {{"symbols": ["BTC", "ETH", "SOL"]}}

            If no valid symbols found, return:
            {{"symbols": []}}
            """

            messages = [
                {"role": "system", "content": "You are a professional cryptocurrency analyst skilled in identifying token symbols from social media content."},
                {"role": "user", "content": prompt}
            ]

            response = self._make_request(
                messages=messages,
                temperature=0.1,  # 低温度以获得更确定的结果
                max_tokens=150
            )

            if response:
                try:
                    # 清理响应内容，移除代码块标记
                    cleaned_response = response.strip()
                    if cleaned_response.startswith('```json'):
                        cleaned_response = cleaned_response[7:]  # 移除 ```json
                    if cleaned_response.startswith('```'):
                        cleaned_response = cleaned_response[3:]  # 移除 ```
                    if cleaned_response.endswith('```'):
                        cleaned_response = cleaned_response[:-3]  # 移除结尾的 ```
                    cleaned_response = cleaned_response.strip()

                    # 尝试解析JSON响应
                    result = json.loads(cleaned_response)

                    # 验证返回的数据
                    if isinstance(result, dict) and 'symbols' in result:
                        symbols = result['symbols']

                        if isinstance(symbols, list):
                            # 过滤和标准化symbols
                            filtered_symbols = []
                            for symbol in symbols:
                                if isinstance(symbol, str):
                                    # 移除$前缀并转为大写
                                    clean_symbol = symbol.strip().upper().lstrip('$')
                                    # 验证长度
                                    if 2 <= len(clean_symbol) <= 10:
                                        filtered_symbols.append(clean_symbol)

                            # 去重并限制数量
                            unique_symbols = list(set(filtered_symbols))[:10]

                            if unique_symbols:
                                self.logger.debug(f"提取到token symbols: {unique_symbols}")
                                return unique_symbols
                            else:
                                return None

                except json.JSONDecodeError:
                    self.logger.warning(f"ChatGPT返回的不是有效JSON: {response}")
                    return None

            return None

        except Exception as e:
            self.logger.error(f"提取token symbols失败: {e}")
            return None

    def classify_tweet_announcement(self, tweet_content: str) -> int:
        """
        判断推文是否为重要公告（合作伙伴、社区活动、技术更新）

        Args:
            tweet_content: 推文内容

        Returns:
            1表示是重要公告，0表示不是
        """
        try:
            prompt = f"""
You are given the content of a tweet from the official account of a crypto project.
Your task is to determine whether the tweet falls into one or more of the following categories:

* **key ecosystem partners & collaborations**: announcements about strategic partners, ecosystem alliances, collaborations with other projects or companies.
* **Community space and other events**: announcements about AMA sessions, Twitter Spaces, conferences, hackathons, offline/online meetups, or community-related activities.
* **Major Tech Updates**: announcements about new product releases, protocol upgrades, mainnet/testnet launches, technical milestones, or major software updates.

Tweet content: {tweet_content}

Please analyze the tweet and determine if it matches ANY of the above categories.

Return in JSON format:
{{"is_announcement": true or false, "categories": ["category1", "category2"], "reason": "brief explanation"}}

If the tweet does NOT match any category, return:
{{"is_announcement": false, "categories": [], "reason": "brief explanation"}}
"""

            messages = [
                {"role": "system", "content": "You are a professional crypto content analyst skilled in identifying important announcements from project tweets."},
                {"role": "user", "content": prompt}
            ]

            response = self._make_request(
                messages=messages,
                temperature=0.1,  # 低温度以获得更确定的结果
                max_tokens=200
            )

            if response:
                try:
                    # 清理响应内容，移除代码块标记
                    cleaned_response = response.strip()
                    if cleaned_response.startswith('```json'):
                        cleaned_response = cleaned_response[7:]  # 移除 ```json
                    if cleaned_response.startswith('```'):
                        cleaned_response = cleaned_response[3:]  # 移除 ```
                    if cleaned_response.endswith('```'):
                        cleaned_response = cleaned_response[:-3]  # 移除结尾的 ```
                    cleaned_response = cleaned_response.strip()

                    # 尝试解析JSON响应
                    result = json.loads(cleaned_response)

                    # 验证返回的数据
                    if isinstance(result, dict) and 'is_announcement' in result:
                        is_announcement = result['is_announcement']
                        categories = result.get('categories', [])
                        reason = result.get('reason', '')

                        if is_announcement:
                            self.logger.info(f"识别为重要公告: 类别={categories}, 理由={reason}")
                            return 1
                        else:
                            self.logger.debug(f"非重要公告: {reason}")
                            return 0

                except json.JSONDecodeError:
                    self.logger.warning(f"ChatGPT返回的不是有效JSON: {response}")
                    return 0

            return 0

        except Exception as e:
            self.logger.error(f"判断公告类型失败: {e}")
            return 0

    def summarize_announcement(self, tweet_content: str) -> Optional[str]:
        """
        Generate a concise announcement summary from a tweet (max 50 characters in Chinese or 50 words in English)

        Args:
            tweet_content: Original tweet content

        Returns:
            Concise announcement-style summary, or None if failed
        """
        try:
            prompt = f"""
You are a professional crypto project announcement editor. Your task is to transform the following tweet into a concise, professional announcement summary.

Original tweet: {tweet_content}

Requirements:
1. Rewrite the tweet to sound like an official announcement rather than a casual social media post
2. Keep it concise: maximum 50 characters in Chinese OR 50 words in English
3. Focus on the key announcement content (what is happening, when, who is involved)
4. Use professional and formal tone
5. Remove casual language, emojis, and unnecessary details
6. Preserve important information like dates, partner names, event names, or technical updates

Return ONLY the summary text without any additional explanation or formatting.

Example:
Input: "🎉 Excited to announce our partnership with @ABC! This is huge for our ecosystem! Stay tuned for more details 🚀"
Output: "Partnership announced with ABC to expand ecosystem capabilities"

Now generate the summary:
"""

            messages = [
                {"role": "system", "content": "You are a professional crypto announcement editor skilled in creating concise, formal summaries from social media posts."},
                {"role": "user", "content": prompt}
            ]

            response = self._make_request(
                messages=messages,
                temperature=0.3,  # Moderate temperature for professional yet concise output
                max_tokens=100    # Limit tokens to ensure conciseness
            )

            if response:
                summary = response.strip()

                # Validate length (rough check)
                if len(summary) > 0:
                    self.logger.info(f"Generated announcement summary: {summary[:100]}...")
                    return summary
                else:
                    self.logger.warning("Generated summary is empty")
                    return None

            return None

        except Exception as e:
            self.logger.error(f"Failed to generate announcement summary: {e}")
            return None

    def detect_campaign_announcement(self, tweets_content: List[str]) -> bool:
        """
        检测推文是否包含活动公告关键词

        关键词包括: campaign, airdrop, quest, reward, giveaway

        Args:
            tweets_content: 推文内容列表

        Returns:
            是否为活动公告
        """
        try:
            # 合并推文内容
            combined_content = "\n".join(tweets_content[:10])  # 限制推文数量

            prompt = f"""
            Analyze the following tweets and determine if they contain campaign/event announcements.

            Key indicators of campaign announcements include:
            - campaign
            - airdrop
            - quest
            - reward
            - giveaway

            Also look for related terms like:
            - token distribution
            - community rewards
            - participation incentives
            - bounty program
            - contest
            - prize

            Tweets content:
            {combined_content}

            Task: Determine if these tweets announce or discuss a campaign, airdrop, quest, reward program, or giveaway.

            Return ONLY "true" if it's a campaign announcement, or "false" if it's not.
            Return a single word without any additional explanation.
            """

            messages = [
                {"role": "system", "content": "You are a cryptocurrency campaign and airdrop detection expert. Analyze tweets to identify campaign announcements accurately."},
                {"role": "user", "content": prompt}
            ]

            response = self._make_request(
                messages=messages,
                temperature=0.1,  # Low temperature for consistent detection
                max_tokens=10
            )

            if response:
                result = response.strip().lower()
                is_campaign = result == "true" or "true" in result

                self.logger.info(f"Campaign detection result: {is_campaign}")
                return is_campaign

            return False

        except Exception as e:
            self.logger.error(f"Failed to detect campaign announcement: {e}")
            return False

    def generate_campaign_summary(self, project_info: Dict[str, Any],
                                 tweets_content: List[str]) -> Optional[str]:
        """
        生成活动公告摘要（英文提示词）

        Args:
            project_info: 项目基本信息
            tweets_content: 相关推文内容列表

        Returns:
            活动摘要文本
        """
        try:
            # 合并推文内容
            tweets_sample = tweets_content[:10]
            tweets_text = "\n".join([f"- {tweet}" for tweet in tweets_sample])

            prompt = f"""
            Generate a professional campaign announcement summary for the cryptocurrency project.

            Project Information:
            - Name: {project_info.get('name', 'Unknown')}
            - Symbol: {project_info.get('symbol', 'Unknown')}
            - Category: {project_info.get('category', 'Unknown')}

            Related Campaign Tweets:
            {tweets_text}

            Please provide a comprehensive campaign summary including:
            1. Campaign Type: Specify if it's an airdrop, quest, reward program, giveaway, or other campaign type
            2. Key Details: What participants need to do, eligibility criteria, rewards offered
            3. Timeline: Start date, end date, or duration if mentioned
            4. Requirements: Specific actions required (follow, retweet, hold tokens, complete tasks, etc.)
            5. Reward Distribution: How and when rewards will be distributed

            Requirements:
            - Professional and clear tone
            - 100-150 words
            - Focus on actionable information for potential participants
            - Highlight important dates and requirements
            - Use English for the summary

            Return ONLY the summary text without any additional formatting or labels.
            """

            messages = [
                {"role": "system", "content": "You are a professional cryptocurrency campaign analyst skilled in summarizing campaign announcements clearly and concisely."},
                {"role": "user", "content": prompt}
            ]

            response = self._make_request(
                messages=messages,
                temperature=0.3,
                max_tokens=300
            )

            if response:
                summary = response.strip()

                if len(summary) > 0:
                    self.logger.info(f"Generated campaign summary: {summary[:100]}...")
                    return summary
                else:
                    self.logger.warning("Generated campaign summary is empty")
                    return None

            return None

        except Exception as e:
            self.logger.error(f"Failed to generate campaign summary: {e}")
            return None

    def extract_activity_structured_data(self, tweet_text: str, tweet_url: str,
                                         tweet_time: str) -> Optional[Dict[str, str]]:
        """
        从推文中提取结构化的活动数据（新JSON格式）

        Args:
            tweet_text: 推文内容（full_text）
            tweet_url: 推文链接
            tweet_time: 推文时间

        Returns:
            结构化的活动数据字典，包含以下字段：
            - title: 活动标题（5个词以内）
            - status: 活动状态（默认"Active"）
            - summary: 活动摘要（20个词以内）
            - time: 推文时间
            - url: 推文链接
        """
        try:
            prompt = f"""
            Extract and structure campaign/activity information from this tweet into JSON format.

            Tweet Content:
            {tweet_text}

            Task: Extract the following information and return ONLY a valid JSON object:
            {{
                "title": "Activity title in 5 words or less",
                "status": "Active",
                "summary": "Activity summary in 20 words or less",
                "time": "{tweet_time}",
                "url": "{tweet_url}"
            }}

            Requirements:
            1. title: Create a concise title (max 5 words) that captures the campaign type and project
            2. status: Always set to "Active" for current activities
            3. summary: Provide a brief summary (max 20 words) covering key participation details
            4. time: Use the provided tweet time as-is
            5. url: Use the provided tweet URL as-is

            Important:
            - Return ONLY the JSON object, no additional text
            - All text should be in English
            - Keep title and summary concise and clear
            - Focus on actionable information (what, how, rewards)

            Return the JSON object:
            """

            messages = [
                {"role": "system", "content": "You are a data extraction specialist. Extract campaign information and return valid JSON only."},
                {"role": "user", "content": prompt}
            ]

            response = self._make_request(
                messages=messages,
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=200
            )

            if response:
                # Parse JSON response
                import json
                try:
                    # Clean response (remove markdown code blocks if present)
                    cleaned_response = response.strip()
                    if cleaned_response.startswith('```'):
                        # Remove markdown code blocks
                        lines = cleaned_response.split('\n')
                        cleaned_response = '\n'.join([l for l in lines if not l.startswith('```')])

                    activity_data = json.loads(cleaned_response.strip())

                    # Validate required fields
                    required_fields = ['title', 'status', 'summary', 'time', 'url']
                    if all(field in activity_data for field in required_fields):
                        self.logger.info(f"Extracted activity data: {activity_data['title']}")
                        return activity_data
                    else:
                        self.logger.warning(f"Missing required fields in activity data: {activity_data}")
                        return None

                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON response: {e}")
                    self.logger.error(f"Response was: {response}")
                    return None

            return None

        except Exception as e:
            self.logger.error(f"Failed to extract activity structured data: {e}")
            return None


# 全局ChatGPT客户端实例
chatgpt_client = ChatGPTClient() 