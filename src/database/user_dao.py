"""
用户数据访问对象 (Data Access Object)
"""
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from .connection import db_manager
from ..models.user import TwitterUser


class UserDAO:
    """用户数据访问对象"""
    
    def __init__(self):
        """初始化DAO"""
        self.db_manager = db_manager
        self.table_name = self.db_manager.db_config.get('tables', {}).get('user', 'twitter_user')
        self.logger = logging.getLogger(__name__)
    
    def insert_user(self, user: TwitterUser) -> bool:
        """
        插入单条用户数据
        
        Args:
            user: 用户对象
            
        Returns:
            是否插入成功
        """
        if not user.validate():
            self.logger.error(f"用户数据验证失败: {user}")
            return False
        
        try:
            # 根据现有表结构调整字段
            sql = f"""
            INSERT INTO {self.table_name} (
                id_str, screen_name, name, description, avatar,
                created_at, followers_count, friends_count, 
                statuses_count, language, update_time
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            user_data = user.to_dict()
            params = (
                user_data['id_str'],
                user_data['screen_name'],
                user_data['name'],
                user_data['description'],
                user_data['avatar'],
                user_data['created_at'],
                user_data['followers_count'],
                user_data['friends_count'],
                user_data['statuses_count'],
                user_data.get('language'),  # 使用get方法以防字段不存在
                user_data['update_time']
            )
            
            affected_rows = self.db_manager.execute_update(sql, params)
            success = affected_rows > 0
            
            if success:
                self.logger.info(f"用户插入成功: {user.id_str}")
            else:
                self.logger.warning(f"用户插入失败: {user.id_str}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"插入用户数据失败: {user.id_str}, 错误: {e}")
            return False
    
    def upsert_user(self, user: TwitterUser) -> bool:
        """
        插入或更新用户数据（Doris Unique Key模型自动处理重复数据）
        
        Args:
            user: 用户对象
            
        Returns:
            是否操作成功
        """
        if not user.validate():
            self.logger.error(f"用户数据验证失败: {user}")
            return False
        
        try:
            # 根据现有表结构调整字段
            sql = f"""
            INSERT INTO {self.table_name} (
                id_str, screen_name, name, description, avatar,
                created_at, followers_count, friends_count, 
                statuses_count, language, update_time
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            user_data = user.to_dict()
            params = (
                user_data['id_str'],
                user_data['screen_name'],
                user_data['name'],
                user_data['description'],
                user_data['avatar'],
                user_data['created_at'],
                user_data['followers_count'],
                user_data['friends_count'],
                user_data['statuses_count'],
                user_data.get('language'),  # 使用get方法以防字段不存在
                user_data['update_time']
            )
            
            affected_rows = self.db_manager.execute_update(sql, params)
            success = affected_rows > 0
            
            if success:
                self.logger.info(f"用户upsert成功: {user.id_str}")
            else:
                self.logger.warning(f"用户upsert失败: {user.id_str}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Upsert用户数据失败: {user.id_str}, 错误: {e}")
            return False
    
    def batch_upsert_users(self, users: List[TwitterUser]) -> int:
        """
        批量插入或更新用户数据
        
        Args:
            users: 用户对象列表
            
        Returns:
            成功操作的数量
        """
        if not users:
            return 0
        
        # 过滤有效的用户
        valid_users = [user for user in users if user.validate()]
        if len(valid_users) != len(users):
            self.logger.warning(f"过滤掉 {len(users) - len(valid_users)} 条无效用户")
        
        if not valid_users:
            return 0
        
        try:
            # 根据现有表结构调整字段
            sql = f"""
            INSERT INTO {self.table_name} (
                id_str, screen_name, name, description, avatar,
                created_at, followers_count, friends_count, 
                statuses_count, language, update_time
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            success_count = 0
            for user in valid_users:
                try:
                    user_data = user.to_dict()
                    params = (
                        user_data['id_str'],
                        user_data['screen_name'],
                        user_data['name'],
                        user_data['description'],
                        user_data['avatar'],
                        user_data['created_at'],
                        user_data['followers_count'],
                        user_data['friends_count'],
                        user_data['statuses_count'],
                        user_data.get('language'),  # 使用get方法以防字段不存在
                        user_data['update_time']
                    )
                    
                    affected_rows = self.db_manager.execute_update(sql, params)
                    if affected_rows > 0:
                        success_count += 1
                        
                except Exception as e:
                    self.logger.error(f"插入用户失败: {user.id_str}, 错误: {e}")
                    continue
            
            self.logger.info(f"批量upsert用户成功: {success_count}/{len(valid_users)} 条数据")
            return success_count
            
        except Exception as e:
            self.logger.error(f"批量upsert用户数据失败: {e}")
            return 0
    
    def get_user_by_id(self, id_str: str) -> Optional[TwitterUser]:
        """
        根据ID获取用户
        
        Args:
            id_str: 用户ID
            
        Returns:
            用户对象或None
        """
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE id_str = %s"
            results = self.db_manager.execute_query(sql, (id_str,))
            
            if results:
                return self._dict_to_user(results[0])
            return None
            
        except Exception as e:
            self.logger.error(f"查询用户失败: {id_str}, 错误: {e}")
            return None
    
    def get_users_by_screen_name(self, screen_name: str) -> List[TwitterUser]:
        """
        根据screen_name获取用户
        
        Args:
            screen_name: 用户screen_name
            
        Returns:
            用户对象列表
        """
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE screen_name = %s"
            results = self.db_manager.execute_query(sql, (screen_name,))
            
            return [self._dict_to_user(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"按screen_name查询用户失败: {screen_name}, 错误: {e}")
            return []
    
    def get_user_count(self) -> int:
        """
        获取用户总数
        
        Returns:
            用户总数
        """
        try:
            sql = f"SELECT COUNT(*) as count FROM {self.table_name}"
            results = self.db_manager.execute_query(sql)
            
            if results:
                return results[0]['count']
            return 0
            
        except Exception as e:
            self.logger.error(f"查询用户总数失败: {e}")
            return 0
    
    def get_top_users_by_followers(self, limit: int = 10) -> List[TwitterUser]:
        """
        获取粉丝数最多的用户
        
        Args:
            limit: 限制数量
            
        Returns:
            用户对象列表
        """
        try:
            sql = f"""
            SELECT * FROM {self.table_name} 
            ORDER BY followers_count DESC 
            LIMIT %s
            """
            results = self.db_manager.execute_query(sql, (limit,))
            
            return [self._dict_to_user(row) for row in results]
            
        except Exception as e:
            self.logger.error(f"查询热门用户失败: {e}")
            return []
    
    def delete_user(self, id_str: str) -> bool:
        """
        删除用户
        
        Args:
            id_str: 用户ID
            
        Returns:
            是否删除成功
        """
        try:
            sql = f"DELETE FROM {self.table_name} WHERE id_str = %s"
            affected_rows = self.db_manager.execute_update(sql, (id_str,))
            
            success = affected_rows > 0
            if success:
                self.logger.info(f"用户删除成功: {id_str}")
            else:
                self.logger.warning(f"用户删除失败，可能不存在: {id_str}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"删除用户失败: {id_str}, 错误: {e}")
            return False
    
    def _dict_to_user(self, data: Dict[str, Any]) -> TwitterUser:
        """
        将数据库查询结果转换为TwitterUser对象
        
        Args:
            data: 数据库查询结果字典
            
        Returns:
            TwitterUser对象
        """
        return TwitterUser(
            id_str=data['id_str'],
            screen_name=data.get('screen_name'),
            name=data.get('name'),
            description=data.get('description'),
            avatar=data.get('avatar'),
            created_at=data.get('created_at'),
            created_at_datetime=None,  # 数据库表中没有此字段
            followers_count=data.get('followers_count', 0),
            friends_count=data.get('friends_count', 0),
            statuses_count=data.get('statuses_count', 0),
            can_dm=False,  # 数据库表中没有此字段，设为默认值
            language=data.get('language'),
            update_time=data.get('update_time')
        )


# 全局DAO实例
user_dao = UserDAO() 