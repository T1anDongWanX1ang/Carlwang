"""
推特引用关系提取器
从推文API数据中提取引用关系
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime


class QuotationExtractor:
    """推特引用关系提取器"""
    
    def __init__(self):
        """初始化提取器"""
        self.logger = logging.getLogger(__name__)
    
    def extract_quotations_from_api_data(self, api_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        从API数据中提取引用关系
        
        Args:
            api_data_list: 推文API原始数据列表
            
        Returns:
            引用关系数据列表
        """
        quotations = []
        
        for api_data in api_data_list:
            try:
                quotation = self._extract_single_quotation(api_data)
                if quotation:
                    quotations.append(quotation)
            except Exception as e:
                self.logger.error(f"提取引用关系失败 (tweet_id: {api_data.get('id_str', 'unknown')}): {e}")
                continue
        
        self.logger.info(f"从 {len(api_data_list)} 条推文数据中提取到 {len(quotations)} 条引用关系")
        return quotations
    
    def _extract_single_quotation(self, api_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从单条推文API数据中提取引用关系
        
        Args:
            api_data: 单条推文的API原始数据
            
        Returns:
            引用关系数据字典，如果不是引用推文则返回None
        """
        try:
            # 检查是否为引用推文
            is_quote_status = api_data.get('is_quote_status', False)
            if not is_quote_status:
                return None
            
            # 检查是否有被引用的推文数据
            quoted_status = api_data.get('quoted_status')
            if not quoted_status or not isinstance(quoted_status, dict):
                self.logger.debug(f"推文 {api_data.get('id_str')} 标记为引用但缺少quoted_status数据")
                return None
            
            # 提取引用推文的基本信息
            twitter_id = api_data.get('id_str')
            user_data = api_data.get('user', {})
            user_id = user_data.get('id_str') if isinstance(user_data, dict) else None
            user_name = user_data.get('screen_name') if isinstance(user_data, dict) else None
            
            # 提取被引用推文的信息
            twitter_quotation_id = quoted_status.get('id_str')
            quoted_user_data = quoted_status.get('user', {})
            user_quotation_id = quoted_user_data.get('id_str') if isinstance(quoted_user_data, dict) else None
            quotations_user_name = quoted_user_data.get('screen_name') if isinstance(quoted_user_data, dict) else None
            
            # 提取创建时间
            created_at_str = api_data.get('created_at')
            created_at = self._parse_twitter_datetime(created_at_str)
            
            # 验证必需字段
            if not all([twitter_id, user_id, user_name, twitter_quotation_id, user_quotation_id, quotations_user_name]):
                missing_fields = []
                if not twitter_id: missing_fields.append('twitter_id')
                if not user_id: missing_fields.append('user_id')
                if not user_name: missing_fields.append('user_name')
                if not twitter_quotation_id: missing_fields.append('twitter_quotation_id')
                if not user_quotation_id: missing_fields.append('user_quotation_id')
                if not quotations_user_name: missing_fields.append('quotations_user_name')
                
                self.logger.warning(f"引用关系数据不完整，缺少字段: {missing_fields}")
                return None
            
            # 构建引用关系数据
            quotation_data = {
                'twitter_id': twitter_id,
                'user_id': user_id,
                'user_name': user_name,
                'twitter_quotation_id': twitter_quotation_id,
                'user_quotation_id': user_quotation_id,
                'quotations_user_name': quotations_user_name,
                'created_at': created_at
            }
            
            self.logger.debug(f"提取引用关系: @{user_name} 引用了 @{quotations_user_name} 的推文")
            return quotation_data
            
        except Exception as e:
            self.logger.error(f"解析引用关系数据异常: {e}")
            return None
    
    def _parse_twitter_datetime(self, date_str: str) -> Optional[datetime]:
        """
        解析Twitter API的日期时间格式
        
        Args:
            date_str: Twitter API返回的日期时间字符串
            
        Returns:
            解析后的datetime对象
        """
        if not date_str:
            return None
        
        try:
            # Twitter API日期格式: "Wed Oct 05 20:11:53 +0000 2016"
            from datetime import datetime
            # 移除时区信息，简化解析
            if '+0000' in date_str:
                date_str = date_str.replace(' +0000', '')
            
            # 解析格式
            return datetime.strptime(date_str, '%a %b %d %H:%M:%S %Y')
            
        except Exception as e:
            self.logger.error(f"解析日期时间失败 '{date_str}': {e}")
            # 返回当前时间作为fallback
            return datetime.now()
    
    def get_quotation_statistics(self, quotations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取引用关系统计信息
        
        Args:
            quotations: 引用关系数据列表
            
        Returns:
            统计信息字典
        """
        if not quotations:
            return {
                'total_quotations': 0,
                'unique_quoters': 0,
                'unique_quoted': 0,
                'top_quoters': [],
                'top_quoted': []
            }
        
        try:
            # 基础统计
            total_quotations = len(quotations)
            unique_quoters = len(set(q['user_id'] for q in quotations))
            unique_quoted = len(set(q['user_quotation_id'] for q in quotations))
            
            # 统计最活跃的引用者
            quoter_counts = {}
            for q in quotations:
                user_id = q['user_id']
                user_name = q['user_name']
                quoter_counts[user_id] = quoter_counts.get(user_id, {'name': user_name, 'count': 0})
                quoter_counts[user_id]['count'] += 1
            
            top_quoters = sorted(
                [{'user_id': uid, 'user_name': data['name'], 'quote_count': data['count']} 
                 for uid, data in quoter_counts.items()],
                key=lambda x: x['quote_count'],
                reverse=True
            )[:10]
            
            # 统计最常被引用的用户
            quoted_counts = {}
            for q in quotations:
                user_id = q['user_quotation_id']
                user_name = q['quotations_user_name']
                quoted_counts[user_id] = quoted_counts.get(user_id, {'name': user_name, 'count': 0})
                quoted_counts[user_id]['count'] += 1
            
            top_quoted = sorted(
                [{'user_id': uid, 'user_name': data['name'], 'quoted_count': data['count']} 
                 for uid, data in quoted_counts.items()],
                key=lambda x: x['quoted_count'],
                reverse=True
            )[:10]
            
            return {
                'total_quotations': total_quotations,
                'unique_quoters': unique_quoters,
                'unique_quoted': unique_quoted,
                'top_quoters': top_quoters,
                'top_quoted': top_quoted
            }
            
        except Exception as e:
            self.logger.error(f"计算引用关系统计失败: {e}")
            return {
                'total_quotations': len(quotations),
                'unique_quoters': 0,
                'unique_quoted': 0,
                'top_quoters': [],
                'top_quoted': []
            }
    
    def filter_valid_quotations(self, quotations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤有效的引用关系数据
        
        Args:
            quotations: 原始引用关系数据列表
            
        Returns:
            过滤后的有效引用关系数据列表
        """
        valid_quotations = []
        required_fields = [
            'twitter_id', 'user_id', 'user_name',
            'twitter_quotation_id', 'user_quotation_id', 'quotations_user_name'
        ]
        
        for quotation in quotations:
            try:
                # 检查必需字段
                if not all(field in quotation and quotation[field] for field in required_fields):
                    missing = [f for f in required_fields if f not in quotation or not quotation[f]]
                    self.logger.debug(f"跳过不完整的引用关系数据，缺少: {missing}")
                    continue
                
                # 检查字段长度（防止数据库字段溢出）
                if len(quotation['user_name']) > 100:
                    quotation['user_name'] = quotation['user_name'][:100]
                if len(quotation['quotations_user_name']) > 100:
                    quotation['quotations_user_name'] = quotation['quotations_user_name'][:100]
                
                # 检查ID格式（应该是数字字符串）
                if not quotation['twitter_id'].isdigit():
                    self.logger.debug(f"跳过无效的推文ID: {quotation['twitter_id']}")
                    continue
                
                if not quotation['twitter_quotation_id'].isdigit():
                    self.logger.debug(f"跳过无效的被引用推文ID: {quotation['twitter_quotation_id']}")
                    continue
                
                # 避免自引用（用户引用自己的推文）
                if quotation['user_id'] == quotation['user_quotation_id']:
                    self.logger.debug(f"跳过自引用: {quotation['user_name']}")
                    continue
                
                valid_quotations.append(quotation)
                
            except Exception as e:
                self.logger.error(f"验证引用关系数据时出错: {e}")
                continue
        
        self.logger.info(f"过滤引用关系数据: {len(quotations)} -> {len(valid_quotations)} 条有效")
        return valid_quotations


# 全局实例
quotation_extractor = QuotationExtractor()