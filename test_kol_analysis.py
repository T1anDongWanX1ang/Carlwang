#!/usr/bin/env python3
"""
KOL分析测试脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.kol_engine import kol_engine
from src.database.user_dao import user_dao
from src.database.kol_dao import kol_dao
from src.utils.logger import get_logger


def test_kol_analysis():
    """测试KOL分析功能"""
    logger = get_logger(__name__)
    
    logger.info("开始测试KOL分析功能...")
    
    try:
        # 1. 检查用户数据
        user_count = user_dao.get_user_count()
        logger.info(f"数据库中用户总数: {user_count}")
        
        if user_count == 0:
            logger.error("数据库中没有用户数据，请先运行爬虫获取用户")
            return False
        
        # 2. 获取一些高粉丝用户进行测试
        top_users = user_dao.get_top_users_by_followers(limit=10)
        logger.info(f"获取到 {len(top_users)} 个高粉丝用户用于测试")
        
        for i, user in enumerate(top_users[:3], 1):
            logger.info(f"  {i}. @{user.screen_name}: {user.followers_count:,} 粉丝")
        
        # 3. 测试ChatGPT KOL分析
        logger.info("\n3. 测试ChatGPT KOL分析...")
        if top_users:
            test_user = top_users[0]
            user_info = {
                'screen_name': test_user.screen_name,
                'name': test_user.name,
                'followers_count': test_user.followers_count,
                'friends_count': test_user.friends_count,
                'statuses_count': test_user.statuses_count,
                'description': test_user.description
            }
            
            # 模拟一些推文内容进行测试
            test_tweets = [
                "Bitcoin is going to $100k this cycle! #BTC #crypto",
                "Just bought more ETH, DeFi is the future",
                "New project launching soon, DYOR"
            ]
            
            kol_analysis = kol_engine.kol_analyzer.chatgpt_client.analyze_kol_profile(user_info, test_tweets)
            
            if kol_analysis:
                logger.info(f"ChatGPT KOL分析成功: {kol_analysis}")
            else:
                logger.warning("ChatGPT判断该用户不是KOL或分析失败")
        
        # 4. 运行KOL分析（少量用户测试）
        logger.info("\n4. 运行KOL识别分析...")
        success = kol_engine.analyze_all_users_as_kols(min_followers=10000, max_users=5)
        
        if success:
            logger.info("KOL分析执行成功")
        else:
            logger.error("KOL分析执行失败")
            return False
        
        # 5. 检查生成的KOL
        logger.info("\n5. 检查识别的KOL...")
        kol_count = kol_dao.get_kol_count()
        logger.info(f"数据库中KOL总数: {kol_count}")
        
        if kol_count > 0:
            # 显示一些KOL样例
            top_kols = kol_dao.get_top_kols_by_influence(limit=3)
            logger.info("\n顶级KOL样例:")
            for i, kol in enumerate(top_kols, 1):
                user = user_dao.get_user_by_id(kol.kol_id)
                screen_name = user.screen_name if user else "unknown"
                
                logger.info(f"  KOL {i}: @{screen_name}")
                logger.info(f"    类型: {kol.type}")
                logger.info(f"    标签: {kol.tag}")
                logger.info(f"    影响力: {kol.influence_score}")
                logger.info(f"    情感: {kol.sentiment}")
                logger.info(f"    信任度: {kol.trust_rating}")
                logger.info(f"    KOL100: {'是' if kol.is_kol100 else '否'}")
                if kol.summary:
                    logger.info(f"    总结: {kol.summary[:100]}...")
        
        # 6. 显示统计信息
        logger.info("\n6. KOL分析统计信息:")
        stats = kol_engine.get_kol_statistics()
        for key, value in stats.items():
            if key not in ['type_distribution', 'sentiment_distribution']:  # 跳过复杂嵌套数据
                logger.info(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"KOL分析测试失败: {e}")
        return False


def main():
    """主函数"""
    logger = get_logger(__name__)
    
    logger.info("KOL分析测试工具")
    logger.info("=" * 40)
    
    # 运行KOL分析测试
    if test_kol_analysis():
        logger.info("KOL分析测试成功")
    else:
        logger.error("KOL分析测试失败")
        sys.exit(1)


if __name__ == '__main__':
    main() 