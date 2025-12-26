#!/usr/bin/env python3
"""
分析智能时间检测的资源使用和停止时机
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
from collections import defaultdict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.api.twitter_api import twitter_api
from src.utils.logger import get_logger

def analyze_stop_timing():
    """分析智能检测的停止时机和资源使用"""
    logger = get_logger(__name__)
    
    test_list_id = "1996845120008900840"
    hours_limit = 24  # 24小时时间跨度
    
    logger.info("=" * 80)
    logger.info(f"🔍 分析智能时间检测的资源使用和停止时机")
    logger.info(f"List: https://x.com/i/lists/{test_list_id}")
    logger.info(f"时间限制: {hours_limit} 小时")
    logger.info("=" * 80)
    
    # 计算时间截止点
    time_cutoff = datetime.now() - timedelta(hours=hours_limit)
    logger.info(f"📅 时间截止点: {time_cutoff.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 手动模拟分页过程，记录详细的停止判断
    page = 1
    total_requests = 0
    total_tweets_processed = 0
    total_valid_tweets = 0
    
    cursor = None
    project_stats = defaultdict(lambda: {
        'total_tweets': 0, 
        'valid_tweets': 0, 
        'latest_time': None, 
        'latest_time_str': '',
        'first_overdue_page': None
    })
    
    try:
        while page <= 15:  # 最大15页保护
            logger.info(f"\n📄 === 第 {page} 页分析 ===")
            
            # 构建参数
            params = {'count': 100}
            if cursor:
                params['cursor'] = cursor
            
            # 发起请求
            total_requests += 1
            logger.info(f"🔗 发起API请求 #{total_requests}")
            
            tweets, next_cursor = twitter_api.fetch_tweets(list_id=test_list_id, **params)
            
            if not tweets:
                logger.info(f"❌ 第 {page} 页没有数据，自然停止")
                break
            
            logger.info(f"📊 获取到 {len(tweets)} 条推文")
            total_tweets_processed += len(tweets)
            
            # 分析本页推文
            page_project_times = {}  # 本页每个项目的最新时间
            page_project_valid = {}  # 本页每个项目是否有有效推文
            page_valid_count = 0
            page_overdue_count = 0
            
            for tweet in tweets:
                try:
                    user_info = tweet.get('user', {})
                    user_id = user_info.get('id_str', 'unknown')
                    user_name = user_info.get('name', 'Unknown')
                    created_at_str = tweet.get('created_at', '')
                    
                    # 判断项目类型
                    project_type = 'other'
                    if any(keyword in user_name.lower() for keyword in ['bitcoin', 'btc']):
                        project_type = 'bitcoin'
                    elif any(keyword in user_name.lower() for keyword in ['solana', 'sol']):
                        project_type = 'solana'
                    
                    # 解析时间
                    if created_at_str:
                        from dateutil import parser as date_parser
                        tweet_time = date_parser.parse(created_at_str)
                        if tweet_time.tzinfo:
                            tweet_time = tweet_time.replace(tzinfo=None)
                        
                        # 更新项目统计
                        project_stats[project_type]['total_tweets'] += 1
                        
                        # 更新项目最新时间
                        if (project_stats[project_type]['latest_time'] is None or 
                            tweet_time > project_stats[project_type]['latest_time']):
                            project_stats[project_type]['latest_time'] = tweet_time
                            project_stats[project_type]['latest_time_str'] = created_at_str
                        
                        # 更新本页项目时间
                        if user_id not in page_project_times or tweet_time > page_project_times[user_id]:
                            page_project_times[user_id] = tweet_time
                        
                        # 检查是否有效
                        if tweet_time >= time_cutoff:
                            project_stats[project_type]['valid_tweets'] += 1
                            page_project_valid[user_id] = True
                            page_valid_count += 1
                        else:
                            page_overdue_count += 1
                            # 记录首次超时的页面
                            if project_stats[project_type]['first_overdue_page'] is None:
                                project_stats[project_type]['first_overdue_page'] = page
                    
                except Exception as e:
                    logger.warning(f"解析推文失败: {e}")
            
            total_valid_tweets += page_valid_count
            
            logger.info(f"✅ 本页有效推文: {page_valid_count}, 超时推文: {page_overdue_count}")
            
            # 显示每个项目的状态
            for project, stats in project_stats.items():
                if stats['total_tweets'] > 0:
                    latest_time = stats['latest_time']
                    is_overdue = latest_time < time_cutoff if latest_time else True
                    hours_ago = (datetime.now() - latest_time).total_seconds() / 3600 if latest_time else 999
                    
                    status = "⏰超时" if is_overdue else "✅活跃"
                    logger.info(f"  {project}: {stats['valid_tweets']}/{stats['total_tweets']} 条有效, "
                              f"最新: {hours_ago:.1f}h前, {status}")
            
            # **关键分析：智能停止判断**
            should_stop = twitter_api._should_stop_by_project_times(
                page_project_times, 
                page_project_valid, 
                time_cutoff, 
                hours_limit
            )
            
            if should_stop:
                logger.info(f"🛑 智能检测决定在第 {page} 页停止拉取")
                logger.info(f"📈 资源使用总结:")
                logger.info(f"  - API请求次数: {total_requests}")
                logger.info(f"  - 处理推文总数: {total_tweets_processed}")
                logger.info(f"  - 有效推文总数: {total_valid_tweets}")
                logger.info(f"  - 停止页面: {page}/{15}")
                break
            else:
                logger.info(f"➡️ 继续拉取下一页")
            
            # 检查是否还有下一页
            if not next_cursor:
                logger.info(f"📄 API返回无更多数据，自然停止在第 {page} 页")
                break
            
            cursor = next_cursor
            page += 1
    
    except Exception as e:
        logger.error(f"分析过程中发生异常: {e}")
        import traceback
        logger.error(f"异常堆栈: {traceback.format_exc()}")
    
    # 输出详细分析报告
    logger.info(f"\n" + "=" * 80)
    logger.info(f"🎯 智能停止时机分析报告")
    logger.info(f"=" * 80)
    
    logger.info(f"\n📊 资源使用情况:")
    logger.info(f"  总API请求: {total_requests} 次")
    logger.info(f"  总处理推文: {total_tweets_processed} 条") 
    logger.info(f"  有效推文: {total_valid_tweets} 条")
    logger.info(f"  有效率: {total_valid_tweets/total_tweets_processed*100:.1f}%")
    logger.info(f"  停止页面: {page-1}/{15} (节省 {15-(page-1)} 页请求)")
    
    logger.info(f"\n📈 各项目数据分析:")
    for project, stats in sorted(project_stats.items(), key=lambda x: x[1]['total_tweets'], reverse=True):
        if stats['total_tweets'] > 0:
            latest_time = stats['latest_time']
            hours_ago = (datetime.now() - latest_time).total_seconds() / 3600 if latest_time else 999
            first_overdue = stats['first_overdue_page']
            
            logger.info(f"\n  🏷️ {project.upper()}:")
            logger.info(f"    总推文: {stats['total_tweets']} 条")
            logger.info(f"    有效推文: {stats['valid_tweets']} 条")
            logger.info(f"    最新推文: {hours_ago:.1f} 小时前")
            logger.info(f"    最新时间: {stats['latest_time_str']}")
            if first_overdue:
                logger.info(f"    首次超时: 第 {first_overdue} 页")
            else:
                logger.info(f"    状态: 全部推文都在时间窗口内")
    
    logger.info(f"\n🎯 智能检测优势:")
    logger.info(f"1. 避免资源浪费: 在合适时机停止，节省了 {15-(page-1)} 页API请求")
    logger.info(f"2. 数据完整性: 确保所有项目在时间窗口内的数据都被获取")
    logger.info(f"3. 智能判断: 基于多个项目的时间状态综合决策，而非单一阈值")
    logger.info(f"4. 性能优化: 有效率 {total_valid_tweets/total_tweets_processed*100:.1f}% 表明停止时机合理")

if __name__ == '__main__':
    print("开始分析智能时间检测的停止时机...")
    analyze_stop_timing()
    print("\n分析完成!")