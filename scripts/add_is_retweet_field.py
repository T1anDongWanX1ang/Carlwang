#!/usr/bin/env python3
"""
直接执行ALTER TABLE添加is_retweet字段
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger


def add_is_retweet_column():
    """添加is_retweet字段到twitter_tweet_project_new表"""
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info("开始为 twitter_tweet_project_new 表添加 is_retweet 字段")
    logger.info("=" * 60)

    # 测试数据库连接
    logger.info("步骤1: 测试数据库连接...")
    if not db_manager.test_connection():
        logger.error("❌ 数据库连接失败，请检查配置")
        return False

    logger.info("✅ 数据库连接成功")

    # 检查表是否存在
    logger.info("\n步骤2: 检查表是否存在...")
    check_table_sql = """
    SELECT COUNT(*) as count
    FROM information_schema.tables
    WHERE table_name = 'twitter_tweet_project_new'
    """

    try:
        result = db_manager.execute_query(check_table_sql)
        if not result or result[0]['count'] == 0:
            logger.error("❌ 表 twitter_tweet_project_new 不存在")
            return False
        logger.info("✅ 表存在")
    except Exception as e:
        logger.warning(f"⚠️  无法检查表是否存在: {e}")
        logger.info("继续执行...")

    # 检查字段是否已存在
    logger.info("\n步骤3: 检查 is_retweet 字段是否已存在...")
    check_column_sql = """
    SELECT COUNT(*) as count
    FROM information_schema.columns
    WHERE table_name = 'twitter_tweet_project_new'
    AND column_name = 'is_retweet'
    """

    try:
        result = db_manager.execute_query(check_column_sql)
        if result and result[0]['count'] > 0:
            logger.warning("⚠️  字段 is_retweet 已存在，跳过添加")
            logger.info("验证现有字段...")
            verify_column()
            return True
        logger.info("✅ 字段不存在，可以添加")
    except Exception as e:
        logger.warning(f"⚠️  无法检查字段是否存在: {e}")
        logger.info("尝试直接添加字段...")

    # 添加字段
    logger.info("\n步骤4: 执行 ALTER TABLE 添加字段...")
    alter_sql = """
    ALTER TABLE twitter_tweet_project_new
    ADD COLUMN is_retweet BOOLEAN DEFAULT false COMMENT '是否为转发推文（检测retweeted_status字段）'
    """

    try:
        db_manager.execute_update(alter_sql)
        logger.info("✅ 字段添加成功")
    except Exception as e:
        error_msg = str(e).lower()
        if 'duplicate column' in error_msg or 'already exists' in error_msg:
            logger.warning("⚠️  字段已存在，跳过添加")
        else:
            logger.error(f"❌ 添加字段失败: {e}")
            return False

    # 验证字段
    logger.info("\n步骤5: 验证字段是否添加成功...")
    if verify_column():
        logger.info("\n" + "=" * 60)
        logger.info("✅ is_retweet 字段添加完成！")
        logger.info("=" * 60)
        return True
    else:
        logger.error("\n" + "=" * 60)
        logger.error("❌ 字段验证失败")
        logger.error("=" * 60)
        return False


def verify_column():
    """验证字段是否存在并显示信息"""
    logger = get_logger(__name__)

    # 查看表结构
    desc_sql = "DESC twitter_tweet_project_new"

    try:
        results = db_manager.execute_query(desc_sql)

        # 查找is_retweet字段
        is_retweet_found = False
        for row in results:
            if row.get('Field') == 'is_retweet':
                is_retweet_found = True
                logger.info("\n字段信息:")
                logger.info(f"  字段名: {row.get('Field')}")
                logger.info(f"  类型: {row.get('Type')}")
                logger.info(f"  允许NULL: {row.get('Null')}")
                logger.info(f"  默认值: {row.get('Default')}")
                logger.info(f"  注释: {row.get('Comment', 'N/A')}")
                break

        if not is_retweet_found:
            logger.error("❌ 在表结构中未找到 is_retweet 字段")
            return False

        # 查询示例数据
        query_sql = """
        SELECT id_str, is_retweet, is_quote_status,
               SUBSTRING(full_text, 1, 50) as text_preview
        FROM twitter_tweet_project_new
        LIMIT 5
        """

        data_results = db_manager.execute_query(query_sql)

        if data_results:
            logger.info(f"\n示例数据 (共{len(data_results)}条):")
            for i, row in enumerate(data_results, 1):
                logger.info(f"  {i}. ID: {row.get('id_str')}")
                logger.info(f"     is_retweet: {row.get('is_retweet')}")
                logger.info(f"     is_quote_status: {row.get('is_quote_status')}")
                logger.info(f"     内容: {row.get('text_preview')}...")
        else:
            logger.info("\n表中暂无数据")

        return True

    except Exception as e:
        logger.error(f"❌ 验证失败: {e}")
        return False


def main():
    """主函数"""
    logger = get_logger(__name__)

    try:
        success = add_is_retweet_column()

        if success:
            logger.info("\n✨ 操作完成！现在可以运行项目推文爬虫了：")
            logger.info("   ./start_service_project.sh once")
            logger.info("   或")
            logger.info("   python3 main.py --mode project-once")
            sys.exit(0)
        else:
            logger.error("\n❌ 操作失败，请检查错误信息")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️  操作被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ 发生异常: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
