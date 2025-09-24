#!/usr/bin/env python3
"""
修复孤立话题问题
清理没有对应推文的话题，或为孤立话题找到相关推文
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import datetime, timedelta
from typing import List, Dict

from src.database.topic_dao import topic_dao
from src.database.tweet_dao import tweet_dao
from src.utils.config_manager import config
from src.utils.logger import get_logger

class OrphanedTopicsFixer:
    """孤立话题修复器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.topic_dao = topic_dao
        self.tweet_dao = tweet_dao
        
        # 统计信息
        self.stats = {
            'orphaned_topics_found': 0,
            'topics_linked': 0,
            'topics_deleted': 0,
            'tweets_updated': 0
        }
    
    def check_and_fix_orphaned_topics(self, delete_orphaned: bool = False, dry_run: bool = True) -> Dict:
        """
        检查并修复孤立话题
        
        Args:
            delete_orphaned: 是否删除无法关联的孤立话题
            dry_run: 是否为试运行模式（不实际执行修改）
            
        Returns:
            修复统计信息
        """
        self.logger.info("开始检查和修复孤立话题...")
        
        if dry_run:
            self.logger.info("=== 试运行模式 - 不会实际修改数据 ===")
        
        # 1. 查找孤立话题
        orphaned_topics = self._find_orphaned_topics()
        self.stats['orphaned_topics_found'] = len(orphaned_topics)
        
        if not orphaned_topics:
            self.logger.info("没有发现孤立话题")
            return self.stats
        
        self.logger.info(f"发现 {len(orphaned_topics)} 个孤立话题")
        
        # 2. 尝试为孤立话题找到相关推文
        for topic in orphaned_topics:
            self.logger.info(f"处理孤立话题: {topic.topic_name} (ID: {topic.topic_id})")
            
            # 查找相关推文
            related_tweets = self._find_tweets_for_topic(topic)
            
            if related_tweets:
                self.logger.info(f"为话题 {topic.topic_name} 找到 {len(related_tweets)} 条相关推文")
                
                if not dry_run:
                    # 更新推文的topic_id
                    updated_count = self._update_tweets_topic_id(related_tweets, topic.topic_id)
                    self.stats['tweets_updated'] += updated_count
                    self.stats['topics_linked'] += 1
                    
                    self.logger.info(f"成功将 {updated_count} 条推文关联到话题 {topic.topic_name}")
                else:
                    self.logger.info(f"[试运行] 将更新 {len(related_tweets)} 条推文关联到话题 {topic.topic_name}")
                    self.stats['topics_linked'] += 1
                    
            else:
                self.logger.warning(f"话题 {topic.topic_name} 未找到相关推文")
                
                if delete_orphaned:
                    if not dry_run:
                        # 删除孤立话题
                        if self.topic_dao.delete_topic(topic.topic_id):
                            self.stats['topics_deleted'] += 1
                            self.logger.info(f"删除孤立话题: {topic.topic_name}")
                        else:
                            self.logger.error(f"删除孤立话题失败: {topic.topic_name}")
                    else:
                        self.logger.info(f"[试运行] 将删除孤立话题: {topic.topic_name}")
                        self.stats['topics_deleted'] += 1
        
        # 3. 输出统计信息
        self._print_stats()
        
        return self.stats
    
    def _find_orphaned_topics(self) -> List:
        """
        查找孤立话题（存在于话题表但推文表中没有对应推文的话题）
        
        Returns:
            孤立话题列表
        """
        try:
            # SQL查询孤立话题
            sql = """
            SELECT t.topic_id, t.topic_name, t.created_at, t.popularity, t.key_entities
            FROM topics t
            LEFT JOIN twitter_tweet tw ON t.topic_id = tw.topic_id
            WHERE tw.topic_id IS NULL
            ORDER BY t.created_at DESC
            """
            
            results = self.topic_dao.db_manager.execute_query(sql, ())
            
            orphaned_topics = []
            for row in results:
                # 构造简化的话题对象
                topic = type('Topic', (), {
                    'topic_id': row['topic_id'],
                    'topic_name': row['topic_name'],
                    'created_at': row['created_at'],
                    'popularity': row['popularity'],
                    'key_entities': row['key_entities'] or ''
                })()
                orphaned_topics.append(topic)
            
            return orphaned_topics
            
        except Exception as e:
            self.logger.error(f"查找孤立话题失败: {e}")
            return []
    
    def _find_tweets_for_topic(self, topic) -> List:
        """
        为话题查找相关推文
        
        Args:
            topic: 话题对象
            
        Returns:
            相关推文列表
        """
        try:
            # 1. 基于话题名称关键词搜索
            topic_keywords = topic.topic_name.lower().split()
            
            # 2. 如果有key_entities，也加入搜索
            if topic.key_entities:
                entity_keywords = topic.key_entities.lower().split()
                topic_keywords.extend(entity_keywords)
            
            # 去重
            topic_keywords = list(set(topic_keywords))
            
            # 3. 搜索最近7天内的推文（避免关联太久远的推文）
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)
            
            recent_tweets = self.tweet_dao.get_tweets_by_date_range(
                start_date=start_time,
                end_date=end_time,
                limit=500
            )
            
            # 4. 筛选相关推文
            related_tweets = []
            for tweet in recent_tweets:
                # 只处理没有topic_id和project_id的推文
                if tweet.topic_id or tweet.project_id:
                    continue
                
                if not tweet.full_text:
                    continue
                
                tweet_text = tweet.full_text.lower()
                
                # 检查是否包含话题关键词
                matches = 0
                for keyword in topic_keywords:
                    if len(keyword) > 2 and keyword in tweet_text:
                        matches += 1
                
                # 如果匹配到足够的关键词，认为是相关推文
                if matches >= min(2, len(topic_keywords)):
                    related_tweets.append(tweet)
            
            # 限制数量，避免过度关联
            return related_tweets[:20]
            
        except Exception as e:
            self.logger.error(f"为话题查找相关推文失败: {topic.topic_name}, 错误: {e}")
            return []
    
    def _update_tweets_topic_id(self, tweets: List, topic_id: str) -> int:
        """
        更新推文的topic_id
        
        Args:
            tweets: 推文列表
            topic_id: 话题ID
            
        Returns:
            成功更新的数量
        """
        try:
            updated_count = 0
            
            for tweet in tweets:
                update_sql = f"""
                UPDATE {self.tweet_dao.table_name} 
                SET topic_id = %s, update_time = %s 
                WHERE id_str = %s AND (topic_id IS NULL OR topic_id = '') AND (project_id IS NULL OR project_id = '')
                """
                
                affected_rows = self.tweet_dao.db_manager.execute_update(
                    update_sql, 
                    (topic_id, datetime.now(), tweet.id_str)
                )
                
                if affected_rows > 0:
                    updated_count += 1
            
            return updated_count
            
        except Exception as e:
            self.logger.error(f"更新推文topic_id失败: {e}")
            return 0
    
    def _print_stats(self):
        """打印统计信息"""
        self.logger.info("=== 孤立话题修复统计 ===")
        self.logger.info(f"发现孤立话题: {self.stats['orphaned_topics_found']} 个")
        self.logger.info(f"成功关联话题: {self.stats['topics_linked']} 个")
        self.logger.info(f"更新推文数量: {self.stats['tweets_updated']} 条")
        self.logger.info(f"删除话题数量: {self.stats['topics_deleted']} 个")
        self.logger.info("=======================")
    
    def check_data_consistency(self) -> Dict:
        """
        检查数据一致性
        
        Returns:
            一致性检查结果
        """
        self.logger.info("开始数据一致性检查...")
        
        consistency_stats = {
            'total_topics': 0,
            'total_tweets': 0,
            'tweets_with_topic_id': 0,
            'tweets_with_project_id': 0,
            'tweets_with_both': 0,
            'tweets_with_neither': 0,
            'orphaned_topics': 0,
            'topics_without_tweets': 0
        }
        
        try:
            # 话题总数
            consistency_stats['total_topics'] = self.topic_dao.get_topic_count()
            
            # 推文统计
            tweet_stats_sql = """
            SELECT 
                COUNT(*) as total_tweets,
                SUM(CASE WHEN topic_id IS NOT NULL AND topic_id != '' THEN 1 ELSE 0 END) as with_topic_id,
                SUM(CASE WHEN project_id IS NOT NULL AND project_id != '' THEN 1 ELSE 0 END) as with_project_id,
                SUM(CASE WHEN (topic_id IS NOT NULL AND topic_id != '') AND (project_id IS NOT NULL AND project_id != '') THEN 1 ELSE 0 END) as with_both,
                SUM(CASE WHEN (topic_id IS NULL OR topic_id = '') AND (project_id IS NULL OR project_id = '') THEN 1 ELSE 0 END) as with_neither
            FROM twitter_tweet
            """
            
            result = self.tweet_dao.db_manager.execute_query(tweet_stats_sql, ())
            if result:
                row = result[0]
                consistency_stats['total_tweets'] = row['total_tweets']
                consistency_stats['tweets_with_topic_id'] = row['with_topic_id']
                consistency_stats['tweets_with_project_id'] = row['with_project_id']
                consistency_stats['tweets_with_both'] = row['with_both']
                consistency_stats['tweets_with_neither'] = row['with_neither']
            
            # 孤立话题数量
            orphaned_topics = self._find_orphaned_topics()
            consistency_stats['orphaned_topics'] = len(orphaned_topics)
            
            # 输出一致性检查结果
            self.logger.info("=== 数据一致性检查结果 ===")
            self.logger.info(f"话题总数: {consistency_stats['total_topics']}")
            self.logger.info(f"推文总数: {consistency_stats['total_tweets']}")
            self.logger.info(f"有topic_id的推文: {consistency_stats['tweets_with_topic_id']}")
            self.logger.info(f"有project_id的推文: {consistency_stats['tweets_with_project_id']}")
            self.logger.info(f"同时有两者的推文: {consistency_stats['tweets_with_both']}")
            self.logger.info(f"两者都没有的推文: {consistency_stats['tweets_with_neither']}")
            self.logger.info(f"孤立话题数量: {consistency_stats['orphaned_topics']}")
            self.logger.info("=========================")
            
            return consistency_stats
            
        except Exception as e:
            self.logger.error(f"数据一致性检查失败: {e}")
            return consistency_stats


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='修复孤立话题问题')
    parser.add_argument('--action', choices=['check', 'fix', 'fix-and-delete'], 
                       default='check', help='执行的操作')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='试运行模式，不实际修改数据')
    parser.add_argument('--execute', action='store_true', 
                       help='实际执行修改（覆盖dry-run）')
    
    args = parser.parse_args()
    
    # 如果明确指定execute，则关闭dry-run
    if args.execute:
        args.dry_run = False
    
    fixer = OrphanedTopicsFixer()
    
    if args.action == 'check':
        # 只进行一致性检查
        fixer.check_data_consistency()
        fixer.check_and_fix_orphaned_topics(delete_orphaned=False, dry_run=True)
        
    elif args.action == 'fix':
        # 修复孤立话题（不删除）
        fixer.check_and_fix_orphaned_topics(delete_orphaned=False, dry_run=args.dry_run)
        
    elif args.action == 'fix-and-delete':
        # 修复孤立话题（删除无法关联的）
        fixer.check_and_fix_orphaned_topics(delete_orphaned=True, dry_run=args.dry_run)
    
    print("\n使用说明:")
    print("python fix_orphaned_topics.py --action check                    # 检查数据一致性")
    print("python fix_orphaned_topics.py --action fix                      # 试运行修复")
    print("python fix_orphaned_topics.py --action fix --execute            # 实际执行修复")
    print("python fix_orphaned_topics.py --action fix-and-delete --execute # 修复并删除无法关联的话题")


if __name__ == "__main__":
    main()