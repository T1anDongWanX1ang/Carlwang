#!/usr/bin/env python3
"""
用户语言检测器
根据用户的推文内容、个人资料描述等信息判断用户主要使用的语言
"""
import re
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta


class LanguageDetector:
    """用户语言检测器"""
    
    def __init__(self, db_manager=None):
        """
        初始化语言检测器
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        
        # 中文字符范围（Unicode）
        self.chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
        # 英文字符范围（字母）
        self.english_pattern = re.compile(r'[a-zA-Z]')
        # 有效字符范围（用于计算比例）- 只包含字母和中文字符
        self.valid_chars_pattern = re.compile(r'[a-zA-Z\u4e00-\u9fff]')
    
    def detect_user_language(self, user_id: str, 
                           user_description: str = None,
                           recent_days: int = 15,
                           min_tweets: int = 3) -> str:
        """
        检测用户的主要语言
        
        Args:
            user_id: 用户ID
            user_description: 用户描述信息（可选）
            recent_days: 分析最近多少天的推文
            min_tweets: 最少需要分析的推文数量
            
        Returns:
            语言类型："English" 或 "Chinese"
        """
        try:
            self.logger.info(f"开始检测用户语言: {user_id}")
            
            # 1. 获取用户最近的推文
            tweets = self._get_user_recent_tweets(user_id, recent_days)
            
            if len(tweets) < min_tweets:
                self.logger.warning(f"用户 {user_id} 推文数量不足({len(tweets)})，尝试使用描述信息")
                # 如果推文不足，使用用户描述信息
                if user_description:
                    return self._detect_text_language(user_description)
                else:
                    self.logger.warning(f"用户 {user_id} 没有足够信息，默认返回English")
                    return "English"
            
            # 2. 分析推文语言
            total_chinese_ratio = 0.0
            valid_tweets = 0
            
            for tweet in tweets:
                text = tweet.get('full_text', '')
                if text and len(text.strip()) > 10:  # 至少10个字符
                    ratio = self._calculate_chinese_ratio(text)
                    total_chinese_ratio += ratio
                    valid_tweets += 1
            
            if valid_tweets == 0:
                self.logger.warning(f"用户 {user_id} 没有有效推文，默认返回English")
                return "English"
            
            # 3. 计算平均中文比例
            avg_chinese_ratio = total_chinese_ratio / valid_tweets
            
            # 4. 结合用户描述信息调整权重
            description_weight = 0.2
            if user_description:
                desc_chinese_ratio = self._calculate_chinese_ratio(user_description)
                avg_chinese_ratio = (avg_chinese_ratio * (1 - description_weight) + 
                                   desc_chinese_ratio * description_weight)
            
            # 5. 判断语言类型
            language = "Chinese" if avg_chinese_ratio > 0.3 else "English"
            
            self.logger.info(f"用户 {user_id} 语言检测结果: {language} (中文比例: {avg_chinese_ratio:.2f})")
            return language
            
        except Exception as e:
            self.logger.error(f"用户语言检测失败: {user_id}, 错误: {e}")
            return "English"  # 默认返回English
    
    def _get_user_recent_tweets(self, user_id: str, recent_days: int) -> List[Dict[str, Any]]:
        """
        获取用户最近的推文
        
        Args:
            user_id: 用户ID
            recent_days: 最近天数
            
        Returns:
            推文列表
        """
        if not self.db_manager:
            return []
        
        try:
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(days=recent_days)
            
            sql = """
            SELECT full_text, created_at_datetime
            FROM twitter_tweet
            WHERE kol_id = %s
            AND created_at_datetime >= %s
            AND created_at_datetime <= %s
            AND full_text IS NOT NULL
            AND LENGTH(full_text) > 10
            ORDER BY created_at_datetime DESC
            LIMIT 20
            """
            
            return self.db_manager.execute_query(sql, [user_id, start_time, end_time])
            
        except Exception as e:
            self.logger.error(f"获取用户推文失败: {user_id}, 错误: {e}")
            return []
    
    def _detect_text_language(self, text: str) -> str:
        """
        检测单个文本的语言
        
        Args:
            text: 文本内容
            
        Returns:
            语言类型："English" 或 "Chinese"
        """
        if not text:
            return "English"
        
        chinese_ratio = self._calculate_chinese_ratio(text)
        return "Chinese" if chinese_ratio > 0.3 else "English"
    
    def _calculate_chinese_ratio(self, text: str) -> float:
        """
        计算文本中中文字符的比例
        
        Args:
            text: 文本内容
            
        Returns:
            中文字符比例 (0.0-1.0)
        """
        if not text:
            return 0.0
        
        try:
            # 计算中文字符数量
            chinese_chars = len(self.chinese_pattern.findall(text))
            
            # 计算有效字符总数（字母+数字+中文）
            valid_chars = len(self.valid_chars_pattern.findall(text))
            
            if valid_chars == 0:
                return 0.0
            
            return chinese_chars / valid_chars
            
        except Exception as e:
            self.logger.warning(f"计算中文比例失败: {e}")
            return 0.0
    
    def batch_detect_user_languages(self, user_ids: List[str]) -> Dict[str, str]:
        """
        批量检测用户语言
        
        Args:
            user_ids: 用户ID列表
            
        Returns:
            用户ID到语言类型的映射
        """
        results = {}
        
        for user_id in user_ids:
            try:
                language = self.detect_user_language(user_id)
                results[user_id] = language
                
            except Exception as e:
                self.logger.error(f"批量检测用户语言失败: {user_id}, 错误: {e}")
                results[user_id] = "English"  # 默认值
        
        return results
    
    def detect_with_ai_fallback(self, user_id: str, 
                               user_description: str = None,
                               chatgpt_client=None) -> str:
        """
        使用AI作为fallback的语言检测
        
        Args:
            user_id: 用户ID
            user_description: 用户描述
            chatgpt_client: ChatGPT客户端实例
            
        Returns:
            语言类型
        """
        try:
            # 首先使用规则方法
            language = self.detect_user_language(user_id, user_description)
            
            # 如果置信度不高且有AI客户端，使用AI辅助判断
            if chatgpt_client and self._should_use_ai_fallback(user_id):
                ai_language = self._detect_with_ai(user_id, user_description, chatgpt_client)
                if ai_language:
                    self.logger.info(f"用户 {user_id} 使用AI检测结果: {ai_language}")
                    return ai_language
            
            return language
            
        except Exception as e:
            self.logger.error(f"AI辅助语言检测失败: {user_id}, 错误: {e}")
            return self.detect_user_language(user_id, user_description)
    
    def _should_use_ai_fallback(self, user_id: str) -> bool:
        """
        判断是否需要使用AI辅助判断
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否需要AI辅助
        """
        try:
            # 获取用户推文，如果推文太少或者语言特征不明显，使用AI
            tweets = self._get_user_recent_tweets(user_id, 30)
            
            if len(tweets) < 5:
                return True
                
            # 计算语言置信度
            chinese_ratios = []
            for tweet in tweets:
                text = tweet.get('full_text', '')
                if text and len(text.strip()) > 10:
                    ratio = self._calculate_chinese_ratio(text)
                    chinese_ratios.append(ratio)
            
            if not chinese_ratios:
                return True
            
            avg_ratio = sum(chinese_ratios) / len(chinese_ratios)
            
            # 如果中文比例在0.2-0.4之间，说明不够明确，需要AI辅助
            return 0.2 <= avg_ratio <= 0.4
            
        except Exception:
            return False
    
    def _detect_with_ai(self, user_id: str, user_description: str, 
                       chatgpt_client) -> Optional[str]:
        """
        使用AI检测用户语言
        
        Args:
            user_id: 用户ID
            user_description: 用户描述
            chatgpt_client: ChatGPT客户端
            
        Returns:
            AI检测的语言结果
        """
        try:
            # 获取用户最近推文
            tweets = self._get_user_recent_tweets(user_id, 15)
            
            # 构建分析文本
            analysis_text = ""
            if user_description:
                analysis_text += f"用户描述: {user_description}\n"
            
            if tweets:
                analysis_text += "最近推文:\n"
                for i, tweet in enumerate(tweets[:5]):  # 只取前5条
                    text = tweet.get('full_text', '')
                    if text:
                        analysis_text += f"{i+1}. {text}\n"
            
            if not analysis_text.strip():
                return None
            
            # 使用现有的语言检测方法
            return chatgpt_client._detect_primary_language(analysis_text)
            
        except Exception as e:
            self.logger.error(f"AI语言检测失败: {user_id}, 错误: {e}")
            return None


# 全局实例
language_detector = None

def get_language_detector(db_manager=None):
    """
    获取全局语言检测器实例
    
    Args:
        db_manager: 数据库管理器
        
    Returns:
        LanguageDetector实例
    """
    global language_detector
    if language_detector is None:
        language_detector = LanguageDetector(db_manager)
    return language_detector