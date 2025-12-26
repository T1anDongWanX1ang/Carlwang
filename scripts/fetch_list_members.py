#!/usr/bin/env python3
"""
获取 Twitter List Members 并入库
从指定的 List ID 中获取所有成员，存入 twitter_list_members_seed 表

使用方法：
    # 测试模式（不调用API，不入库）
    python fetch_list_members.py --test

    # 查看List信息（不入库）
    python fetch_list_members.py --list-id "1996467877948600431" --dry-run

    # 正式运行（处理单个List）
    python fetch_list_members.py --list-id "1996467877948600431" --list-name "KOL_CMC_top100"

    # 处理多个List（按顺序逐个处理）
    python fetch_list_members.py --batch

    # 查看已入库统计
    python fetch_list_members.py --stats
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import time
import requests
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger


class ListMembersFetcher:
    """Twitter List Members 获取器"""

    def __init__(self, api_key: str):
        """
        初始化获取器

        Args:
            api_key: Twitter API密钥
        """
        self.logger = get_logger(__name__)
        self.db_manager = db_manager
        self.api_key = api_key
        self.api_base_url = "https://api.twitterapi.io/twitter/list/members"

        # 统计信息
        self.total_lists = 0
        self.processed_lists = 0
        self.success_lists = 0
        self.failed_lists = 0
        self.total_members = 0
        self.inserted_members = 0
        self.skipped_members = 0
        self.api_calls = 0

        # 你的10个List IDs配置
        self.list_configs = [
            {
                "list_id": "1996467877948600431",
                "list_name": "KOL_CMC_top100",
                "description": "CMC Top 100 KOLs",
                "priority": 1
            },
            {
                "list_id": "1996305216485150751",
                "list_name": "List_02",
                "description": "待补充",
                "priority": 2
            },
            {
                "list_id": "1996038927162245632",
                "list_name": "List_03",
                "description": "待补充",
                "priority": 3
            },
            {
                "list_id": "1996038183545663844",
                "list_name": "List_04",
                "description": "待补充",
                "priority": 4
            },
            {
                "list_id": "1995387419634622745",
                "list_name": "List_05",
                "description": "待补充",
                "priority": 5
            },
            {
                "list_id": "1993260268055417065",
                "list_name": "List_06",
                "description": "待补充",
                "priority": 6
            },
            {
                "list_id": "1994386548842811578",
                "list_name": "List_07",
                "description": "待补充",
                "priority": 7
            },
            {
                "list_id": "1996848536520897010",
                "list_name": "List_08",
                "description": "待补充",
                "priority": 8
            },
            {
                "list_id": "1996863048959820198",
                "list_name": "List_09",
                "description": "待补充",
                "priority": 9
            },
            {
                "list_id": "1996887049027440697",
                "list_name": "List_10",
                "description": "待补充",
                "priority": 10
            }
        ]

    def fetch_members(self, list_id: str) -> List[Dict[str, Any]]:
        """
        调用API获取List成员（支持分页）

        Args:
            list_id: List ID

        Returns:
            成员列表
        """
        all_members = []
        cursor = None
        page = 1

        try:
            while True:
                url = self.api_base_url
                params = {'list_id': list_id}
                if cursor:
                    params['cursor'] = cursor

                headers = {'X-API-Key': self.api_key}

                self.logger.info(f"  API请求 第{page}页: {url}?list_id={list_id}" + (f"&cursor={cursor[:20]}..." if cursor else ""))

                response = requests.get(url, params=params, headers=headers, timeout=30)

                self.api_calls += 1

                if response.status_code == 200:
                    data = response.json()
                    # API返回的是 'members'，不是 'users'
                    members = data.get('members', data.get('users', []))

                    if members:
                        all_members.extend(members)
                        self.logger.info(f"  第{page}页返回 {len(members)} 个成员，累计 {len(all_members)} 个")
                    else:
                        self.logger.info(f"  第{page}页无数据")

                    # 检查是否有下一页
                    has_next = data.get('has_next_page', False)
                    next_cursor = data.get('next_cursor')

                    if has_next and next_cursor:
                        cursor = next_cursor
                        page += 1
                        # 添加延迟避免API限流
                        time.sleep(1)
                    else:
                        self.logger.info(f"  ✓ 所有页面获取完成，共 {len(all_members)} 个成员")
                        break
                else:
                    self.logger.error(f"  API请求失败: HTTP {response.status_code}")
                    self.logger.error(f"  响应内容: {response.text[:500]}")
                    break

            return all_members

        except requests.exceptions.Timeout:
            self.logger.error(f"  API请求超时")
            return all_members
        except requests.exceptions.RequestException as e:
            self.logger.error(f"  API请求异常: {e}")
            return all_members
        except json.JSONDecodeError as e:
            self.logger.error(f"  JSON解析失败: {e}")
            return all_members
        except Exception as e:
            self.logger.error(f"  获取List成员失败: {e}")
            import traceback
            self.logger.error(f"  详细错误: {traceback.format_exc()}")
            return all_members

    def _map_member_data(self, member: Dict[str, Any], list_id: str, list_name: str = None) -> Dict[str, Any]:
        """
        映射API返回数据到数据库字段
        完整映射 https://docs.twitterapi.io/api-reference/endpoint/get_list_members 的所有字段

        Args:
            member: API返回的成员数据
            list_id: List ID
            list_name: List名称

        Returns:
            映射后的数据字典
        """
        # 兼容两种API返回格式
        return {
            # 基础身份字段
            'twitter_user_id': member.get('id_str') or str(member.get('id', '')),
            'username': member.get('userName') or member.get('screen_name'),
            'name': member.get('name'),
            'description': member.get('description'),
            'type': member.get('type', 'user'),
            'url': member.get('url'),

            # 来源追踪
            'source_list_id': list_id,
            'source_list_name': list_name,

            # 用户指标
            'followers_count': member.get('followers') or member.get('followers_count', 0),
            'following_count': member.get('following') or member.get('friends_count', 0),
            'statuses_count': member.get('statusesCount') or member.get('statuses_count', 0),
            'favourites_count': member.get('favouritesCount', 0),
            'media_count': member.get('mediaCount', 0),

            # 账户时间
            'account_created_at': member.get('createdAt') or member.get('created_at'),

            # 认证相关
            'is_verified': 1 if (member.get('isVerified') or member.get('isBlueVerified') or member.get('verified')) else 0,
            'is_blue_verified': 1 if member.get('isBlueVerified') else 0,
            'verified_type': member.get('verifiedType'),

            # 账户属性
            'is_protected': 1 if member.get('protected') else 0,
            'can_dm': 1 if member.get('canDm') else 0,
            'has_custom_timelines': 1 if member.get('hasCustomTimelines') else 0,
            'is_translator': 1 if member.get('isTranslator') else 0,
            'is_automated': 1 if member.get('isAutomated') else 0,
            'automated_by': member.get('automatedBy'),

            # 媒体资料
            'profile_picture': member.get('profilePicture'),
            'cover_picture': member.get('coverPicture'),
            'location': member.get('location'),

            # 简介详情（JSON格式）
            'profile_bio': json.dumps(member.get('profile_bio')) if member.get('profile_bio') else None,

            # 可用性状态
            'unavailable': 1 if member.get('unavailable') else 0,
            'unavailable_reason': member.get('unavailableReason'),
            'message': member.get('message'),

            # 其他属性（JSON格式）
            'withheld_in_countries': json.dumps(member.get('withheldInCountries')) if member.get('withheldInCountries') else None,
            'pinned_tweet_ids': json.dumps(member.get('pinnedTweetIds')) if member.get('pinnedTweetIds') else None,
        }

    def _insert_member(self, member_data: Dict[str, Any]) -> bool:
        """
        插入单个成员到数据库（包含所有API返回字段）

        Args:
            member_data: 成员数据

        Returns:
            是否成功
        """
        try:
            # 使用 INSERT IGNORE 避免重复
            sql = """
            INSERT INTO public_data.twitter_list_members_seed (
                `twitter_user_id`, `username`, `name`, `description`,
                `type`, `url`,
                `source_list_id`, `source_list_name`,
                `followers_count`, `following_count`, `statuses_count`,
                `favourites_count`, `media_count`,
                `account_created_at`,
                `is_verified`, `is_blue_verified`, `verified_type`,
                `is_protected`, `can_dm`, `has_custom_timelines`,
                `is_translator`, `is_automated`, `automated_by`,
                `profile_picture`, `cover_picture`, `location`,
                `profile_bio`,
                `unavailable`, `unavailable_reason`, `message`,
                `withheld_in_countries`, `pinned_tweet_ids`,
                `status`, `created_at`
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, 'pending', NOW()
            )
            """

            params = (
                member_data['twitter_user_id'],
                member_data['username'],
                member_data['name'],
                member_data['description'],
                member_data.get('type', 'user'),
                member_data.get('url'),
                member_data['source_list_id'],
                member_data['source_list_name'],
                member_data['followers_count'],
                member_data['following_count'],
                member_data['statuses_count'],
                member_data.get('favourites_count', 0),
                member_data.get('media_count', 0),
                member_data['account_created_at'],
                member_data['is_verified'],
                member_data.get('is_blue_verified', 0),
                member_data.get('verified_type'),
                member_data['is_protected'],
                member_data.get('can_dm', 0),
                member_data.get('has_custom_timelines', 0),
                member_data.get('is_translator', 0),
                member_data.get('is_automated', 0),
                member_data.get('automated_by'),
                member_data.get('profile_picture'),
                member_data.get('cover_picture'),
                member_data.get('location'),
                member_data.get('profile_bio'),
                member_data.get('unavailable', 0),
                member_data.get('unavailable_reason'),
                member_data.get('message'),
                member_data.get('withheld_in_countries'),
                member_data.get('pinned_tweet_ids'),
            )

            affected_rows = self.db_manager.execute_update(sql, params)
            return affected_rows > 0

        except Exception as e:
            # 如果是重复键错误，不算失败
            if 'Duplicate entry' in str(e) or 'duplicate key' in str(e).lower():
                self.logger.debug(f"    用户已存在: {member_data['username']}")
                return False
            else:
                raise e

    def save_members(self, members: List[Dict[str, Any]], list_id: str, list_name: str = None) -> int:
        """
        保存成员到数据库

        Args:
            members: 成员列表
            list_id: 来源List ID
            list_name: List名称

        Returns:
            插入成功的数量
        """
        if not members:
            return 0

        try:
            inserted_count = 0

            for member in members:
                try:
                    member_data = self._map_member_data(member, list_id, list_name)

                    # 检查必填字段
                    if not member_data['twitter_user_id'] or not member_data['username']:
                        self.logger.warning(f"    跳过无效数据: {member}")
                        continue

                    if self._insert_member(member_data):
                        inserted_count += 1
                        self.logger.debug(f"    ✓ 入库: {member_data['username']} (粉丝: {member_data['followers_count']})")
                    else:
                        self.logger.debug(f"    - 已存在: {member_data['username']}")

                except Exception as e:
                    self.logger.warning(f"    插入成员失败 {member.get('screen_name')}: {e}")
                    continue

            return inserted_count

        except Exception as e:
            self.logger.error(f"  保存成员失败: {e}")
            import traceback
            self.logger.error(f"  详细错误: {traceback.format_exc()}")
            return 0

    def process_single_list(self, list_id: str, list_name: str = None, dry_run: bool = False) -> bool:
        """
        处理单个List

        Args:
            list_id: List ID
            list_name: List名称
            dry_run: 模拟运行（调用API但不入库）

        Returns:
            是否成功
        """
        try:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"开始处理List: {list_id}")
            if list_name:
                self.logger.info(f"List名称: {list_name}")
            self.logger.info(f"{'='*60}")

            # 获取成员
            members = self.fetch_members(list_id)

            if not members:
                self.logger.warning(f"  未获取到成员")
                return False

            self.logger.info(f"  获取到 {len(members)} 个成员")
            self.total_members += len(members)

            # 显示部分成员信息
            self.logger.info(f"  成员示例 (前5个):")
            for i, member in enumerate(members[:5], 1):
                username = member.get('userName') or member.get('screen_name') or 'Unknown'
                name = member.get('name', 'N/A')
                followers = member.get('followers') or member.get('followers_count', 0)
                self.logger.info(f"    {i}. @{username} - {name} (粉丝: {followers:,})")

            if dry_run:
                self.logger.info(f"  [模拟模式] 将入库 {len(members)} 个成员")
                return True

            # 入库
            self.logger.info(f"  开始入库...")
            inserted = self.save_members(members, list_id, list_name)
            self.inserted_members += inserted
            self.skipped_members += (len(members) - inserted)

            self.logger.info(f"  入库完成: {inserted} 条新增, {len(members) - inserted} 条已存在")

            return True

        except Exception as e:
            self.logger.error(f"  处理List失败: {e}")
            import traceback
            self.logger.error(f"  详细错误: {traceback.format_exc()}")
            return False

    def process_batch_lists(self, test_mode: bool = False, dry_run: bool = False):
        """
        批量处理多个List（按优先级顺序）

        Args:
            test_mode: 测试模式
            dry_run: 模拟运行
        """
        self.logger.info("=" * 60)
        self.logger.info("开始批量处理List Members")
        if test_mode:
            self.logger.info("【测试模式 - 不调用API，不入库】")
        elif dry_run:
            self.logger.info("【模拟运行 - 调用API但不入库】")
        else:
            self.logger.info("【正常模式】")
        self.logger.info("=" * 60)

        self.total_lists = len(self.list_configs)

        for idx, config in enumerate(self.list_configs, 1):
            list_id = config['list_id']
            list_name = config['list_name']

            self.logger.info(f"\n▶ [{idx}/{self.total_lists}] 处理 {list_name} ({list_id})")

            if test_mode:
                self.logger.info(f"  [测试] 跳过API调用")
                self.processed_lists += 1
                self.success_lists += 1
                continue

            try:
                success = self.process_single_list(list_id, list_name, dry_run)

                self.processed_lists += 1
                if success:
                    self.success_lists += 1
                else:
                    self.failed_lists += 1

                # API限流保护
                if idx < self.total_lists:
                    self.logger.info(f"  等待2秒后处理下一个List...")
                    time.sleep(2)

            except Exception as e:
                self.logger.error(f"  处理失败: {e}")
                self.failed_lists += 1
                continue

        # 显示统计
        self._show_statistics(test_mode, dry_run)

    def show_stats(self):
        """显示数据库统计信息"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("数据库统计信息")
            self.logger.info("=" * 60)

            # 总体统计
            sql_total = "SELECT COUNT(*) as total FROM public_data.twitter_list_members_seed"
            result = self.db_manager.execute_query(sql_total)
            total = result[0]['total'] if result else 0
            self.logger.info(f"\n总用户数: {total:,}")

            # 按List统计
            sql_by_list = """
            SELECT
                source_list_id,
                source_list_name,
                COUNT(*) as member_count,
                AVG(followers_count) as avg_followers,
                MAX(followers_count) as max_followers
            FROM public_data.twitter_list_members_seed
            GROUP BY source_list_id, source_list_name
            ORDER BY member_count DESC
            """
            result = self.db_manager.execute_query(sql_by_list)

            if result:
                self.logger.info(f"\n按List统计:")
                for row in result:
                    self.logger.info(f"  {row['source_list_name']}: {row['member_count']:,} 个成员, "
                                   f"平均粉丝: {int(row['avg_followers']):,}, "
                                   f"最高粉丝: {int(row['max_followers']):,}")

            # 处理状态统计
            sql_status = """
            SELECT status, COUNT(*) as count
            FROM public_data.twitter_list_members_seed
            GROUP BY status
            """
            result = self.db_manager.execute_query(sql_status)

            if result:
                self.logger.info(f"\n处理状态:")
                for row in result:
                    self.logger.info(f"  {row['status']}: {row['count']:,}")

            # Top 10 粉丝最多
            sql_top = """
            SELECT username, name, followers_count, source_list_name
            FROM public_data.twitter_list_members_seed
            ORDER BY followers_count DESC
            LIMIT 10
            """
            result = self.db_manager.execute_query(sql_top)

            if result:
                self.logger.info(f"\n粉丝数Top 10:")
                for i, row in enumerate(result, 1):
                    self.logger.info(f"  {i}. @{row['username']} - {row['name']}: {row['followers_count']:,} 粉丝 [{row['source_list_name']}]")

            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"查询统计信息失败: {e}")

    def _show_statistics(self, test_mode: bool = False, dry_run: bool = False):
        """显示统计信息"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("处理完成！")
        self.logger.info("=" * 60)
        self.logger.info(f"总List数: {self.total_lists}")
        self.logger.info(f"已处理: {self.processed_lists}")
        self.logger.info(f"成功: {self.success_lists}")
        self.logger.info(f"失败: {self.failed_lists}")

        if not test_mode:
            self.logger.info(f"\nAPI调用统计:")
            self.logger.info(f"  API调用次数: {self.api_calls}")
            self.logger.info(f"  总成员数: {self.total_members}")

            if not dry_run:
                self.logger.info(f"\n入库统计:")
                self.logger.info(f"  新增入库: {self.inserted_members}")
                self.logger.info(f"  已存在跳过: {self.skipped_members}")

        self.logger.info("=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='获取Twitter List Members并入库',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 测试模式
  python %(prog)s --test

  # 查看List信息（不入库）
  python %(prog)s --list-id "1996467877948600431" --dry-run

  # 处理单个List
  python %(prog)s --list-id "1996467877948600431" --list-name "KOL_CMC_top100"

  # 批量处理所有List
  python %(prog)s --batch

  # 查看统计信息
  python %(prog)s --stats
        """
    )

    parser.add_argument('--list-id', type=str,
                       help='处理单个List ID')
    parser.add_argument('--list-name', type=str,
                       help='List名称 (可选)')
    parser.add_argument('--batch', action='store_true',
                       help='批量处理所有List')
    parser.add_argument('--test', action='store_true',
                       help='测试模式（不调用API，不入库）')
    parser.add_argument('--dry-run', action='store_true',
                       help='模拟运行（调用API但不入库）')
    parser.add_argument('--stats', action='store_true',
                       help='查看数据库统计信息')
    parser.add_argument('--api-key', type=str,
                       default='new1_038536908c7f4960812ee7d601f620a1',
                       help='Twitter API密钥')

    args = parser.parse_args()

    # 创建获取器
    fetcher = ListMembersFetcher(api_key=args.api_key)
    logger = get_logger(__name__)

    # 只查看统计
    if args.stats:
        if not db_manager.test_connection():
            logger.error("数据库连接失败")
            sys.exit(1)
        fetcher.show_stats()
        sys.exit(0)

    # 测试数据库连接
    if not db_manager.test_connection():
        logger.error("数据库连接失败，请检查配置")
        sys.exit(1)

    logger.info("✓ 数据库连接成功\n")

    # 执行获取
    if args.batch:
        # 批量处理
        fetcher.process_batch_lists(test_mode=args.test, dry_run=args.dry_run)
    elif args.list_id:
        # 处理单个List
        success = fetcher.process_single_list(
            args.list_id,
            args.list_name,
            dry_run=args.dry_run or args.test
        )
        if success:
            print("\n✓ 处理完成")
        else:
            print("\n✗ 处理失败")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    print("\n✓ 任务完成")


if __name__ == '__main__':
    main()
