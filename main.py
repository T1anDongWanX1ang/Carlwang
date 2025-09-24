#!/usr/bin/env python3
"""
Twitter数据爬虫主程序
"""
import argparse
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.crawler import crawler
from src.utils.scheduler import scheduler
from src.utils.logger import get_logger
from src.utils.config_manager import config
from src.topic_engine import topic_engine
from src.kol_engine import kol_engine
from src.project_engine import project_engine


def main():
    """主函数"""
    # 设置日志
    logger = get_logger(__name__)
    
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='Twitter数据爬虫')
    parser.add_argument('--mode', choices=['once', 'schedule', 'test', 'topic', 'kol', 'project'], default='once',
                       help='运行模式: once=单次执行, schedule=定时调度, test=测试连接, topic=话题分析, kol=KOL分析, project=项目分析')
    parser.add_argument('--list-id', type=str, help='Twitter列表ID')
    parser.add_argument('--max-pages', type=int, help='最大页数')
    parser.add_argument('--page-size', type=int, help='每页大小')
    parser.add_argument('--interval', type=int, help='调度间隔(分钟)')
    parser.add_argument('--config', type=str, help='配置文件路径')
    
    args = parser.parse_args()
    
    logger.info("=" * 50)
    logger.info("Twitter数据爬虫启动")
    logger.info("=" * 50)
    
    try:
        # 如果指定了配置文件，重新加载配置
        if args.config:
            config.config_file = Path(args.config)
            config.reload_config()
            logger.info(f"使用配置文件: {args.config}")
        
                         # 根据模式执行相应操作
        if args.mode == 'test':
            run_tests()
        elif args.mode == 'once':
            run_once(args)
        elif args.mode == 'schedule':
            run_scheduled(args)
        elif args.mode == 'topic':
            run_topic_analysis(args)
        elif args.mode == 'kol':
            run_kol_analysis(args)
        elif args.mode == 'project':
            run_project_analysis(args)
        
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在退出...")
    except Exception as e:
        logger.error(f"程序异常: {e}")
        sys.exit(1)
    finally:
        # 清理资源
        cleanup()


def run_tests():
    """运行连接测试"""
    logger = get_logger(__name__)
    
    logger.info("开始运行连接测试...")
    
    # 测试数据库连接
    db_success = crawler.test_connection()
    
    # 测试API连接
    api_success = crawler.test_api_connection()
    
    # 显示测试结果
    logger.info("=" * 30)
    logger.info("测试结果:")
    logger.info(f"数据库连接: {'✓ 成功' if db_success else '✗ 失败'}")
    logger.info(f"API连接: {'✓ 成功' if api_success else '✗ 失败'}")
    logger.info("=" * 30)
    
    if db_success and api_success:
        logger.info("所有连接测试通过")
        sys.exit(0)
    else:
        logger.error("连接测试失败")
        sys.exit(1)


def run_once(args):
    """单次执行爬取"""
    logger = get_logger(__name__)
    
    logger.info("开始单次数据爬取...")
    
    # 执行爬取
    success = crawler.crawl_tweets(
        list_id=args.list_id,
        max_pages=args.max_pages,
        page_size=args.page_size
    )
    
    # 显示爬取统计信息
    stats = crawler.get_statistics()
    logger.info("=" * 30)
    logger.info("爬取统计:")
    for key, value in stats.items():
        logger.info(f"{key}: {value}")
    logger.info("=" * 30)
    
    if success:
        logger.info("数据爬取完成")
        logger.info("单次执行完成")
        sys.exit(0)
    else:
        logger.error("数据爬取失败")
        sys.exit(1)


def run_scheduled(args):
    """定时调度执行"""
    logger = get_logger(__name__)
    
    logger.info("开始定时调度模式...")
    
    # 设置调度间隔
    if args.interval:
        scheduler.update_interval(args.interval)
    
    # 创建爬取任务函数
    def crawl_task():
        """定时爬取任务（包含项目分析）"""
        logger.info("执行定时爬取任务...")
        
        # 执行爬取
        crawl_success = crawler.crawl_tweets(
            list_id=args.list_id,
            max_pages=args.max_pages,
            page_size=args.page_size
        )
        
        if crawl_success:
            logger.info("爬取完成，开始项目分析...")
            # 执行项目分析（限制推文数量以提高速度）
            max_tweets = min(50, (args.max_pages or 3) * (args.page_size or 100))
            project_success = project_engine.analyze_recent_tweets(hours=24, max_tweets=max_tweets)
            
            if project_success:
                logger.info("项目分析完成")
            else:
                logger.warning("项目分析失败")
        
        return crawl_success
    
    # 设置调度器
    scheduler.set_crawler(crawl_task)
    
    # 先执行一次测试
    logger.info("执行连接测试...")
    if not (crawler.test_connection() and crawler.test_api_connection()):
        logger.error("连接测试失败，无法启动定时调度")
        sys.exit(1)
    
    # 启动定时调度
    scheduler.start_crawling()
    
    logger.info("定时调度已启动，按 Ctrl+C 停止")
    
    try:
        # 主循环，定期显示状态
        while True:
            time.sleep(300)  # 每5分钟显示一次状态
            
            # 显示调度器状态
            scheduler_status = scheduler.get_status()
            logger.info(f"调度器状态: 运行中={scheduler_status['is_running']}, "
                       f"任务数={scheduler_status['task_count']}, "
                       f"成功率={scheduler_status['success_rate']:.1f}%")
            
            # 显示爬虫统计
            crawler_stats = crawler.get_statistics()
            logger.info(f"爬虫统计: 成功={crawler_stats['success_count']}, "
                       f"失败={crawler_stats['error_count']}, "
                       f"数据库推文数={crawler_stats['database_tweet_count']}")
    
    except KeyboardInterrupt:
        logger.info("接收到停止信号...")
        scheduler.stop()


