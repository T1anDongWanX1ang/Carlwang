"""
Project数据访问对象 (Data Access Object)
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta

from .connection import db_manager
from ..models.project import Project


class ProjectDAO:
    """Project数据访问对象"""
    
    def __init__(self):
        """初始化DAO"""
        self.db_manager = db_manager
        self.table_name = self.db_manager.db_config.get('tables', {}).get('project', 'twitter_projects')
        self.logger = logging.getLogger(__name__)
    
    def insert_project(self, project: Project) -> bool:
        """
        插入单条项目数据
        
        Args:
            project: Project对象
            
        Returns:
            是否插入成功
        """
        if not project.validate():
            self.logger.error(f"项目数据验证失败: {project}")
            return False
        
        try:
            sql = f"""
            INSERT INTO {self.table_name} (
                project_id, name, symbol, token_address, twitter_id,
                created_at, category, narratives, sentiment_index, sentiment_history,
                popularity, popularity_history, summary, last_updated, update_time
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            project_data = project.to_dict()
            params = (
                project_data['project_id'],
                project_data['name'],
                project_data['symbol'],
                project_data['token_address'],
                project_data['twitter_id'],
                project_data['created_at'],
                project_data['category'],
                project_data['narratives'],
                project_data['sentiment_index'],
                project_data['sentiment_history'],
                project_data['popularity'],
                project_data['popularity_history'],
                project_data['summary'],
                project_data['last_updated'],
                project_data['update_time']
            )
            
            affected_rows = self.db_manager.execute_update(sql, params)
            success = affected_rows > 0
            
            if success:
                self.logger.info(f"项目插入成功: {project.name} ({project.symbol})")
            else:
                self.logger.warning(f"项目插入失败: {project.name}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"插入项目数据失败: {project.name}, 错误: {e}")
            return False
    
    def upsert_project(self, project: Project) -> bool:
        """
        插入或更新项目数据
        
        Args:
            project: Project对象
            
        Returns:
            是否操作成功
        """
        if not project.validate():
            self.logger.error(f"项目数据验证失败: {project}")
            return False
        
        try:
            # 先尝试查找现有项目
            existing_project = self.get_project_by_id(project.project_id)
            
            if existing_project:
                # 更新现有项目
                sql = f"""
                UPDATE {self.table_name} SET
                    name = %s,
                    symbol = %s,
                    token_address = %s,
                    twitter_id = %s,
                    category = %s,
                    narratives = %s,
                    sentiment_index = %s,
                    sentiment_history = %s,
                    popularity = %s,
                    popularity_history = %s,
                    summary = %s,
                    last_updated = %s,
                    update_time = %s
                WHERE project_id = %s
                """
                
                project_data = project.to_dict()
                params = (
                    project_data['name'],
                    project_data['symbol'],
                    project_data['token_address'],
                    project_data['twitter_id'],
                    project_data['category'],
                    project_data['narratives'],
                    project_data['sentiment_index'],
                    project_data['sentiment_history'],
                    project_data['popularity'],
                    project_data['popularity_history'],
                    project_data['summary'],
                    project_data['last_updated'],
                    project_data['update_time'],
                    project_data['project_id']
                )
                
                affected_rows = self.db_manager.execute_update(sql, params)
                success = affected_rows > 0
                
                if success:
                    self.logger.info(f"项目更新成功: {project.name}")
                else:
                    self.logger.warning(f"项目更新失败: {project.name}")
            else:
                # 插入新项目
                success = self.insert_project(project)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Upsert项目数据失败: {project.name}, 错误: {e}")
            return False
    
    def batch_upsert_projects(self, projects: List[Project]) -> int:
        """
        批量插入或更新项目数据
        
        Args:
            projects: Project对象列表
            
        Returns:
            成功操作的数量
        """
        if not projects:
            return 0
        
        # 过滤有效的项目
        valid_projects = [project for project in projects if project.validate()]
        if len(valid_projects) != len(projects):
            self.logger.warning(f"过滤掉 {len(projects) - len(valid_projects)} 条无效项目")
        
        if not valid_projects:
            return 0
        
        success_count = 0
        for project in valid_projects:
            try:
                if self.upsert_project(project):
                    success_count += 1
            except Exception as e:
                self.logger.error(f"批量upsert项目失败: {project.name}, 错误: {e}")
                continue
        
        self.logger.info(f"批量upsert项目成功: {success_count}/{len(valid_projects)} 条数据")
        return success_count
    
    def get_project_by_id(self, project_id: str) -> Optional[Project]:
        """
        根据ID获取项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            Project对象或None
        """
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE project_id = %s"
            results = self.db_manager.execute_query(sql, (project_id,))
            
            if results:
                return Project.from_dict(results[0])
            return None
            
        except Exception as e:
            self.logger.error(f"查询项目失败: {project_id}, 错误: {e}")
            return None
    
    def get_project_by_name(self, name: str) -> Optional[Project]:
        """
        根据项目名称获取项目
        
        Args:
            name: 项目名称
            
        Returns:
            Project对象或None
        """
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE name = %s"
            results = self.db_manager.execute_query(sql, (name,))
            
            if results:
                return Project.from_dict(results[0])
            return None
            
        except Exception as e:
            self.logger.error(f"根据名称查询项目失败: {name}, 错误: {e}")
            return None
    
    def get_project_by_symbol(self, symbol: str) -> Optional[Project]:
        """
        根据代币符号获取项目
        
        Args:
            symbol: 代币符号
            
        Returns:
            Project对象或None
        """
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE symbol = %s"
            results = self.db_manager.execute_query(sql, (symbol,))
            
            if results:
                return Project.from_dict(results[0])
            return None
            
        except Exception as e:
            self.logger.error(f"根据符号查询项目失败: {symbol}, 错误: {e}")
            return None
    
    def get_projects_by_category(self, category: str, limit: int = 50) -> List[Project]:
        """
        根据分类获取项目
        
        Args:
            category: 项目分类
            limit: 限制数量
            
        Returns:
            项目列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE category = %s 
            ORDER BY popularity DESC 
            LIMIT %s
            """
            results = self.db_manager.execute_query(sql, (category, limit))
            
            return [Project.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"按分类查询项目失败: {category}, 错误: {e}")
            return []
    
    def get_hot_projects(self, limit: int = 20) -> List[Project]:
        """
        获取热门项目
        
        Args:
            limit: 限制数量
            
        Returns:
            热门项目列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            ORDER BY popularity DESC 
            LIMIT %s
            """
            results = self.db_manager.execute_query(sql, (limit,))
            
            return [Project.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"查询热门项目失败: {e}")
            return []
    
    def get_trending_projects(self, limit: int = 20) -> List[Project]:
        """
        获取趋势项目（基于情感变化）
        
        Args:
            limit: 限制数量
            
        Returns:
            趋势项目列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE sentiment_index > 60 
            ORDER BY last_updated DESC 
            LIMIT %s
            """
            results = self.db_manager.execute_query(sql, (limit,))
            
            return [Project.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"查询趋势项目失败: {e}")
            return []
    
    def get_projects_by_sentiment_range(self, min_sentiment: float, max_sentiment: float, 
                                       limit: int = 50) -> List[Project]:
        """
        根据情感范围获取项目
        
        Args:
            min_sentiment: 最小情感分数
            max_sentiment: 最大情感分数
            limit: 限制数量
            
        Returns:
            项目列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE sentiment_index BETWEEN %s AND %s 
            ORDER BY sentiment_index DESC 
            LIMIT %s
            """
            results = self.db_manager.execute_query(sql, (min_sentiment, max_sentiment, limit))
            
            return [Project.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"按情感范围查询项目失败: {e}")
            return []
    
    def search_projects(self, keyword: str, limit: int = 20) -> List[Project]:
        """
        搜索项目
        
        Args:
            keyword: 搜索关键词
            limit: 限制数量
            
        Returns:
            项目列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE name LIKE %s OR symbol LIKE %s OR category LIKE %s
            ORDER BY popularity DESC 
            LIMIT %s
            """
            search_pattern = f"%{keyword}%"
            results = self.db_manager.execute_query(
                sql, 
                (search_pattern, search_pattern, search_pattern, limit)
            )
            
            return [Project.from_dict(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"搜索项目失败: {keyword}, 错误: {e}")
            return []
    
    def get_project_count(self) -> int:
        """
        获取项目总数
        
        Returns:
            项目总数
        """
        try:
            sql = f"SELECT COUNT(*) as count FROM {self.table_name}"
            results = self.db_manager.execute_query(sql)
            
            if results:
                return results[0]['count']
            return 0
            
        except Exception as e:
            self.logger.error(f"查询项目总数失败: {e}")
            return 0
    
    def delete_project(self, project_id: str) -> bool:
        """
        删除项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            是否删除成功
        """
        try:
            sql = f"DELETE FROM {self.table_name} WHERE project_id = %s"
            affected_rows = self.db_manager.execute_update(sql, (project_id,))
            
            success = affected_rows > 0
            if success:
                self.logger.info(f"项目删除成功: {project_id}")
            else:
                self.logger.warning(f"项目删除失败，可能不存在: {project_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"删除项目失败: {project_id}, 错误: {e}")
            return False


# 全局DAO实例
project_dao = ProjectDAO() 