#!/usr/bin/env python3
"""
修复数据库中的中文 brief
将所有中文 brief 重新生成为英文

使用方法：
    # 检查有多少中文 brief
    python fix_chinese_brief.py --check

    # 修复最近48小时的数据
    python fix_chinese_brief.py --hours 48

    # 修复所有中文 brief
    python fix_chinese_brief.py --all

    # 模拟运行（不实际修改）
    python fix_chinese_brief.py --hours 48 --dry-run
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import re

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.database.topic_dao import topic_dao
from src.api.chatgpt_client import chatgpt_client
from src.utils.logger import get_logger


class ChineseBriefFixer:
    """中文 brief 修复器"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.db_manager = db_manager
        self.topic_dao = topic_dao
        self.chatgpt_client = chatgpt_client

        # 统计信息
        self.total_checked = 0
        self.chinese_found = 0
        self.fixed_count = 0
        self.failed_count = 0

    def has_chinese(self, text: str) -> bool:
        """
        检查文本是否包含中文字符

        Args:
            text: 待检查的文本

        Returns:
            是否包含中文
        """
        if not text:
            return False
        # 检查是否包含中文字符（Unicode范围）
        return bool(re.search('[\u4e00-\u9fff]', text))

    def get_topics_to_fix(self, hours: int = None, check_all: bool = False) -> List[Dict[str, Any]]:
        """
        获取需要修复的 topic 列表

        Args:
            hours: 检查最近多少小时的数据
            check_all: 是否检查所有数据

        Returns:
            需要修复的 topic 列表
        """
        try:
            table_name = self.db_manager.db_config.get('tables', {}).get('topic', 'twitter_topic')

            if check_all:
                sql = f"""
                SELECT topic_id, topic_name, brief, created_at, update_time
                FROM {table_name}
                WHERE brief IS NOT NULL AND brief != ''
                ORDER BY update_time DESC
                """
                results = self.db_manager.execute_query(sql)
            elif hours:
                cutoff_time = datetime.now() - timedelta(hours=hours)
                sql = f"""
                SELECT topic_id, topic_name, brief, created_at, update_time
                FROM {table_name}
                WHERE brief IS NOT NULL AND brief != ''
                AND update_time >= %s
                ORDER BY update_time DESC
                """
                results = self.db_manager.execute_query(sql, (cutoff_time,))
            else:
                return []

            # 过滤出包含中文的 brief
            chinese_topics = []
            for row in results:
                self.total_checked += 1
                if self.has_chinese(row['brief']):
                    chinese_topics.append(row)
                    self.chinese_found += 1

            return chinese_topics

        except Exception as e:
            self.logger.error(f"查询需要修复的 topic 失败: {e}")
            return []

    def regenerate_brief(self, topic_name: str, old_brief: str) -> str:
        """
        重新生成英文 brief

        Args:
            topic_name: topic 名称
            old_brief: 旧的 brief（可能是中文）

        Returns:
            新的英文 brief
        """
        try:
            prompt = f"""
Please generate a brief English description for the following cryptocurrency topic:

Topic Name: {topic_name}
Current Description (may be in Chinese): {old_brief}

Please provide:
- A concise English description (20-50 words)
- Explain the topic content and background
- Focus on cryptocurrency, blockchain, or related themes

IMPORTANT: The description MUST be in English only.

Return only the brief description text, no JSON format needed.
            """

            messages = [
                {"role": "system", "content": "You are a professional cryptocurrency content analyst. Always respond in English."},
                {"role": "user", "content": prompt}
            ]

            response = self.chatgpt_client._make_request(
                messages=messages,
                temperature=0.3,
                max_tokens=150
            )

            if response:
                # 清理响应
                new_brief = response.strip()
                # 移除可能的引号
                if new_brief.startswith('"') and new_brief.endswith('"'):
                    new_brief = new_brief[1:-1]
                if new_brief.startswith("'") and new_brief.endswith("'"):
                    new_brief = new_brief[1:-1]
                return new_brief

            return None

        except Exception as e:
            self.logger.error(f"重新生成 brief 失败: {e}")
            return None

    def fix_topic_brief(self, topic_id: str, topic_name: str, old_brief: str, dry_run: bool = False) -> bool:
        """
        修复单个 topic 的 brief

        Args:
            topic_id: topic ID
            topic_name: topic 名称
            old_brief: 旧的 brief
            dry_run: 是否为模拟运行

        Returns:
            是否成功
        """
        try:
            # 生成新的英文 brief
            new_brief = self.regenerate_brief(topic_name, old_brief)

            if not new_brief:
                self.logger.error(f"  生成新 brief 失败: {topic_name}")
                return False

            # 验证新 brief 是否为英文
            if self.has_chinese(new_brief):
                self.logger.warning(f"  生成的 brief 仍包含中文: {topic_name}")
                self.logger.warning(f"  内容: {new_brief}")
                return False

            self.logger.info(f"  旧 brief: {old_brief[:50]}...")
            self.logger.info(f"  新 brief: {new_brief[:50]}...")

            if not dry_run:
                # 更新数据库
                table_name = self.db_manager.db_config.get('tables', {}).get('topic', 'twitter_topic')
                sql = f"""
                UPDATE {table_name}
                SET brief = %s, update_time = %s
                WHERE topic_id = %s
                """

                affected_rows = self.db_manager.execute_update(
                    sql,
                    (new_brief, datetime.now(), topic_id)
                )

                if affected_rows > 0:
                    self.logger.info(f"  ✓ 更新成功")
                    return True
                else:
                    self.logger.error(f"  ✗ 更新失败（无影响行）")
                    return False
            else:
                self.logger.info(f"  [模拟] 将更新 brief")
                return True

        except Exception as e:
            self.logger.error(f"  修复 topic brief 失败: {e}")
            return False

    def fix_all(self, hours: int = None, check_all: bool = False, dry_run: bool = False):
        """
        修复所有中文 brief

        Args:
            hours: 处理最近多少小时的数据
            check_all: 是否处理所有数据
            dry_run: 是否为模拟运行
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("开始修复中文 brief")
            if dry_run:
                self.logger.info("【模拟运行模式 - 不会修改数据库】")
            if check_all:
                self.logger.info("【检查所有数据】")
            elif hours:
                self.logger.info(f"【检查最近 {hours} 小时的数据】")
            self.logger.info("=" * 60)

            # 获取需要修复的 topic
            topics_to_fix = self.get_topics_to_fix(hours=hours, check_all=check_all)

            self.logger.info(f"总共检查: {self.total_checked} 个 topic")
            self.logger.info(f"发现中文 brief: {self.chinese_found} 个")

            if not topics_to_fix:
                self.logger.info("没有需要修复的 topic")
                return

            # 逐个修复
            for idx, topic in enumerate(topics_to_fix, 1):
                topic_id = topic['topic_id']
                topic_name = topic['topic_name']
                old_brief = topic['brief']
                update_time = topic['update_time']

                self.logger.info(f"\n[{idx}/{len(topics_to_fix)}] 修复 topic: {topic_name}")
                self.logger.info(f"  Topic ID: {topic_id}")
                self.logger.info(f"  更新时间: {update_time}")

                if self.fix_topic_brief(topic_id, topic_name, old_brief, dry_run):
                    self.fixed_count += 1
                else:
                    self.failed_count += 1

                # API 限流保护
                import time
                time.sleep(1)

            # 显示统计
            self.logger.info("\n" + "=" * 60)
            self.logger.info("修复完成！")
            self.logger.info(f"检查总数: {self.total_checked}")
            self.logger.info(f"发现中文: {self.chinese_found}")
            self.logger.info(f"修复成功: {self.fixed_count}")
            self.logger.info(f"修复失败: {self.failed_count}")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"修复中文 brief 失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='修复数据库中的中文 brief')
    parser.add_argument('--check', action='store_true',
                        help='只检查，不修复')
    parser.add_argument('--hours', type=int, default=None,
                        help='处理最近多少小时的数据')
    parser.add_argument('--all', action='store_true',
                        help='处理所有数据')
    parser.add_argument('--dry-run', action='store_true',
                        help='模拟运行（不修改数据库）')

    args = parser.parse_args()

    # 参数验证
    if not args.check and not args.hours and not args.all:
        print("错误：必须指定 --check、--hours 或 --all 参数")
        parser.print_help()
        sys.exit(1)

    # 创建修复器
    fixer = ChineseBriefFixer()
    logger = get_logger(__name__)

    # 测试数据库连接
    if not db_manager.test_connection():
        logger.error("数据库连接失败，请检查配置")
        sys.exit(1)

    logger.info("数据库连接成功\n")

    # 执行修复
    if args.check:
        # 只检查
        topics = fixer.get_topics_to_fix(hours=args.hours or 48, check_all=args.all)
        print(f"\n检查结果:")
        print(f"  总共检查: {fixer.total_checked} 个 topic")
        print(f"  发现中文 brief: {fixer.chinese_found} 个")

        if topics:
            print(f"\n需要修复的 topic（前10个）:")
            for topic in topics[:10]:
                print(f"  - {topic['topic_name']}: {topic['brief'][:50]}...")
    else:
        # 执行修复
        fixer.fix_all(hours=args.hours, check_all=args.all, dry_run=args.dry_run)

    sys.exit(0)


if __name__ == '__main__':
    main()
