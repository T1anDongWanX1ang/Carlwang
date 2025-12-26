#!/usr/bin/env python3
"""
检查数据库表结构脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger


def check_table_structure():
    """检查表结构"""
    logger = get_logger(__name__)
    
    logger.info("检查数据库表结构...")
    
    try:
        # 检查推文表结构
        logger.info("推文表结构:")
        tweet_columns = db_manager.execute_query("DESCRIBE twitter_tweet")
        for col in tweet_columns:
            logger.info(f"  {col}")
        
        print()
        
        # 检查用户表结构
        logger.info("用户表结构:")
        user_columns = db_manager.execute_query("DESCRIBE twitter_user")
        for col in user_columns:
            logger.info(f"  {col}")
        
        return True
        
    except Exception as e:
        logger.error(f"检查表结构失败: {e}")
        return False


def main():
    """主函数"""
    logger = get_logger(__name__)
    
    logger.info("数据库表结构检查工具")
    logger.info("=" * 40)
    
    # 测试连接
    if not db_manager.test_connection():
        logger.error("数据库连接失败")
        sys.exit(1)
    
    # 检查表结构
    check_table_structure()


if __name__ == '__main__':
    main() 