"""
数据库连接管理模块
"""
import pymysql
from pymysql import Connection
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Generator
import threading
import time
from queue import Queue, Empty
import logging

from ..utils.config_manager import config


class DatabaseConnectionPool:
    """数据库连接池"""
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        初始化连接池
        
        Args:
            db_config: 数据库配置
        """
        self.db_config = db_config
        self.pool_config = db_config.get('connection_pool', {})
        
        self.max_connections = self.pool_config.get('max_connections', 10)
        self.min_connections = self.pool_config.get('min_connections', 1)
        self.connection_timeout = self.pool_config.get('connection_timeout', 30)
        self.idle_timeout = self.pool_config.get('idle_timeout', 600)
        
        self._pool = Queue(maxsize=self.max_connections)
        self._active_connections = 0
        self._lock = threading.Lock()
        
        self.logger = logging.getLogger(__name__)
        
        # 初始化最小连接数
        self._initialize_pool()
    
    def _initialize_pool(self):
        """初始化连接池"""
        for _ in range(self.min_connections):
            try:
                conn = self._create_connection()
                self._pool.put((conn, time.time()))
                self._active_connections += 1
            except Exception as e:
                self.logger.error(f"初始化连接池失败: {e}")
                break
    
    def _create_connection(self) -> Connection:
        """
        创建新的数据库连接
        
        Returns:
            数据库连接对象
        """
        try:
            connection_params = {
                'host': self.db_config['host'],
                'port': self.db_config['port'],
                'user': self.db_config['username'],
                'password': self.db_config['password'],
                'database': self.db_config['database'],
                'charset': 'utf8mb4',
                'connect_timeout': self.connection_timeout,
                'autocommit': False,
            }
            
            # 添加额外选项
            options = self.db_config.get('options', {})
            if options.get('useSSL') is False:
                connection_params['ssl_disabled'] = True
            
            conn = pymysql.connect(**connection_params)
            self.logger.info("创建新的数据库连接成功")
            return conn
            
        except Exception as e:
            self.logger.error(f"创建数据库连接失败: {e}")
            raise
    
    def get_connection(self) -> Connection:
        """
        从连接池获取连接
        
        Returns:
            数据库连接对象
        """
        try:
            # 尝试从池中获取连接
            conn, last_used = self._pool.get_nowait()
            
            # 检查连接是否超时
            if time.time() - last_used > self.idle_timeout:
                try:
                    conn.close()
                except:
                    pass
                conn = self._create_connection()
            
            # 检查连接是否有效
            if not self._is_connection_valid(conn):
                conn = self._create_connection()
            
            return conn
            
        except Empty:
            # 池中没有连接，创建新连接
            with self._lock:
                if self._active_connections < self.max_connections:
                    conn = self._create_connection()
                    self._active_connections += 1
                    return conn
                else:
                    # 等待连接可用
                    conn, _ = self._pool.get(timeout=self.connection_timeout)
                    return conn
    
    def return_connection(self, conn: Connection):
        """
        将连接返回到池中
        
        Args:
            conn: 数据库连接对象
        """
        if self._is_connection_valid(conn):
            try:
                # 回滚任何未提交的事务
                conn.rollback()
                self._pool.put((conn, time.time()), block=False)
            except:
                # 池已满，关闭连接
                try:
                    conn.close()
                except:
                    pass
                with self._lock:
                    self._active_connections -= 1
        else:
            # 连接无效，关闭并减少计数
            try:
                conn.close()
            except:
                pass
            with self._lock:
                self._active_connections -= 1
    
    def _is_connection_valid(self, conn: Connection) -> bool:
        """
        检查连接是否有效
        
        Args:
            conn: 数据库连接对象
            
        Returns:
            连接是否有效
        """
        try:
            conn.ping(reconnect=False)
            return True
        except:
            return False
    
    def close_all(self):
        """关闭所有连接"""
        while not self._pool.empty():
            try:
                conn, _ = self._pool.get_nowait()
                conn.close()
            except:
                pass
        
        with self._lock:
            self._active_connections = 0


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        """初始化数据库管理器"""
        self.db_config = config.get_database_config()
        # 保持向后兼容性
        self.table_name = self.db_config.get('table_name') or self.db_config.get('tables', {}).get('tweet', 'twitter_tweet')
        self.pool = DatabaseConnectionPool(self.db_config)
        self.logger = logging.getLogger(__name__)
    
    @contextmanager
    def get_connection(self) -> Generator[Connection, None, None]:
        """
        获取数据库连接的上下文管理器
        
        Yields:
            数据库连接对象
        """
        conn = None
        try:
            conn = self.pool.get_connection()
            yield conn
        finally:
            if conn:
                self.pool.return_connection(conn)
    
    @contextmanager
    def get_cursor(self) -> Generator[tuple, None, None]:
        """
        获取数据库游标的上下文管理器
        
        Yields:
            (连接对象, 游标对象)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            try:
                yield conn, cursor
            finally:
                cursor.close()
    
    def execute_query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        执行查询SQL
        
        Args:
            sql: SQL语句
            params: 参数
            
        Returns:
            查询结果列表
        """
        try:
            with self.get_cursor() as (conn, cursor):
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"执行查询失败: {sql}, 参数: {params}, 错误: {e}")
            raise
    
    def execute_update(self, sql: str, params: Optional[tuple] = None) -> int:
        """
        执行更新SQL
        
        Args:
            sql: SQL语句
            params: 参数
            
        Returns:
            影响的行数
        """
        try:
            with self.get_cursor() as (conn, cursor):
                affected_rows = cursor.execute(sql, params)
                conn.commit()
                return affected_rows
        except Exception as e:
            self.logger.error(f"执行更新失败: {sql}, 参数: {params}, 错误: {e}")
            raise
    
    def execute_batch_update(self, sql: str, params_list: List[tuple]) -> int:
        """
        执行批量更新SQL
        
        Args:
            sql: SQL语句
            params_list: 参数列表
            
        Returns:
            总影响的行数
        """
        if not params_list:
            return 0
            
        try:
            with self.get_cursor() as (conn, cursor):
                total_affected = 0
                for params in params_list:
                    affected_rows = cursor.execute(sql, params)
                    total_affected += affected_rows
                conn.commit()
                return total_affected
        except Exception as e:
            self.logger.error(f"执行批量更新失败: {sql}, 错误: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        测试数据库连接
        
        Returns:
            连接是否成功
        """
        try:
            with self.get_cursor() as (conn, cursor):
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            self.logger.error(f"数据库连接测试失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接池"""
        self.pool.close_all()


# 全局数据库管理器实例
db_manager = DatabaseManager() 