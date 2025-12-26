#!/usr/bin/env python3
"""
查看 List Members Following 获取进度
显示已处理和未处理的member统计信息
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger

def check_progress(list_id: str = '1996467877948600431'):
    """
    检查指定List的following获取进度

    Args:
        list_id: Twitter List ID
    """
    logger = get_logger(__name__)

    try:
        # 测试数据库连接
        if not db_manager.test_connection():
            logger.error("数据库连接失败")
            return False

        print("\n" + "=" * 70)
        print(f"List Members Following 获取进度")
        print(f"List ID: {list_id}")
        print("=" * 70)

        # 1. 总Member数
        total_sql = f"""
        SELECT COUNT(*) as total
        FROM public_data.twitter_list_members_seed
        WHERE source_list_id = '{list_id}'
        """
        result = db_manager.execute_query(total_sql)
        total = result[0]['total'] if result else 0

        # 2. 已处理的Member数（有following数据的）
        processed_sql = f"""
        SELECT COUNT(DISTINCT follower_id) as processed
        FROM public_data.twitter_kol_all
        WHERE follower_id IN (
            SELECT twitter_user_id
            FROM public_data.twitter_list_members_seed
            WHERE source_list_id = '{list_id}'
        )
        """
        result = db_manager.execute_query(processed_sql)
        processed = result[0]['processed'] if result else 0

        # 3. 统计按status分组
        status_sql = f"""
        SELECT
            status,
            COUNT(*) as count
        FROM public_data.twitter_list_members_seed
        WHERE source_list_id = '{list_id}'
        GROUP BY status
        """
        status_result = db_manager.execute_query(status_sql)

        # 4. 获取缓存进度（实时进度）
        cache_file = Path(__file__).parent / ".kol_cache" / "progress.json"
        cache_count = 0
        completed_list = []
        last_update = None
        if cache_file.exists():
            import json
            from datetime import datetime
            with open(cache_file, 'r') as f:
                progress_data = json.load(f)
                completed_list = progress_data.get('completed', [])
                cache_count = len(completed_list)
                last_update = progress_data.get('last_update', '')

        # 显示统计
        print(f"\n📊 总体进度:")
        print(f"  总Member数:    {total:>6}")
        print(f"  已获取Following: {processed:>6}")
        print(f"  剩余未处理:    {total - processed:>6}")
        if total > 0:
            print(f"  完成度:        {processed/total*100:>5.2f}%")

        print(f"\n📁 数据库状态:")
        if status_result:
            for row in status_result:
                print(f"  {row['status']:12s}: {row['count']:>6}")

        print(f"\n💾 实时获取进度 (来自缓存):")
        print(f"  已完成API获取:  {cache_count:>6} 个members")
        print(f"  已入库到数据库: {processed:>6} 个members")
        if cache_count > processed:
            print(f"  ⚠️  差异:        {cache_count - processed:>6} 个 (正在入库中)")
        if last_update:
            print(f"  最后更新:       {last_update}")
        if cache_file.exists():
            print(f"  缓存文件:       {cache_file}")
            if completed_list:
                print(f"\n  最近完成的5个members:")
                for username in completed_list[-5:]:
                    print(f"    • {username}")
        else:
            print(f"  缓存文件:       不存在（首次运行）")

        # 5. 显示Top 5已处理的member
        top_processed_sql = f"""
        SELECT
            m.username,
            m.name,
            m.followers_count,
            COUNT(DISTINCT f.id) as following_count
        FROM public_data.twitter_list_members_seed m
        INNER JOIN public_data.twitter_kol_all f
            ON f.follower_id = m.twitter_user_id
        WHERE m.source_list_id = '{list_id}'
        GROUP BY m.twitter_user_id, m.username, m.name, m.followers_count
        ORDER BY following_count DESC
        LIMIT 5
        """
        top_result = db_manager.execute_query(top_processed_sql)

        if top_result:
            print(f"\n✅ 已处理 Top 5 (按following数量):")
            print(f"  {'Username':<20} {'Name':<20} {'Followers':>10} {'Following':>10}")
            print(f"  {'-'*20} {'-'*20} {'-'*10} {'-'*10}")
            for row in top_result:
                username = (row['username'] or 'N/A')[:20]
                name = (row['name'] or 'N/A')[:20]
                print(f"  {username:<20} {name:<20} {row['followers_count']:>10,} {row['following_count']:>10,}")

        # 6. 显示未处理的member数量（按粉丝数排序）
        unprocessed_sql = f"""
        SELECT
            m.username,
            m.name,
            m.followers_count
        FROM public_data.twitter_list_members_seed m
        LEFT JOIN public_data.twitter_kol_all f
            ON f.follower_id = m.twitter_user_id
        WHERE m.source_list_id = '{list_id}'
        AND f.id IS NULL
        ORDER BY m.followers_count DESC
        LIMIT 5
        """
        unprocessed_result = db_manager.execute_query(unprocessed_sql)

        if unprocessed_result:
            print(f"\n⏳ 待处理 Top 5 (按粉丝数):")
            print(f"  {'Username':<20} {'Name':<20} {'Followers':>10}")
            print(f"  {'-'*20} {'-'*20} {'-'*10}")
            for row in unprocessed_result:
                username = (row['username'] or 'N/A')[:20]
                name = (row['name'] or 'N/A')[:20]
                print(f"  {username:<20} {name:<20} {row['followers_count']:>10,}")

        print("\n" + "=" * 70)

        return True

    except Exception as e:
        logger.error(f"查询进度失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='查看List Members Following获取进度')
    parser.add_argument('--list-id', type=str,
                       default='1996467877948600431',
                       help='Twitter List ID (默认: 1996467877948600431)')

    args = parser.parse_args()

    success = check_progress(args.list_id)

    if not success:
        print("\n✗ 查询失败")
        sys.exit(1)
