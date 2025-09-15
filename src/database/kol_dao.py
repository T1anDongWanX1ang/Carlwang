"""
KOL数据访问对象 (Data Access Object)
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from .connection import db_manager
from ..models.kol import KOL


class KolDAO:
    """KOL数据访问对象"""
    
    def __init__(self):
        """初始化DAO"""
        self.db_manager = db_manager
        self.table_name = self.db_manager.db_config.get('tables', {}).get('kol', 'kols')
        self.logger = logging.getLogger(__name__)
    
    def insert_kol(self, kol: KOL) -> bool:
        """
        插入单条KOL数据
        
        Args:
            kol: KOL对象
            
        Returns:
            是否插入成功
        """
        if not kol.validate():
            self.logger.error(f"KOL数据验证失败: {kol}")
            return False
        
        try:
            sql = f"""
            INSERT INTO {self.table_name} (
                kol_id, type, tag, influence_score, influence_score_history,
                call_increase_1h, call_increase_24h, call_increase_3d, call_increase_7d,
                sentiment, sentiment_history, summary, trust_rating, is_kol100,
                last_updated, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            kol_data = kol.to_dict()
            params = (
                kol_data['kol_id'],
                kol_data['type'],
                kol_data['tag'],
                kol_data['influence_score'],
                kol_data['influence_score_history'],
                kol_data['call_increase_1h'],
                kol_data['call_increase_24h'],
                kol_data['call_increase_3d'],
                kol_data['call_increase_7d'],
                kol_data['sentiment'],
                kol_data['sentiment_history'],
                kol_data['summary'],
                kol_data['trust_rating'],
                kol_data['is_kol100'],
                kol_data['last_updated'],
                kol_data['created_at']
            )
            
            affected_rows = self.db_manager.execute_update(sql, params)
            success = affected_rows > 0
            
            if success:
                self.logger.info(f"KOL插入成功: {kol.kol_id}")
            else:
                self.logger.warning(f"KOL插入失败: {kol.kol_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"插入KOL数据失败: {kol.kol_id}, 错误: {e}")
            return False
    
    def upsert_kol(self, kol: KOL) -> bool:
        """
        插入或更新KOL数据
        
        Args:
            kol: KOL对象
            
        Returns:
            是否操作成功
        """
        if not kol.validate():
            self.logger.error(f"KOL数据验证失败: {kol}")
            return False
        
        try:
            # 先尝试查找现有KOL
            existing_kol = self.get_kol_by_id(kol.kol_id)
            
            if existing_kol:
                # 更新现有KOL
                sql = f"""
                UPDATE {self.table_name} SET
                    type = %s,
                    tag = %s,
                    influence_score = %s,
                    influence_score_history = %s,
                    call_increase_1h = %s,
                    call_increase_24h = %s,
                    call_increase_3d = %s,
                    call_increase_7d = %s,
                    sentiment = %s,
                    sentiment_history = %s,
                    summary = %s,
                    trust_rating = %s,
                    is_kol100 = %s,
                    last_updated = %s
                WHERE kol_id = %s
                """
                
                kol_data = kol.to_dict()
                params = (
                    kol_data['type'],
                    kol_data['tag'],
                    kol_data['influence_score'],
                    kol_data['influence_score_history'],
                    kol_data['call_increase_1h'],
                    kol_data['call_increase_24h'],
                    kol_data['call_increase_3d'],
                    kol_data['call_increase_7d'],
                    kol_data['sentiment'],
                    kol_data['sentiment_history'],
                    kol_data['summary'],
                    kol_data['trust_rating'],
                    kol_data['is_kol100'],
                    kol_data['last_updated'],
                    kol_data['kol_id']
                )
                
                affected_rows = self.db_manager.execute_update(sql, params)
                success = affected_rows > 0
                
                if success:
                    self.logger.info(f"KOL更新成功: {kol.kol_id}")
                else:
                    self.logger.warning(f"KOL更新失败: {kol.kol_id}")
            else:
                # 插入新KOL
                success = self.insert_kol(kol)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Upsert KOL数据失败: {kol.kol_id}, 错误: {e}")
            return False
    
    def batch_upsert_kols(self, kols: List[KOL]) -> int:
        """
        批量插入或更新KOL数据
        
        Args:
            kols: KOL对象列表
            
        Returns:
            成功操作的数量
        """
        if not kols:
            return 0
        
        # 过滤有效的KOL
        valid_kols = [kol for kol in kols if kol.validate()]
        if len(valid_kols) != len(kols):
            self.logger.warning(f"过滤掉 {len(kols) - len(valid_kols)} 条无效KOL")
        
        if not valid_kols:
            return 0
        
        success_count = 0
        for kol in valid_kols:
            try:
                if self.upsert_kol(kol):
                    success_count += 1
            except Exception as e:
                self.logger.error(f"批量upsert KOL失败: {kol.kol_id}, 错误: {e}")
                continue
        
        self.logger.info(f"批量upsert KOL成功: {success_count}/{len(valid_kols)} 条数据")
        return success_count
    
    def get_kol_by_id(self, kol_id: str) -> Optional[KOL]:
        """
        根据ID获取KOL
        
        Args:
            kol_id: KOL ID
            
        Returns:
            KOL对象或None
        """
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE kol_id = %s"
            results = self.db_manager.execute_query(sql, (kol_id,))
            
            if results:
                return KOL.from_dict(results[0])
            return None
            
        except Exception as e:
            self.logger.error(f"查询KOL失败: {kol_id}, 错误: {e}")
            return None
    
    def get_kols_by_type(self, kol_type: str, limit: int = 50) -> List[KOL]:
        """
        根据类型获取KOL
        
        Args:
            kol_type: KOL类型
            limit: 限制数量
            
        Returns:
            KOL列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE type = %s 
            ORDER BY influence_score DESC 
            LIMIT %s
            """
            results = self.db_manager.execute_query(sql, (kol_type, limit))
            
            return [KOL.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"按类型查询KOL失败: {kol_type}, 错误: {e}")
            return []
    
    def get_top_kols_by_influence(self, limit: int = 20) -> List[KOL]:
        """
        获取影响力最高的KOL
        
        Args:
            limit: 限制数量
            
        Returns:
            KOL列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            ORDER BY influence_score DESC 
            LIMIT %s
            """
            results = self.db_manager.execute_query(sql, (limit,))
            
            return [KOL.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"查询顶级KOL失败: {e}")
            return []
    
    def get_kol100_list(self) -> List[KOL]:
        """
        获取KOL100列表
        
        Returns:
            KOL100列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE is_kol100 = 1 
            ORDER BY influence_score DESC
            """
            results = self.db_manager.execute_query(sql)
            
            return [KOL.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"查询KOL100失败: {e}")
            return []
    
    def get_kols_by_sentiment(self, sentiment: str, limit: int = 20) -> List[KOL]:
        """
        根据情感倾向获取KOL
        
        Args:
            sentiment: 情感倾向 (bullish/bearish/neutral)
            limit: 限制数量
            
        Returns:
            KOL列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE sentiment = %s 
            ORDER BY influence_score DESC 
            LIMIT %s
            """
            results = self.db_manager.execute_query(sql, (sentiment, limit))
            
            return [KOL.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"按情感查询KOL失败: {sentiment}, 错误: {e}")
            return []
    
    def get_kol_count(self) -> int:
        """
        获取KOL总数
        
        Returns:
            KOL总数
        """
        try:
            sql = f"SELECT COUNT(*) as count FROM {self.table_name}"
            results = self.db_manager.execute_query(sql)
            
            if results:
                return results[0]['count']
            return 0
            
        except Exception as e:
            self.logger.error(f"查询KOL总数失败: {e}")
            return 0
    
    def search_kols(self, keyword: str, limit: int = 20) -> List[KOL]:
        """
        搜索KOL
        
        Args:
            keyword: 搜索关键词
            limit: 限制数量
            
        Returns:
            KOL列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE tag LIKE %s OR summary LIKE %s
            ORDER BY influence_score DESC 
            LIMIT %s
            """
            search_pattern = f"%{keyword}%"
            results = self.db_manager.execute_query(
                sql, 
                (search_pattern, search_pattern, limit)
            )
            
            return [KOL.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"搜索KOL失败: {keyword}, 错误: {e}")
            return []
    
    def delete_kol(self, kol_id: str) -> bool:
        """
        删除KOL
        
        Args:
            kol_id: KOL ID
            
        Returns:
            是否删除成功
        """
        try:
            sql = f"DELETE FROM {self.table_name} WHERE kol_id = %s"
            affected_rows = self.db_manager.execute_update(sql, (kol_id,))
            
            success = affected_rows > 0
            if success:
                self.logger.info(f"KOL删除成功: {kol_id}")
            else:
                self.logger.warning(f"KOL删除失败，可能不存在: {kol_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"删除KOL失败: {kol_id}, 错误: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取KOL统计信息
        
        Returns:
            统计信息字典
        """
        try:
            sql = f"""
            SELECT 
                COUNT(*) as total_count,
                COUNT(CASE WHEN is_kol100 = true THEN 1 END) as kol100_count,
                AVG(influence_score) as avg_influence,
                AVG(trust_rating) as avg_trust
            FROM {self.table_name}
            WHERE influence_score IS NOT NULL
            """
            
            results = self.db_manager.execute_query(sql)
            
            if results:
                stats = results[0]
                return {
                    'total_kols': stats['total_count'] or 0,
                    'kol100_count': stats['kol100_count'] or 0,
                    'average_influence': round(stats['avg_influence'] or 0, 2),
                    'average_trust': round(stats['avg_trust'] or 0, 2)
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"获取KOL统计信息失败: {e}")
            return {}
    
    def get_active_kols(self, min_influence_score: float = 0.0) -> List[Any]:
        """
        获取所有KOL列表（已去除评分限制）
        
        Args:
            min_influence_score: 最低影响力评分（已废弃，保持兼容性）
            
        Returns:
            所有KOL列表
        """
        try:
            sql = f"""
            SELECT kol_id, type, influence_score, trust_rating, is_kol100, summary
            FROM {self.table_name}
            ORDER BY influence_score DESC NULLS LAST, is_kol100 DESC
            """
            
            results = self.db_manager.execute_query(sql)
            
            # 转换为简单的对象以便使用
            active_kols = []
            for row in results:
                kol_data = {
                    'kol_id': row['kol_id'],
                    'user_id': row['kol_id'],  # 使用kol_id作为user_id
                    'type': row['type'],
                    'influence_score': float(row['influence_score']) if row['influence_score'] else 50.0,
                    'trust_rating': float(row['trust_rating']) if row['trust_rating'] else 5.0,
                    'is_kol100': row['is_kol100'],
                    'summary': row['summary']
                }
                active_kols.append(type('KOL', (), kol_data))  # 创建简单的属性对象
            
            self.logger.info(f"找到{len(active_kols)}个KOL（已去除评分限制）")
            return active_kols
            
        except Exception as e:
            self.logger.error(f"获取所有KOL失败: {e}")
            return []
    
    def get_high_quality_kols(self, min_influence_score: float = 30.0, min_trust_rating: float = 5.0) -> List[Any]:
        """
        获取高质量KOL列表（保留原有筛选逻辑，供特殊需求使用）
        
        Args:
            min_influence_score: 最低影响力评分
            min_trust_rating: 最低信任评分
            
        Returns:
            高质量KOL列表
        """
        try:
            sql = f"""
            SELECT kol_id, type, influence_score, trust_rating, is_kol100, summary
            FROM {self.table_name}
            WHERE influence_score >= %s
            AND trust_rating >= %s
            ORDER BY influence_score DESC, is_kol100 DESC
            """
            
            results = self.db_manager.execute_query(sql, (min_influence_score, min_trust_rating))
            
            # 转换为简单的对象以便使用
            high_quality_kols = []
            for row in results:
                kol_data = {
                    'kol_id': row['kol_id'],
                    'user_id': row['kol_id'],  # 使用kol_id作为user_id
                    'type': row['type'],
                    'influence_score': float(row['influence_score']) if row['influence_score'] else 50.0,
                    'trust_rating': float(row['trust_rating']) if row['trust_rating'] else 5.0,
                    'is_kol100': row['is_kol100'],
                    'summary': row['summary']
                }
                high_quality_kols.append(type('KOL', (), kol_data))  # 创建简单的属性对象
            
            self.logger.info(f"找到{len(high_quality_kols)}个高质量KOL（influence>={min_influence_score}, trust>={min_trust_rating}）")
            return high_quality_kols
            
        except Exception as e:
            self.logger.error(f"获取高质量KOL失败: {e}")
            return []


# 全局KOL DAO实例  
kol_dao = KolDAO() 