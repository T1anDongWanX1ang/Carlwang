#!/usr/bin/env python3
"""
用户语言检测集成工具
用于在用户数据处理流程中自动添加语言检测功能
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .language_detector import get_language_detector
from ..models.user import TwitterUser
from ..api.chatgpt_client import ChatGPTClient


class UserLanguageIntegration:
    """用户语言检测集成类"""
    
    def __init__(self, db_manager=None, chatgpt_client: Optional[ChatGPTClient] = None):
        """
        初始化集成工具
        
        Args:
            db_manager: 数据库管理器
            chatgpt_client: ChatGPT客户端（可选，用于AI辅助检测）
        """
        self.db_manager = db_manager
        self.chatgpt_client = chatgpt_client
        self.language_detector = get_language_detector(db_manager)
        self.logger = logging.getLogger(__name__)
    
    def enhance_user_with_language(self, user: TwitterUser, 
                                 use_ai_fallback: bool = False) -> TwitterUser:
        """
        为用户对象添加语言检测
        
        Args:
            user: 用户对象
            use_ai_fallback: 是否使用AI辅助检测
            
        Returns:
            增强后的用户对象（包含language字段）
        """
        try:
            if user.language:
                # 如果已经有语言信息，直接返回
                return user
            
            if use_ai_fallback and self.chatgpt_client:
                # 使用AI辅助检测
                detected_language = self.language_detector.detect_with_ai_fallback(
                    user_id=user.id_str,
                    user_description=user.description,
                    chatgpt_client=self.chatgpt_client
                )
            else:
                # 使用规则方法检测
                detected_language = self.language_detector.detect_user_language(
                    user_id=user.id_str,
                    user_description=user.description
                )
            
            # 更新用户对象
            user.language = detected_language
            
            self.logger.info(f"用户 {user.screen_name}({user.id_str}) 语言检测完成: {detected_language}")
            return user
            
        except Exception as e:
            self.logger.error(f"用户语言检测失败: {user.id_str}, 错误: {e}")
            # 默认设置为English
            user.language = "English"
            return user
    
    def enhance_users_batch(self, users: List[TwitterUser], 
                           use_ai_fallback: bool = False) -> List[TwitterUser]:
        """
        批量为用户添加语言检测
        
        Args:
            users: 用户对象列表
            use_ai_fallback: 是否使用AI辅助检测
            
        Returns:
            增强后的用户对象列表
        """
        enhanced_users = []
        
        for user in users:
            try:
                enhanced_user = self.enhance_user_with_language(user, use_ai_fallback)
                enhanced_users.append(enhanced_user)
            except Exception as e:
                self.logger.error(f"批量语言检测失败: {user.id_str}, 错误: {e}")
                # 添加默认语言
                user.language = "English"
                enhanced_users.append(user)
        
        return enhanced_users
    
    def update_existing_users_language(self, user_ids: List[str], 
                                     force_update: bool = False) -> Dict[str, str]:
        """
        更新现有用户的语言信息
        
        Args:
            user_ids: 用户ID列表
            force_update: 是否强制更新（即使已有语言信息）
            
        Returns:
            用户ID到语言的映射
        """
        if not self.db_manager:
            raise ValueError("需要数据库管理器来更新现有用户")
        
        results = {}
        
        for user_id in user_ids:
            try:
                # 检查用户是否已有语言信息
                if not force_update:
                    check_sql = "SELECT language FROM twitter_user WHERE id_str = %s"
                    existing = self.db_manager.execute_query(check_sql, [user_id])
                    
                    if existing and existing[0]['language']:
                        results[user_id] = existing[0]['language']
                        continue
                
                # 获取用户描述
                desc_sql = "SELECT description FROM twitter_user WHERE id_str = %s"
                desc_result = self.db_manager.execute_query(desc_sql, [user_id])
                user_description = desc_result[0]['description'] if desc_result else ""
                
                # 检测语言
                detected_language = self.language_detector.detect_user_language(
                    user_id=user_id,
                    user_description=user_description
                )
                
                # 更新数据库
                update_sql = """
                UPDATE twitter_user 
                SET language = %s, update_time = %s 
                WHERE id_str = %s
                """
                
                affected_rows = self.db_manager.execute_update(
                    update_sql, 
                    [detected_language, datetime.now(), user_id]
                )
                
                if affected_rows > 0:
                    results[user_id] = detected_language
                    self.logger.info(f"用户 {user_id} 语言更新成功: {detected_language}")
                else:
                    self.logger.warning(f"用户 {user_id} 语言更新失败")
                    results[user_id] = "English"  # 默认值
                
            except Exception as e:
                self.logger.error(f"更新用户语言失败: {user_id}, 错误: {e}")
                results[user_id] = "English"  # 默认值
        
        return results
    
    def get_language_statistics(self) -> Dict[str, Any]:
        """
        获取语言分布统计
        
        Returns:
            语言统计信息
        """
        if not self.db_manager:
            raise ValueError("需要数据库管理器来获取统计信息")
        
        try:
            # 总体统计
            total_sql = """
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN language IS NOT NULL THEN 1 END) as users_with_language,
                COUNT(CASE WHEN language IS NULL THEN 1 END) as users_without_language
            FROM twitter_user
            """
            
            total_stats = self.db_manager.execute_query(total_sql)[0]
            
            # 语言分布
            language_sql = """
            SELECT 
                language,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / %s, 2) as percentage
            FROM twitter_user
            WHERE language IS NOT NULL
            GROUP BY language
            ORDER BY count DESC
            """
            
            language_stats = self.db_manager.execute_query(
                language_sql, 
                [total_stats['users_with_language']]
            )
            
            return {
                'total_users': total_stats['total_users'],
                'users_with_language': total_stats['users_with_language'],
                'users_without_language': total_stats['users_without_language'],
                'completion_rate': round(
                    total_stats['users_with_language'] / total_stats['total_users'] * 100, 2
                ) if total_stats['total_users'] > 0 else 0,
                'language_distribution': language_stats
            }
            
        except Exception as e:
            self.logger.error(f"获取语言统计失败: {e}")
            return {}
    
    def validate_language_detection(self, sample_size: int = 50) -> Dict[str, Any]:
        """
        验证语言检测的准确性
        
        Args:
            sample_size: 验证样本大小
            
        Returns:
            验证结果
        """
        if not self.db_manager:
            raise ValueError("需要数据库管理器来进行验证")
        
        try:
            # 获取有语言标记且有推文的用户样本
            sample_sql = """
            SELECT u.id_str, u.screen_name, u.description, u.language,
                   COUNT(t.id_str) as tweet_count
            FROM twitter_user u
            INNER JOIN twitter_tweet t ON u.id_str = t.kol_id
            WHERE u.language IS NOT NULL
            AND t.full_text IS NOT NULL
            GROUP BY u.id_str, u.screen_name, u.description, u.language
            HAVING tweet_count >= 5
            ORDER BY RAND()
            LIMIT %s
            """
            
            samples = self.db_manager.execute_query(sample_sql, [sample_size])
            
            validation_results = {
                'total_samples': len(samples),
                'consistent_detections': 0,
                'inconsistent_detections': 0,
                'samples': []
            }
            
            for sample in samples:
                user_id = sample['id_str']
                stored_language = sample['language']
                
                # 重新检测语言
                new_detection = self.language_detector.detect_user_language(
                    user_id=user_id,
                    user_description=sample.get('description', '')
                )
                
                is_consistent = stored_language == new_detection
                
                if is_consistent:
                    validation_results['consistent_detections'] += 1
                else:
                    validation_results['inconsistent_detections'] += 1
                
                validation_results['samples'].append({
                    'user_id': user_id,
                    'screen_name': sample['screen_name'],
                    'stored_language': stored_language,
                    'new_detection': new_detection,
                    'is_consistent': is_consistent,
                    'tweet_count': sample['tweet_count']
                })
            
            # 计算一致性率
            if validation_results['total_samples'] > 0:
                validation_results['consistency_rate'] = round(
                    validation_results['consistent_detections'] / validation_results['total_samples'] * 100, 2
                )
            else:
                validation_results['consistency_rate'] = 0
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"语言检测验证失败: {e}")
            return {}


# 全局实例
user_language_integration = None

def get_user_language_integration(db_manager=None, chatgpt_client=None):
    """
    获取全局用户语言集成实例
    
    Args:
        db_manager: 数据库管理器
        chatgpt_client: ChatGPT客户端
        
    Returns:
        UserLanguageIntegration实例
    """
    global user_language_integration
    if user_language_integration is None:
        user_language_integration = UserLanguageIntegration(db_manager, chatgpt_client)
    return user_language_integration