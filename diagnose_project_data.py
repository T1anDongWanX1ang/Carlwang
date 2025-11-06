#!/usr/bin/env python3
"""
诊断 twitter_projects 数据更新问题
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

def diagnose_project_data():
    """诊断项目数据问题"""
    logger = get_logger(__name__)
    
    print("=" * 80)
    print("🔍 诊断 twitter_projects 数据更新问题")
    print("=" * 80)
    print()
    
    try:
        # 1. 检查数据库连接
        print("1️⃣  检查数据库连接...")
        if not db_manager.test_connection():
            print("   ❌ 数据库连接失败")
            return False
        print("   ✅ 数据库连接正常")
        print()
        
        # 2. 检查推文数据
        print("2️⃣  检查推文数据...")
        tweet_sql = '''
            SELECT 
                COUNT(*) as total,
                MAX(created_at) as latest_tweet,
                MAX(update_time) as latest_update
            FROM twitter_tweet
        '''
        tweet_result = db_manager.execute_query(tweet_sql)
        if tweet_result:
            total_tweets = tweet_result[0]['total']
            latest_tweet = tweet_result[0]['latest_tweet']
            latest_update = tweet_result[0]['latest_update']
            
            print(f"   总推文数: {total_tweets}")
            print(f"   最新推文时间: {latest_tweet}")
            print(f"   最新更新时间: {latest_update}")
            
            # 检查最新推文距今多久
            if latest_tweet:
                try:
                    if isinstance(latest_tweet, str):
                        latest_dt = datetime.strptime(str(latest_tweet).split('.')[0], '%Y-%m-%d %H:%M:%S')
                    else:
                        latest_dt = latest_tweet
                    
                    days_ago = (datetime.now() - latest_dt).days
                    print(f"   ⚠️  最新推文是 {days_ago} 天前的数据")
                    
                    if days_ago > 1:
                        print(f"   ❌ 推文数据已经 {days_ago} 天没有更新了！")
                except Exception as e:
                    print(f"   ⚠️  无法计算时间差: {e}")
        print()
        
        # 3. 检查最近推文数据
        print("3️⃣  检查最近推文数量...")
        time_ranges = [
            ("1小时", 1),
            ("24小时", 24),
            ("7天", 24 * 7),
            ("30天", 24 * 30)
        ]
        
        for label, hours in time_ranges:
            cutoff = datetime.now() - timedelta(hours=hours)
            count_sql = f'''
                SELECT COUNT(*) as count 
                FROM twitter_tweet 
                WHERE created_at >= '{cutoff.strftime("%Y-%m-%d %H:%M:%S")}'
            '''
            result = db_manager.execute_query(count_sql)
            count = result[0]['count'] if result else 0
            print(f"   最近{label}: {count} 条推文")
        print()
        
        # 4. 检查项目数据
        print("4️⃣  检查项目数据...")
        project_sql = '''
            SELECT 
                COUNT(*) as total,
                MAX(update_time) as latest_update,
                MAX(created_at) as latest_created
            FROM twitter_projects
        '''
        project_result = db_manager.execute_query(project_sql)
        if project_result:
            total_projects = project_result[0]['total']
            latest_update = project_result[0]['latest_update']
            latest_created = project_result[0]['latest_created']
            
            print(f"   总项目数: {total_projects}")
            print(f"   最新更新时间: {latest_update}")
            print(f"   最新创建时间: {latest_created}")
            
            # 检查最新项目距今多久
            if latest_update:
                try:
                    if isinstance(latest_update, str):
                        latest_dt = datetime.strptime(str(latest_update).split('.')[0], '%Y-%m-%d %H:%M:%S')
                    else:
                        latest_dt = latest_update
                    
                    days_ago = (datetime.now() - latest_dt).days
                    print(f"   ⚠️  最新项目是 {days_ago} 天前更新的")
                    
                    if days_ago > 1:
                        print(f"   ❌ 项目数据已经 {days_ago} 天没有更新了！")
                except Exception as e:
                    print(f"   ⚠️  无法计算时间差: {e}")
        print()
        
        # 5. 检查最近项目更新分布
        print("5️⃣  检查最近项目更新分布...")
        for label, hours in time_ranges:
            cutoff = datetime.now() - timedelta(hours=hours)
            count_sql = f'''
                SELECT COUNT(*) as count 
                FROM twitter_projects 
                WHERE update_time >= '{cutoff.strftime("%Y-%m-%d %H:%M:%S")}'
            '''
            result = db_manager.execute_query(count_sql)
            count = result[0]['count'] if result else 0
            print(f"   最近{label}更新的项目: {count} 个")
        print()
        
        # 6. 查看最近更新的项目
        print("6️⃣  最近更新的5个项目:")
        recent_projects_sql = '''
            SELECT project_id, name, symbol, update_time, popularity, sentiment_index 
            FROM twitter_projects 
            ORDER BY update_time DESC 
            LIMIT 5
        '''
        recent_projects = db_manager.execute_query(recent_projects_sql)
        if recent_projects:
            for i, p in enumerate(recent_projects, 1):
                print(f"   {i}. {p['name']} ({p['symbol']})")
                print(f"      更新时间: {p['update_time']}")
                print(f"      热度: {p['popularity']}, 情绪: {p['sentiment_index']}")
        else:
            print("   ❌ 没有找到任何项目")
        print()
        
        # 7. 检查配置
        print("7️⃣  检查配置...")
        from src.utils.config_manager import config
        chatgpt_config = config.get('chatgpt', {})
        enable_project_analysis = chatgpt_config.get('enable_project_analysis', False)
        print(f"   项目分析功能: {'✅ 已启用' if enable_project_analysis else '❌ 已禁用'}")
        print()
        
        # 8. 诊断结论
        print("=" * 80)
        print("📋 诊断结论:")
        print("=" * 80)
        
        # 检查推文数据是否正常
        if tweet_result and tweet_result[0]['latest_tweet']:
            try:
                latest_tweet_str = str(tweet_result[0]['latest_tweet']).split('.')[0]
                latest_tweet_dt = datetime.strptime(latest_tweet_str, '%Y-%m-%d %H:%M:%S')
                tweet_days_ago = (datetime.now() - latest_tweet_dt).days
                
                if tweet_days_ago > 1:
                    print("❌ 根本原因: 推文数据爬取已停止")
                    print(f"   最新推文是 {tweet_days_ago} 天前的，爬虫服务可能已停止")
                    print()
                    print("🔧 解决方案:")
                    print("   1. 检查爬虫服务是否运行:")
                    print("      ./start_crawler_service.sh status")
                    print()
                    print("   2. 如果未运行，启动爬虫服务:")
                    print("      ./start_crawler_service.sh start")
                    print()
                    print("   3. 查看爬虫日志:")
                    print("      tail -f logs/crawler_service.log")
                    print()
                    print("   4. 推文数据恢复后，项目数据会自动生成")
                    return False
            except Exception as e:
                print(f"⚠️  分析推文时间时出错: {e}")
        
        # 检查项目数据是否正常
        if project_result and project_result[0]['latest_update']:
            try:
                latest_project_str = str(project_result[0]['latest_update']).split('.')[0]
                latest_project_dt = datetime.strptime(latest_project_str, '%Y-%m-%d %H:%M:%S')
                project_days_ago = (datetime.now() - latest_project_dt).days
                
                if project_days_ago > 1:
                    print(f"⚠️  项目数据已经 {project_days_ago} 天没有更新")
                    
                    if not enable_project_analysis:
                        print("❌ 项目分析功能已禁用")
                        print()
                        print("🔧 解决方案:")
                        print("   在 config/config.json 中设置:")
                        print('   "enable_project_analysis": true')
                        return False
            except Exception as e:
                print(f"⚠️  分析项目时间时出错: {e}")
        
        print("✅ 如果以上问题都解决，项目数据应该会自动更新")
        print()
        
        return True
        
    except Exception as e:
        logger.error(f"诊断失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    try:
        diagnose_project_data()
    except KeyboardInterrupt:
        print("\n诊断已中断")
    except Exception as e:
        print(f"❌ 诊断过程出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

