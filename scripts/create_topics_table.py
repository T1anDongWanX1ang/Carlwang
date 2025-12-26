#!/usr/bin/env python3
"""
创建话题表脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger


def create_topics_table():
    """创建话题表"""
    logger = get_logger(__name__)
    
    logger.info("开始创建话题表...")
    
    # 创建话题表SQL
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS topics (
        `topic_id` bigint NOT NULL AUTO_INCREMENT COMMENT "话题ID（主键）",
        `topic_name` text NULL COMMENT "话题名（LLM对KOL推文进行事件聚类，提取出共同话题）",
        `created_at` datetime NOT NULL COMMENT "话题创建时间",
        `brief` text NULL COMMENT "话题简述（LLM整体分析KOL推文，提取出共同话题）",
        `popularity` int NULL DEFAULT 0 COMMENT "话题热度（综合推文数量和互动数据计算）",
        `propagation_speed_5m` float NULL COMMENT "话题5min传播速度（衡量事件相关推文/互动量在5min内的增长速率）",
        `propagation_speed_1h` float NULL COMMENT "话题1h传播速度（衡量事件相关推文/互动量在1h内的增长速率）",
        `propagation_speed_4h` float NULL COMMENT "话题4h传播速度（衡量事件相关推文/互动量在4h内的增长速率）",
        `kol_opinions` json NULL COMMENT "KOL观点列表（JSON数组格式，包含每个KOL的观点和方向）",
        `mob_opinion_direction` varchar(10) NULL COMMENT "散户整体的观点方向，positive/negative/neutral（LLM总结）",
        `summary` text NULL COMMENT "AI总结，KOL对此话题的观点总结（通过LLM生成。输入是与此话题相关的新入库KOL推文+上一次的AI总结）",
        `popularity_history` json NULL COMMENT "热度历史数据（JSON数组格式，存储历史热度值和时间戳）",
        `update_time` datetime NULL DEFAULT CURRENT_TIMESTAMP COMMENT "记录更新时间"
    ) ENGINE=OLAP
    UNIQUE KEY(`topic_id`)
    COMMENT '话题主表（包含所有字段）'
    DISTRIBUTED BY HASH(`topic_id`) BUCKETS 10
    PROPERTIES (
        "replication_allocation" = "tag.location.default: 1"
    )
    """
    
    try:
        logger.info("创建话题表...")
        db_manager.execute_update(create_table_sql)
        logger.info("话题表创建成功")
        
        # 验证表是否创建成功
        count_result = db_manager.execute_query("SELECT COUNT(*) as count FROM topics")
        if count_result:
            logger.info(f"话题表验证成功，当前记录数: {count_result[0]['count']}")
        
        return True
        
    except Exception as e:
        logger.error(f"创建话题表失败: {e}")
        return False


def main():
    """主函数"""
    logger = get_logger(__name__)
    
    logger.info("话题表创建工具")
    logger.info("=" * 30)
    
    # 测试连接
    if not db_manager.test_connection():
        logger.error("数据库连接失败")
        sys.exit(1)
    
    # 创建表
    if create_topics_table():
        logger.info("话题表创建完成")
    else:
        logger.error("话题表创建失败")
        sys.exit(1)


if __name__ == '__main__':
    main() 