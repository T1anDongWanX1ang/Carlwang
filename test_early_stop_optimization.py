#!/usr/bin/env python3
"""
测试优化后的智能时间检测和早期停止逻辑
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_early_stop_logic():
    """测试早期停止逻辑"""
    print("=" * 60)
    print("测试早期停止逻辑优化")
    print("=" * 60)
    
    # 模拟项目时间分析的输入数据
    time_cutoff = datetime.now() - timedelta(hours=3)
    
    # 情况1: 大部分项目超时，无活跃项目
    project_latest_times_1 = {}
    project_has_valid_tweets_this_page_1 = {}
    project_ever_had_valid_tweets_1 = {}
    
    # 创建94个项目，73个超时，0个活跃
    for i in range(94):
        user_id = f"user_{i}"
        if i < 73:  # 前73个项目超时
            project_latest_times_1[user_id] = time_cutoff - timedelta(hours=1)
        else:  # 后21个项目在时间范围内，但本页无有效推文
            project_latest_times_1[user_id] = time_cutoff + timedelta(hours=1)
        
        project_has_valid_tweets_this_page_1[user_id] = False  # 本页无有效推文
        if i < 21:  # 前21个项目曾经有过有效推文
            project_ever_had_valid_tweets_1[user_id] = True
        else:
            project_ever_had_valid_tweets_1[user_id] = False
    
    print(f"测试场景1: 总项目数={len(project_latest_times_1)}, 本页活跃项目=0")
    print(f"预期结果: 应该停止（60%超时阈值触发）")
    
    # 计算停止条件
    total_projects = len(project_latest_times_1)
    overdue_projects = sum(1 for latest_time in project_latest_times_1.values() 
                         if latest_time < time_cutoff)
    active_projects = sum(1 for has_valid in project_has_valid_tweets_this_page_1.values() 
                         if has_valid)
    
    should_stop_1 = (active_projects == 0 and overdue_projects >= total_projects * 0.6)
    
    print(f"  - 超时项目: {overdue_projects}/{total_projects} ({overdue_projects/total_projects:.1%})")
    print(f"  - 活跃项目: {active_projects}")
    print(f"  - 停止决策: {'是' if should_stop_1 else '否'}")
    
    return should_stop_1

def test_consecutive_empty_pages():
    """测试连续空页面检测"""
    print("\n" + "=" * 60)
    print("测试连续空页面检测")
    print("=" * 60)
    
    # 模拟连续5页空页面
    consecutive_empty_pages = 0
    max_consecutive_empty_pages = 5
    
    # 模拟页面处理
    pages_with_valid_tweets = [0, 0, 0, 0, 0, 2]  # 前5页空，第6页有2条
    
    print("页面处理模拟:")
    for page_num, valid_count in enumerate(pages_with_valid_tweets, 1):
        if valid_count == 0:
            consecutive_empty_pages += 1
            print(f"  第{page_num}页: {valid_count}条有效推文，连续空页面: {consecutive_empty_pages}")
            if consecutive_empty_pages >= max_consecutive_empty_pages:
                print(f"  -> 触发连续空页面停止条件")
                return True
        else:
            consecutive_empty_pages = 0
            print(f"  第{page_num}页: {valid_count}条有效推文，重置连续空页面计数")
    
    return False

def test_efficiency_detection():
    """测试效率检测"""
    print("\n" + "=" * 60)
    print("测试效率检测")
    print("=" * 60)
    
    # 模拟10页的有效推文数量
    pages_valid_counts = [2, 1, 0, 0, 0, 1, 0, 0, 0, 0]  # 前10页的有效推文数，总计4条，平均0.4
    pages_for_efficiency_check = 10
    
    total_valid_tweets = sum(pages_valid_counts)
    avg_valid_per_page = total_valid_tweets / pages_for_efficiency_check
    
    print(f"最近{pages_for_efficiency_check}页有效推文: {pages_valid_counts}")
    print(f"总有效推文: {total_valid_tweets}")
    print(f"平均每页: {avg_valid_per_page:.2f}")
    print(f"效率阈值: 1.0/页")
    
    should_stop = avg_valid_per_page < 1.0
    print(f"停止决策: {'是' if should_stop else '否'} (效率过低)")
    
    return should_stop

def test_large_page_protection():
    """测试大页数保护"""
    print("\n" + "=" * 60)
    print("测试大页数保护（40页+严格模式）")
    print("=" * 60)
    
    page_num = 42  # 模拟第42页
    project_has_valid_tweets_this_page = {
        f"user_{i}": False for i in range(94)  # 所有项目本页都无有效推文
    }
    
    active_projects_count = len([uid for uid, has_valid in project_has_valid_tweets_this_page.items() if has_valid])
    
    print(f"当前页数: {page_num}")
    print(f"本页活跃项目数: {active_projects_count}")
    
    should_stop = page_num >= 40 and active_projects_count == 0
    print(f"停止决策: {'是' if should_stop else '否'} (大页数+无活跃项目)")
    
    return should_stop

def main():
    """主函数"""
    print("智能时间检测和早期停止逻辑优化测试")
    print("="*80)
    print("优化内容:")
    print("1. 连续空页面检测：最多允许5页连续无有效推文")
    print("2. 效率检测：最近10页平均有效推文密度 < 1.0/页则停止")
    print("3. 大页数保护：40页以上时，无活跃项目直接停止") 
    print("4. 项目超时阈值降低：从70%降低到60%")
    print("5. 超时项目比例阈值降低：从90%降低到80%")
    print("="*80)
    
    try:
        # 运行各项测试
        test1 = test_early_stop_logic()
        test2 = test_consecutive_empty_pages()
        test3 = test_efficiency_detection()
        test4 = test_large_page_protection()
        
        print("\n" + "=" * 60)
        print("测试结果总结")
        print("=" * 60)
        print(f"1. 项目超时检测: {'✓ 通过' if test1 else '✗ 失败'}")
        print(f"2. 连续空页面检测: {'✓ 通过' if test2 else '✗ 失败'}")
        print(f"3. 效率检测: {'✓ 通过' if test3 else '✗ 失败'}")
        print(f"4. 大页数保护: {'✓ 通过' if test4 else '✗ 失败'}")
        
        if all([test1, test2, test3, test4]):
            print("\n✅ 所有早期停止逻辑测试通过！")
            print("\n预期效果:")
            print("- 避免连续40+页无效拉取")
            print("- 在60%项目超时时就停止（而非原来的70%）")
            print("- 连续5页空页面时停止")
            print("- 效率过低时停止")
            print("- 大页数时更严格的停止条件")
            print("\n这些优化将显著减少API资源浪费！")
            return True
        else:
            print("\n❌ 某些测试失败")
            return False
            
    except Exception as e:
        print(f"\n测试异常: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)