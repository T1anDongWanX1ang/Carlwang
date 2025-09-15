#!/usr/bin/env python3
"""
分析所有现有用户，识别KOL
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


def analyze_all_users():
    """分析所有现有用户"""
    logger = get_logger(__name__)
    
    logger.info("开始分析所有现有用户，识别KOL...")
    
    try:
        # 1. 获取用户总数
        total_users = user_dao.get_user_count()
        logger.info(f"数据库中总用户数: {total_users}")
        
        if total_users == 0:
            logger.error("数据库中没有用户数据")
            return False
        
        # 2. 获取高粉丝用户
        logger.info("获取高粉丝用户...")
        high_follower_users = user_dao.get_top_users_by_followers(limit=30)
        logger.info(f"获取到 {len(high_follower_users)} 个高粉丝用户")
        
        # 显示用户信息
        logger.info("\n高粉丝用户列表:")
        for i, user in enumerate(high_follower_users[:10], 1):
            logger.info(f"  {i}. @{user.screen_name}: {user.followers_count:,} 粉丝")
        
        # 3. 分批分析用户
        logger.info(f"\n开始分析 {len(high_follower_users)} 个用户...")
        
        # 分析参数
        min_followers = 5000  # 降低门槛以识别更多KOL
        max_users = len(high_follower_users)
        
        success = kol_engine.analyze_all_users_as_kols(
            min_followers=min_followers, 
            max_users=max_users
        )
        
        if not success:
            logger.error("KOL分析失败")
            return False
        
        # 4. 显示分析结果
        logger.info("\n=== KOL分析结果 ===")
        
        # 获取统计信息
        stats = kol_engine.get_kol_statistics()
        logger.info(f"分析执行次数: {stats.get('analysis_count', 0)}")
        logger.info(f"成功次数: {stats.get('success_count', 0)}")
        logger.info(f"成功率: {stats.get('success_rate', 0):.1f}%")
        logger.info(f"识别的KOL数: {stats.get('kols_identified', 0)}")
        logger.info(f"数据库中KOL总数: {stats.get('total_kols_in_db', 0)}")
        logger.info(f"KOL100数量: {stats.get('kol100_count', 0)}")
        
        # 显示ChatGPT使用统计
        chatgpt_stats = stats.get('chatgpt_stats', {})
        logger.info(f"ChatGPT请求数: {chatgpt_stats.get('chatgpt_requests', 0)}")
        logger.info(f"ChatGPT成功率: {chatgpt_stats.get('chatgpt_success_rate', 0):.1f}%")
        
        # 5. 显示识别的KOL
        kol_count = kol_dao.get_kol_count()
        if kol_count > 0:
            logger.info(f"\n=== 识别的KOL ({kol_count}个) ===")
            
            # 按类型显示
            for kol_type in ['founder', 'influencer', 'investor', 'trader', 'analyst']:
                type_kols = kol_dao.get_kols_by_type(kol_type, limit=10)
                if type_kols:
                    logger.info(f"\n{kol_type.upper()} ({len(type_kols)}个):")
                    for kol in type_kols:
                        user = user_dao.get_user_by_id(kol.kol_id)
                        screen_name = user.screen_name if user else "unknown"
                        followers = user.followers_count if user else 0
                        
                        logger.info(f"  @{screen_name}")
                        logger.info(f"    影响力: {kol.influence_score}")
                        logger.info(f"    标签: {kol.tag}")
                        logger.info(f"    情感: {kol.sentiment}")
                        logger.info(f"    粉丝: {followers:,}")
                        logger.info(f"    KOL100: {'是' if kol.is_kol100 else '否'}")
                        if kol.summary:
                            logger.info(f"    总结: {kol.summary[:60]}...")
        
        # 6. 显示KOL100列表
        kol100_list = kol_dao.get_kol100_list()
        if kol100_list:
            logger.info(f"\n=== KOL100指数成员 ({len(kol100_list)}个) ===")
            for i, kol in enumerate(kol100_list[:5], 1):
                user = user_dao.get_user_by_id(kol.kol_id)
                screen_name = user.screen_name if user else "unknown"
                logger.info(f"  {i}. @{screen_name} (影响力: {kol.influence_score})")
        
        return True
        
    except Exception as e:
        logger.error(f"分析所有用户失败: {e}")
        return False


def main():
    """主函数"""
    logger = get_logger(__name__)
    
    logger.info("所有用户KOL分析工具")
    logger.info("=" * 50)
    
    # 运行分析
    if analyze_all_users():
        logger.info("所有用户KOL分析完成")
    else:
        logger.error("所有用户KOL分析失败")
        sys.exit(1)


if __name__ == '__main__':
    main() 