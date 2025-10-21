#!/usr/bin/env python3
"""
批处理优化测试脚本
测试新的智能批处理和token节省效果
"""

import sys
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 添加项目路径
sys.path.append('.')

from src.api.chatgpt_client import chatgpt_client
from src.topic_engine import topic_engine
from src.database.tweet_dao import tweet_dao
from src.utils.logger import get_logger

class BatchOptimizationTester:
    """批处理优化测试器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.chatgpt_client = chatgpt_client
        self.topic_engine = topic_engine
        
    def test_batch_topic_extraction(self, tweet_count: int = 20) -> Dict[str, Any]:
        """
        测试批量话题提取效果
        
        Args:
            tweet_count: 测试推文数量
            
        Returns:
            测试结果统计
        """
        self.logger.info(f"开始测试批量话题提取，推文数量: {tweet_count}")
        
        # 获取测试推文
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        
        tweets = tweet_dao.get_tweets_by_date_range(
            start_date=start_time,
            end_date=end_time,
            limit=tweet_count
        )
        
        if not tweets:
            self.logger.error("没有找到测试推文")
            return {}
        
        self.logger.info(f"获取到 {len(tweets)} 条测试推文")
        
        # 重置统计信息
        self.chatgpt_client.request_count = 0
        self.chatgpt_client.success_count = 0
        self.chatgpt_client.error_count = 0
        
        # 测试1：传统逐个处理
        self.logger.info("=" * 50)
        self.logger.info("测试1: 传统逐个处理")
        
        start_time_traditional = time.time()
        traditional_results = []
        traditional_api_calls = 0
        
        for tweet in tweets[:10]:  # 测试前10条
            result = self.chatgpt_client.extract_topic_from_tweet(tweet.full_text)
            traditional_results.append(result)
            traditional_api_calls += 1
        
        traditional_duration = time.time() - start_time_traditional
        traditional_requests = self.chatgpt_client.request_count
        
        self.logger.info(f"传统方式完成，耗时: {traditional_duration:.2f}秒")
        self.logger.info(f"API调用次数: {traditional_requests}")
        
        # 重置统计
        self.chatgpt_client.request_count = 0
        
        # 测试2：新的批量处理
        self.logger.info("=" * 50)
        self.logger.info("测试2: 新的智能批量处理")
        
        start_time_batch = time.time()
        tweet_contents = [tweet.full_text for tweet in tweets[:10]]
        batch_results = self.chatgpt_client.batch_extract_topics_from_tweets(tweet_contents)
        
        batch_duration = time.time() - start_time_batch
        batch_requests = self.chatgpt_client.request_count
        
        self.logger.info(f"批量方式完成，耗时: {batch_duration:.2f}秒")
        self.logger.info(f"API调用次数: {batch_requests}")
        
        # 计算优化效果
        time_saved = traditional_duration - batch_duration
        time_saved_percent = (time_saved / traditional_duration) * 100 if traditional_duration > 0 else 0
        
        api_calls_saved = traditional_requests - batch_requests
        api_calls_saved_percent = (api_calls_saved / traditional_requests) * 100 if traditional_requests > 0 else 0
        
        results = {
            'test_tweet_count': 10,
            'traditional': {
                'duration_seconds': traditional_duration,
                'api_calls': traditional_requests,
                'results_count': len([r for r in traditional_results if r])
            },
            'batch_optimized': {
                'duration_seconds': batch_duration,
                'api_calls': batch_requests,
                'results_count': len([r for r in batch_results if r])
            },
            'optimization_effect': {
                'time_saved_seconds': time_saved,
                'time_saved_percent': time_saved_percent,
                'api_calls_saved': api_calls_saved,
                'api_calls_saved_percent': api_calls_saved_percent
            }
        }
        
        self.logger.info("=" * 50)
        self.logger.info("优化效果总结:")
        self.logger.info(f"时间节省: {time_saved:.2f}秒 ({time_saved_percent:.1f}%)")
        self.logger.info(f"API调用节省: {api_calls_saved} 次 ({api_calls_saved_percent:.1f}%)")
        
        return results
    
    def test_content_filtering(self, tweet_count: int = 50) -> Dict[str, Any]:
        """
        测试内容预筛选效果
        
        Args:
            tweet_count: 测试推文数量
            
        Returns:
            筛选效果统计
        """
        self.logger.info(f"开始测试内容预筛选，推文数量: {tweet_count}")
        
        # 获取测试推文
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=48)
        
        tweets = tweet_dao.get_tweets_by_date_range(
            start_date=start_time,
            end_date=end_time,
            limit=tweet_count
        )
        
        if not tweets:
            self.logger.error("没有找到测试推文")
            return {}
        
        original_count = len(tweets)
        filtered_tweets = self.topic_engine._filter_high_quality_tweets(tweets)
        filtered_count = len(filtered_tweets)
        
        filtered_out_count = original_count - filtered_count
        filter_rate = (filtered_out_count / original_count) * 100 if original_count > 0 else 0
        
        results = {
            'original_tweet_count': original_count,
            'filtered_tweet_count': filtered_count,
            'filtered_out_count': filtered_out_count,
            'filter_rate_percent': filter_rate,
            'potential_api_calls_saved': filtered_out_count
        }
        
        self.logger.info("=" * 50)
        self.logger.info("内容筛选效果:")
        self.logger.info(f"原始推文数: {original_count}")
        self.logger.info(f"筛选后推文数: {filtered_count}")
        self.logger.info(f"过滤掉推文数: {filtered_out_count}")
        self.logger.info(f"过滤率: {filter_rate:.1f}%")
        self.logger.info(f"潜在节省API调用: {filtered_out_count} 次")
        
        return results
    
    def test_cache_effectiveness(self, test_rounds: int = 3) -> Dict[str, Any]:
        """
        测试响应缓存效果
        
        Args:
            test_rounds: 测试轮数
            
        Returns:
            缓存效果统计
        """
        self.logger.info(f"开始测试响应缓存效果，测试轮数: {test_rounds}")
        
        # 准备测试内容
        test_tweets = [
            "Bitcoin is breaking new highs today! 🚀 #BTC",
            "Ethereum 2.0 staking rewards are impressive",
            "DeFi protocols are revolutionizing finance",
            "NFT market showing signs of recovery",
            "Bitcoin price action looks bullish"
        ]
        
        # 清空缓存
        if hasattr(self.chatgpt_client, 'response_cache'):
            self.chatgpt_client.response_cache.clear()
        
        cache_hits = 0
        total_requests = 0
        
        for round_num in range(test_rounds):
            self.logger.info(f"测试轮次 {round_num + 1}/{test_rounds}")
            
            # 重置请求计数
            initial_requests = self.chatgpt_client.request_count
            
            # 批量处理相同内容
            results = self.chatgpt_client.batch_extract_topics_from_tweets(test_tweets)
            
            # 计算实际API请求数
            actual_requests = self.chatgpt_client.request_count - initial_requests
            expected_requests = len(test_tweets) if round_num == 0 else 0  # 第一轮需要请求，后续轮次应该全部命中缓存
            
            if round_num > 0:
                cache_hits += len(test_tweets) - actual_requests
            
            total_requests += len(test_tweets)
            
            self.logger.info(f"轮次 {round_num + 1}: 实际API请求 {actual_requests}, 预期请求 {expected_requests}")
        
        cache_hit_rate = (cache_hits / max(total_requests - len(test_tweets), 1)) * 100  # 排除第一轮
        
        results = {
            'test_rounds': test_rounds,
            'total_potential_requests': total_requests,
            'cache_hits': cache_hits,
            'cache_hit_rate_percent': cache_hit_rate,
            'api_calls_saved': cache_hits
        }
        
        self.logger.info("=" * 50)
        self.logger.info("缓存效果:")
        self.logger.info(f"总潜在请求数: {total_requests}")
        self.logger.info(f"缓存命中数: {cache_hits}")
        self.logger.info(f"缓存命中率: {cache_hit_rate:.1f}%")
        self.logger.info(f"节省API调用: {cache_hits} 次")
        
        return results
    
    def run_complete_test(self) -> Dict[str, Any]:
        """
        运行完整的批处理优化测试
        
        Returns:
            完整测试结果
        """
        self.logger.info("开始运行完整的批处理优化测试")
        self.logger.info("=" * 60)
        
        results = {}
        
        try:
            # 测试1: 批量话题提取
            results['batch_topic_extraction'] = self.test_batch_topic_extraction()
            
            # 测试2: 内容预筛选
            results['content_filtering'] = self.test_content_filtering()
            
            # 测试3: 响应缓存
            results['cache_effectiveness'] = self.test_cache_effectiveness()
            
            # 计算总体优化效果
            total_api_calls_saved = (
                results['batch_topic_extraction']['optimization_effect']['api_calls_saved'] +
                results['content_filtering']['potential_api_calls_saved'] +
                results['cache_effectiveness']['api_calls_saved']
            )
            
            results['summary'] = {
                'total_api_calls_saved': total_api_calls_saved,
                'optimization_strategies_tested': 3,
                'test_completion_time': datetime.now().isoformat()
            }
            
            self.logger.info("=" * 60)
            self.logger.info("批处理优化测试完成")
            self.logger.info(f"总计节省API调用: {total_api_calls_saved} 次")
            
        except Exception as e:
            self.logger.error(f"测试过程中出现错误: {e}")
            results['error'] = str(e)
        
        return results

def main():
    """主函数"""
    print("批处理优化测试脚本")
    print("=" * 60)
    
    tester = BatchOptimizationTester()
    
    try:
        # 运行完整测试
        results = tester.run_complete_test()
        
        # 输出结果
        print("\n测试结果:")
        print("=" * 60)
        
        if 'error' not in results:
            # 批量处理测试结果
            batch_results = results.get('batch_topic_extraction', {})
            if batch_results:
                opt_effect = batch_results.get('optimization_effect', {})
                print(f"批量处理优化:")
                print(f"  - API调用节省: {opt_effect.get('api_calls_saved', 0)} 次 ({opt_effect.get('api_calls_saved_percent', 0):.1f}%)")
                print(f"  - 时间节省: {opt_effect.get('time_saved_seconds', 0):.2f} 秒 ({opt_effect.get('time_saved_percent', 0):.1f}%)")
            
            # 内容筛选测试结果
            filter_results = results.get('content_filtering', {})
            if filter_results:
                print(f"内容预筛选:")
                print(f"  - 过滤率: {filter_results.get('filter_rate_percent', 0):.1f}%")
                print(f"  - 潜在节省API调用: {filter_results.get('potential_api_calls_saved', 0)} 次")
            
            # 缓存测试结果
            cache_results = results.get('cache_effectiveness', {})
            if cache_results:
                print(f"响应缓存:")
                print(f"  - 缓存命中率: {cache_results.get('cache_hit_rate_percent', 0):.1f}%")
                print(f"  - 节省API调用: {cache_results.get('api_calls_saved', 0)} 次")
            
            # 总结
            summary = results.get('summary', {})
            print(f"\n总体优化效果:")
            print(f"  - 总计节省API调用: {summary.get('total_api_calls_saved', 0)} 次")
        else:
            print(f"测试失败: {results['error']}")
    
    except Exception as e:
        print(f"运行测试时出错: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
