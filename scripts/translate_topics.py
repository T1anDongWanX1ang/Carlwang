#!/usr/bin/env python3
"""
翻译 topics 表中的中文内容为英文
用于处理过去48小时内更新的、topic_name 和 brief 为中文的记录
"""
import sys
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.connection import db_manager
from src.api.chatgpt_client import ChatGPTClient


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('translate_topics.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def is_chinese(text: str) -> bool:
    """
    检测文本是否主要是中文

    Args:
        text: 文本内容

    Returns:
        是否为中文
    """
    if not text:
        return False

    # 统计中文字符
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    total_chars = len(re.findall(r'[\w\u4e00-\u9fff]', text))

    if total_chars == 0:
        return False

    chinese_ratio = len(chinese_chars) / total_chars

    # 如果中文字符占比超过30%，认为是中文内容
    return chinese_ratio > 0.3


def get_chinese_topics_from_last_48h() -> List[Dict[str, Any]]:
    """
    获取过去48小时内更新的中文topics

    Returns:
        中文topics列表
    """
    try:
        # 计算48小时前的时间
        start_time = datetime.now() - timedelta(hours=48)

        # 查询过去48小时内更新的topics
        sql = """
        SELECT
            topic_id,
            topic_name,
            brief,
            update_time
        FROM public_data.topics
        WHERE update_time >= %s
        AND topic_name IS NOT NULL
        AND brief IS NOT NULL
        ORDER BY update_time DESC
        """

        results = db_manager.execute_query(sql, (start_time,))

        if not results:
            logger.info("未找到过去48小时内更新的topics")
            return []

        logger.info(f"查询到 {len(results)} 条topics（过去48小时）")

        # 筛选中文内容
        chinese_topics = []
        for topic in results:
            topic_name = topic.get('topic_name', '')
            brief = topic.get('brief', '')

            # 检查是否为中文
            is_name_chinese = is_chinese(topic_name)
            is_brief_chinese = is_chinese(brief)

            if is_name_chinese or is_brief_chinese:
                chinese_topics.append({
                    'topic_id': topic['topic_id'],
                    'topic_name': topic_name,
                    'brief': brief,
                    'update_time': topic['update_time'],
                    'is_name_chinese': is_name_chinese,
                    'is_brief_chinese': is_brief_chinese
                })
                logger.debug(f"识别到中文topic: {topic['topic_id']}, name={is_name_chinese}, brief={is_brief_chinese}")

        logger.info(f"筛选出 {len(chinese_topics)} 条中文topics")
        return chinese_topics

    except Exception as e:
        logger.error(f"查询topics失败: {e}")
        return []


def translate_text(chatgpt_client: ChatGPTClient, text: str, context: str = "topic") -> Optional[str]:
    """
    使用ChatGPT翻译文本

    Args:
        chatgpt_client: ChatGPT客户端
        text: 要翻译的文本
        context: 上下文（topic/brief）

    Returns:
        翻译后的文本，失败返回None
    """
    try:
        if context == "topic":
            prompt = f"""
Please translate the following Chinese cryptocurrency topic name to English:

Chinese: {text}

Requirements:
1. Keep it concise and professional
2. Preserve technical terms in their common English forms (e.g., DeFi, NFT, Layer2)
3. Use standard cryptocurrency industry terminology
4. Return ONLY the translated text without any additional explanation

Translation:
"""
        else:  # brief
            prompt = f"""
Please translate the following Chinese cryptocurrency topic description to English:

Chinese: {text}

Requirements:
1. Keep it concise and clear
2. Preserve technical terms and project names in their common English forms
3. Use standard cryptocurrency industry terminology
4. Maintain the original meaning and tone
5. Return ONLY the translated text without any additional explanation

Translation:
"""

        messages = [
            {"role": "system", "content": "You are a professional translator specializing in cryptocurrency and blockchain content. You provide accurate, concise translations while preserving technical terminology."},
            {"role": "user", "content": prompt}
        ]

        response = chatgpt_client._make_request(
            messages=messages,
            temperature=0.3,
            max_tokens=200
        )

        if response:
            translation = response.strip()
            # 移除可能的引号
            translation = translation.strip('"\'')
            logger.debug(f"翻译: {text[:50]}... -> {translation[:50]}...")
            return translation

        return None

    except Exception as e:
        logger.error(f"翻译失败: {e}")
        return None


def update_topic_translation(topic_id: str, topic_name_en: str = None, brief_en: str = None) -> bool:
    """
    更新topic的翻译

    Args:
        topic_id: Topic ID
        topic_name_en: 英文topic名称（None表示不更新）
        brief_en: 英文brief（None表示不更新）

    Returns:
        是否更新成功
    """
    try:
        # 构建更新语句
        update_fields = []
        params = []

        if topic_name_en is not None:
            update_fields.append("topic_name = %s")
            params.append(topic_name_en)

        if brief_en is not None:
            update_fields.append("brief = %s")
            params.append(brief_en)

        if not update_fields:
            logger.warning(f"Topic {topic_id}: 没有需要更新的字段")
            return False

        # 添加update_time
        update_fields.append("update_time = %s")
        params.append(datetime.now())

        # 添加topic_id到参数
        params.append(topic_id)

        sql = f"""
        UPDATE public_data.topics
        SET {', '.join(update_fields)}
        WHERE topic_id = %s
        """

        affected_rows = db_manager.execute_update(sql, tuple(params))

        if affected_rows > 0:
            logger.debug(f"Topic {topic_id} 更新成功")
            return True
        else:
            logger.warning(f"Topic {topic_id} 更新失败（可能不存在）")
            return False

    except Exception as e:
        logger.error(f"更新Topic {topic_id} 失败: {e}")
        return False


def translate_topics(topics: List[Dict[str, Any]], batch_size: int = 10) -> Dict[str, int]:
    """
    批量翻译topics

    Args:
        topics: topics列表
        batch_size: 批处理大小（用于进度显示）

    Returns:
        统计信息
    """
    chatgpt_client = ChatGPTClient()

    stats = {
        'total': len(topics),
        'name_translated': 0,
        'brief_translated': 0,
        'updated': 0,
        'failed': 0,
        'skipped': 0
    }

    logger.info(f"开始翻译 {len(topics)} 条topics...")

    for i, topic in enumerate(topics):
        try:
            topic_id = topic['topic_id']
            topic_name = topic['topic_name']
            brief = topic['brief']
            is_name_chinese = topic['is_name_chinese']
            is_brief_chinese = topic['is_brief_chinese']

            logger.info(f"处理 {i+1}/{len(topics)}: {topic_id}")

            topic_name_en = None
            brief_en = None

            # 翻译topic_name
            if is_name_chinese:
                logger.info(f"  翻译topic_name: {topic_name}")
                topic_name_en = translate_text(chatgpt_client, topic_name, context="topic")
                if topic_name_en:
                    stats['name_translated'] += 1
                    logger.info(f"  ✓ topic_name: {topic_name} -> {topic_name_en}")
                else:
                    logger.warning(f"  ✗ topic_name翻译失败")

            # 翻译brief
            if is_brief_chinese:
                logger.info(f"  翻译brief: {brief[:50]}...")
                brief_en = translate_text(chatgpt_client, brief, context="brief")
                if brief_en:
                    stats['brief_translated'] += 1
                    logger.info(f"  ✓ brief翻译完成")
                else:
                    logger.warning(f"  ✗ brief翻译失败")

            # 更新数据库
            if topic_name_en or brief_en:
                if update_topic_translation(topic_id, topic_name_en, brief_en):
                    stats['updated'] += 1
                    logger.info(f"  ✓ 数据库更新成功")
                else:
                    stats['failed'] += 1
                    logger.error(f"  ✗ 数据库更新失败")
            else:
                stats['skipped'] += 1
                logger.info(f"  - 跳过（翻译失败）")

            # 每处理batch_size条输出一次进度
            if (i + 1) % batch_size == 0:
                logger.info(f"进度: {i+1}/{len(topics)} ({(i+1)*100//len(topics)}%)")
                logger.info(f"统计: name={stats['name_translated']}, brief={stats['brief_translated']}, "
                          f"updated={stats['updated']}, failed={stats['failed']}, skipped={stats['skipped']}")

        except Exception as e:
            logger.error(f"处理topic {topic.get('topic_id')} 时出错: {e}")
            stats['failed'] += 1
            continue

    return stats


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='翻译topics表中的中文内容为英文')
    parser.add_argument('--hours', type=int, default=48, help='回溯小时数（默认48小时）')
    parser.add_argument('--batch-size', type=int, default=10, help='批处理大小（默认10）')
    parser.add_argument('--dry-run', action='store_true', help='试运行模式（不更新数据库）')

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("开始翻译topics中文内容为英文")
    logger.info(f"参数: hours={args.hours}, batch_size={args.batch_size}, dry_run={args.dry_run}")
    logger.info("=" * 80)

    # 获取中文topics
    topics = get_chinese_topics_from_last_48h()

    if not topics:
        logger.warning("没有找到需要翻译的中文topics")
        return

    # 显示待翻译列表
    logger.info("\n待翻译topics列表:")
    for i, topic in enumerate(topics[:10], 1):  # 只显示前10条
        logger.info(f"  {i}. {topic['topic_id']}")
        logger.info(f"     topic_name: {topic['topic_name'][:50]}... (中文={topic['is_name_chinese']})")
        logger.info(f"     brief: {topic['brief'][:50]}... (中文={topic['is_brief_chinese']})")

    if len(topics) > 10:
        logger.info(f"  ... 还有 {len(topics) - 10} 条")

    # 试运行模式
    if args.dry_run:
        logger.info("\n⚠️  试运行模式：不会实际更新数据库")
        logger.info(f"共找到 {len(topics)} 条需要翻译的topics")
        return

    # 确认执行
    logger.info(f"\n将翻译 {len(topics)} 条topics，是否继续？")
    logger.info("提示: 按 Ctrl+C 可以中断执行")

    import time
    time.sleep(2)  # 给用户2秒时间考虑

    # 执行翻译
    stats = translate_topics(topics, batch_size=args.batch_size)

    # 输出最终统计
    logger.info("=" * 80)
    logger.info("翻译完成！")
    logger.info(f"总数: {stats['total']}")
    logger.info(f"topic_name翻译: {stats['name_translated']}")
    logger.info(f"brief翻译: {stats['brief_translated']}")
    logger.info(f"数据库更新成功: {stats['updated']}")
    logger.info(f"数据库更新失败: {stats['failed']}")
    logger.info(f"跳过: {stats['skipped']}")
    logger.info(f"成功率: {stats['updated']*100/max(stats['total'], 1):.2f}%")
    logger.info("=" * 80)


if __name__ == '__main__':
    main()
