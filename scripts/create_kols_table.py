#!/usr/bin/env python3
"""
创建KOL表脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger


def create_kols_table():
    """创建KOL表"""
    logger = get_logger(__name__)
    
    logger.info("开始创建KOL表...")
    
    # 创建KOL表SQL
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS kols (
        `kol_id` VARCHAR(50) NOT NULL COMMENT "推特账号ID（主键）",
        `type` VARCHAR(50) NULL COMMENT "KOL分类, 如founder/influencer/investor等",
        `tag` VARCHAR(100) NULL COMMENT "标签，如BNB/Meme/AI等（基于长期发推内容总结）",
        `influence_score` DECIMAL(38, 0) NULL COMMENT "影响力评分（综合KOL粉丝数、原创发帖数、发帖频次、互动数计算）",
        `influence_score_history` JSON NULL COMMENT "影响力评分历史记录",
        `call_increase_1h` DECIMAL(38, 0) NULL COMMENT "每次喊单后1小时涨跌幅均值",
        `call_increase_24h` DECIMAL(38, 0) NULL COMMENT "每次喊单后24小时涨跌幅均值", 
        `call_increase_3d` DECIMAL(38, 0) NULL COMMENT "每次喊单后3天涨跌幅均值",
        `call_increase_7d` DECIMAL(38, 0) NULL COMMENT "每次喊单后7天涨跌幅均值",
        `sentiment` VARCHAR(20) NULL COMMENT "多空倾向，bullish/bearish/neutral（LLM总结）",
        `sentiment_history` JSON NULL COMMENT "多空倾向历史记录",
        `summary` TEXT NULL COMMENT "AI总结，KOL对整个市场的观点总结（通过LLM生成）",
        `trust_rating` DECIMAL(38, 0) NULL DEFAULT 0 COMMENT "可信度评级（检查KOL是否删推、是否吹过归零项目）",
        `is_kol100` int default 0 COMMENT "是否被纳入KOL100指数",
        `last_updated` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "最后更新时间",
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT "记录创建时间"
    )
    ENGINE=olap
    UNIQUE KEY(`kol_id`)
    COMMENT "KOL分析主表"
    DISTRIBUTED BY HASH(`kol_id`) BUCKETS 10
    PROPERTIES (
        "replication_allocation" = "tag.location.default: 1"
    )
    """
    
    try:
        logger.info("创建KOL表...")
        db_manager.execute_update(create_table_sql)
        logger.info("KOL表创建成功")
        
        # 验证表是否创建成功
        count_result = db_manager.execute_query("SELECT COUNT(*) as count FROM kols")
        if count_result:
            logger.info(f"KOL表验证成功，当前记录数: {count_result[0]['count']}")
        
        return True
        
    except Exception as e:
        logger.error(f"创建KOL表失败: {e}")
        return False


def main():
    """主函数"""
    logger = get_logger(__name__)
    
    logger.info("KOL表创建工具")
    logger.info("=" * 30)
    
    # 测试连接
    if not db_manager.test_connection():
        logger.error("数据库连接失败")
        sys.exit(1)
    
    # 创建表
    if create_kols_table():
        logger.info("KOL表创建完成")
    else:
        logger.error("KOL表创建失败")
        sys.exit(1)


if __name__ == '__main__':
    main() 