def run_topic_analysis(args):
    """运行话题分析"""
    logger = get_logger(__name__)
    
    logger.info("开始话题分析模式...")
    
    # 分析现有推文数据
    max_tweets = args.max_pages * (args.page_size or 10) if args.max_pages and args.page_size else 20
    
    success = topic_engine.analyze_recent_tweets(hours=24, max_tweets=max_tweets)
    
    # 显示分析结果
    stats = topic_engine.get_topic_statistics()
    logger.info("=" * 30)
    logger.info("话题分析统计:")
    for key, value in stats.items():
        if key != 'hot_topics_sample':  # 跳过复杂的嵌套数据
            logger.info(f"{key}: {value}")
    
    # 显示生成的话题
    from src.database.topic_dao import topic_dao
    topic_count = topic_dao.get_topic_count()
    if topic_count > 0:
        hot_topics = topic_dao.get_hot_topics(limit=3)
        logger.info("\n最新热门话题:")
        for i, topic in enumerate(hot_topics, 1):
            logger.info(f"{i}. {topic.topic_name} (热度: {topic.popularity})")
    
    logger.info("=" * 30)
    
    if success:
        logger.info("话题分析完成")
        sys.exit(0)
    else:
        logger.error("话题分析失败")
        sys.exit(1)


def run_kol_analysis(args):
    """运行KOL分析"""
    logger = get_logger(__name__)
    
    logger.info("开始KOL分析模式...")
    
    # 分析参数
    min_followers = 10000  # 最小粉丝数阈值
    max_users = args.max_pages * (args.page_size or 5) if args.max_pages and args.page_size else 10
    
    success = kol_engine.analyze_all_users_as_kols(min_followers=min_followers, max_users=max_users)
    
    # 显示分析结果
    stats = kol_engine.get_kol_statistics()
    logger.info("=" * 30)
    logger.info("KOL分析统计:")
    for key, value in stats.items():
        if key not in ['type_distribution', 'sentiment_distribution', 'chatgpt_stats']:
            logger.info(f"{key}: {value}")
    
    # 显示识别的KOL
    from src.database.kol_dao import kol_dao
    kol_count = kol_dao.get_kol_count()
    if kol_count > 0:
        top_kols = kol_dao.get_top_kols_by_influence(limit=3)
        logger.info("\n顶级KOL:")
        for i, kol in enumerate(top_kols, 1):
            from src.database.user_dao import user_dao
            user = user_dao.get_user_by_id(kol.kol_id)
            screen_name = user.screen_name if user else "unknown"
            logger.info(f"{i}. @{screen_name} (类型: {kol.type}, 影响力: {kol.influence_score})")
    
    logger.info("=" * 30)
    
    if success:
        logger.info("KOL分析完成")
        sys.exit(0)
    else:
        logger.error("KOL分析失败")
        sys.exit(1)


def run_project_analysis(args):
    """运行项目分析"""
    logger = get_logger(__name__)
    
    logger.info("开始项目分析模式...")
    
    # 分析参数
    hours = 24  # 分析最近24小时
    max_tweets = args.max_pages * (args.page_size or 10) if args.max_pages and args.page_size else 50
    
    success = project_engine.analyze_recent_tweets(hours=hours, max_tweets=max_tweets)
    
    # 显示分析结果
    stats = project_engine.get_project_statistics()
    logger.info("=" * 30)
    logger.info("项目分析统计:")
    for key, value in stats.items():
        if key not in ['category_distribution', 'sentiment_distribution', 'hot_projects', 'chatgpt_stats']:
            logger.info(f"{key}: {value}")
    
    # 显示热门项目
    hot_projects = stats.get('hot_projects', [])
    if hot_projects:
        logger.info("\n热门项目:")
        for i, project in enumerate(hot_projects, 1):
            logger.info(f"{i}. {project['name']} ({project['symbol']}) - 热度: {project['popularity']}, 情感: {project['sentiment']}")
    
    # 显示分类分布
    category_dist = stats.get('category_distribution', {})
    if category_dist:
        logger.info("\n项目分类分布:")
        for category, count in category_dist.items():
            if count > 0:
                logger.info(f"  {category}: {count} 个项目")
    
    logger.info("=" * 30)
    
    if success:
        logger.info("项目分析完成")
        sys.exit(0)
    else:
        logger.error("项目分析失败")
        sys.exit(1)


def cleanup():
    """清理资源"""
    logger = get_logger(__name__)
    
    try:
        # 停止调度器
        if scheduler.is_running:
            scheduler.stop()
        
        # 关闭爬虫
        crawler.close()
        
        logger.info("资源清理完成")
        
    except Exception as e:
        logger.error(f"清理资源时出错: {e}")


if __name__ == '__main__':
    main() 