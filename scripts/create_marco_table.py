#!/usr/bin/env python3
"""
创建 twitter_marco 数据表脚本
"""
import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.connection import db_manager
from src.utils.logger import setup_logger


def create_marco_table():
    """创建 twitter_marco 表"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS twitter_marco (
        `id` VARCHAR(50) NOT NULL COMMENT "主键，全局唯一标识符",
        `timestamp` DATETIME NOT NULL COMMENT "时间点，每30分钟记录一次",
        `sentiment_index` FLOAT NULL COMMENT "整个Crypto推特情绪得分[0,100]，基于KOL100指数推文计算",
        `summary` TEXT NULL COMMENT "AI总结，基于近4小时KOL推文的事件聚类和观点总结",
        
        `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "记录更新时间"
    )
    ENGINE=OLAP
    UNIQUE KEY(`id`, `timestamp`)
    COMMENT "推特Marco衍生数据表"
    DISTRIBUTED BY HASH(`id`) BUCKETS 10
    PROPERTIES (
        "replication_allocation" = "tag.location.default: 1"
    )
    """
    
    try:
        logger = logging.getLogger(__name__)
        
        # 测试数据库连接
        if not db_manager.test_connection():
            logger.error("数据库连接失败")
            return False
        
        logger.info("开始创建 twitter_marco 表...")
        
        # 执行创建表SQL
        affected_rows = db_manager.execute_update(create_table_sql)
        
        logger.info(f"twitter_marco 表创建完成")
        
        # 验证表是否创建成功
        check_sql = "SHOW TABLES LIKE 'twitter_marco'"
        results = db_manager.execute_query(check_sql)
        
        if results:
            logger.info("✅ twitter_marco 表创建成功并验证通过")
            
            # 显示表结构
            desc_sql = "DESCRIBE twitter_marco"
            columns = db_manager.execute_query(desc_sql)
            
            print("\n=== twitter_marco 表结构 ===")
            for col in columns:
                print(f"{col.get('Field', 'N/A'):20} {col.get('Type', 'N/A'):15} {col.get('Null', 'N/A'):8} {col.get('Key', 'N/A'):8}")
            
            return True
        else:
            logger.error("❌ 表创建失败或验证失败")
            return False
            
    except Exception as e:
        logger.error(f"创建 twitter_marco 表失败: {e}")
        return False


def main():
    """主函数"""
    # 设置日志
    setup_logger()
    
    # 设置日志级别
    logging.getLogger().setLevel(logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("开始创建 twitter_marco 数据表")
        
        if create_marco_table():
            logger.info("🎉 twitter_marco 表创建成功！")
            print("\n现在可以运行以下命令生成Marco数据:")
            print("python generate_marco_data.py --mode latest")
            print("python generate_marco_data.py --mode backfill --days 7")
        else:
            logger.error("❌ twitter_marco 表创建失败")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"程序执行异常: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 