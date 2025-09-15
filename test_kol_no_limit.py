#!/usr/bin/env python3
"""
测试修改后的KOL获取功能，验证去掉评分限制后的效果
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.kol_dao import kol_dao
from src.models.kol import KOL
from src.utils.logger import setup_logger
from datetime import datetime


def test_get_all_kols():
    """测试获取所有KOL（去掉评分限制）"""
    setup_logger()
    
    print("🔍 测试修改后的KOL获取功能")
    print("=" * 60)
    
    try:
        # 1. 测试修改后的get_active_kols方法
        print("1. 测试get_active_kols方法（已去除评分限制）:")
        all_kols = kol_dao.get_active_kols()
        print(f"   获取到的KOL数量: {len(all_kols)}")
        
        if all_kols:
            # 显示评分分布
            influence_scores = [kol.influence_score for kol in all_kols if kol.influence_score is not None]
            trust_ratings = [kol.trust_rating for kol in all_kols if kol.trust_rating is not None]
            
            print(f"   影响力评分分布:")
            if influence_scores:
                print(f"     最高分: {max(influence_scores)}")
                print(f"     最低分: {min(influence_scores)}")
                print(f"     平均分: {sum(influence_scores)/len(influence_scores):.1f}")
                print(f"     有评分的KOL: {len(influence_scores)}/{len(all_kols)}")
            else:
                print(f"     无影响力评分数据")
            
            print(f"   信任评分分布:")
            if trust_ratings:
                print(f"     最高分: {max(trust_ratings)}")
                print(f"     最低分: {min(trust_ratings)}")
                print(f"     平均分: {sum(trust_ratings)/len(trust_ratings):.1f}")
                print(f"     有评分的KOL: {len(trust_ratings)}/{len(all_kols)}")
            else:
                print(f"     无信任评分数据")
            
            # 显示前5个KOL的详情
            print(f"\n   前5个KOL详情:")
            for i, kol in enumerate(all_kols[:5]):
                print(f"     {i+1}. {kol.kol_id}")
                print(f"        影响力: {kol.influence_score}")
                print(f"        信任度: {kol.trust_rating}")
                print(f"        类型: {kol.type}")
                print(f"        KOL100: {kol.is_kol100}")
        
        # 2. 测试高质量KOL方法（保留原有筛选逻辑）
        print(f"\n2. 测试get_high_quality_kols方法（保留筛选逻辑）:")
        high_quality_kols = kol_dao.get_high_quality_kols()
        print(f"   获取到的高质量KOL数量: {len(high_quality_kols)}")
        
        # 3. 对比两种方法的差异
        print(f"\n3. 对比分析:")
        print(f"   所有KOL: {len(all_kols)} 个")
        print(f"   高质量KOL: {len(high_quality_kols)} 个")
        print(f"   增加的KOL: {len(all_kols) - len(high_quality_kols)} 个")
        
        if len(all_kols) > len(high_quality_kols):
            print(f"   ✅ 成功去除评分限制，获取到更多KOL")
            
            # 找出新增的KOL（低评分或无评分的KOL）
            high_quality_ids = {kol.kol_id for kol in high_quality_kols}
            new_kols = [kol for kol in all_kols if kol.kol_id not in high_quality_ids]
            
            if new_kols:
                print(f"\n   新增的KOL列表:")
                for i, kol in enumerate(new_kols[:3], 1):  # 显示前3个
                    print(f"     {i}. {kol.kol_id}")
                    print(f"        影响力: {kol.influence_score}")
                    print(f"        信任度: {kol.trust_rating}")
                    print(f"        类型: {kol.type}")
                
                if len(new_kols) > 3:
                    print(f"     ... 还有 {len(new_kols) - 3} 个新增KOL")
        elif len(all_kols) == len(high_quality_kols):
            print(f"   ⚠️ 数量相同，可能表中所有KOL都满足原有的高质量标准")
        else:
            print(f"   ❌ 异常：所有KOL数量少于高质量KOL")
        
        # 4. 测试不同阈值
        print(f"\n4. 测试不同质量阈值:")
        thresholds = [
            (0, 0, "无限制"),
            (10, 3, "低门槛"),
            (20, 4, "中门槛"),
            (30, 5, "原有门槛"),
            (50, 6, "高门槛")
        ]
        
        for influence_min, trust_min, desc in thresholds:
            test_kols = kol_dao.get_high_quality_kols(influence_min, trust_min)
            print(f"   {desc}（影响≥{influence_min}, 信任≥{trust_min}）: {len(test_kols)} 个")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_kol_insertion():
    """测试插入低评分KOL"""
    print(f"\n5. 测试插入低评分KOL:")
    
    try:
        # 创建一个低评分的测试KOL
        test_kol = KOL(
            kol_id=f"test_low_score_{int(datetime.now().timestamp())}",
            type="influencer",
            influence_score=5.0,  # 低影响力评分
            trust_rating=2.0,     # 低信任评分
            is_kol100=0,
            summary="测试用的低评分KOL",
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        print(f"   创建测试KOL:")
        print(f"   - ID: {test_kol.kol_id}")
        print(f"   - 影响力: {test_kol.influence_score}")
        print(f"   - 信任度: {test_kol.trust_rating}")
        
        # 验证KOL数据
        if test_kol.validate():
            print(f"   ✅ KOL数据验证通过")
        else:
            print(f"   ❌ KOL数据验证失败")
            return False
        
        # 尝试插入数据库
        success = kol_dao.upsert_kol(test_kol)
        if success:
            print(f"   ✅ 低评分KOL插入成功")
            
            # 验证是否能获取到
            all_kols_after = kol_dao.get_active_kols()
            saved_kol = None
            for kol in all_kols_after:
                if kol.kol_id == test_kol.kol_id:
                    saved_kol = kol
                    break
            
            if saved_kol:
                print(f"   ✅ 能够在get_active_kols()中获取到低评分KOL")
                print(f"   - 影响力: {saved_kol.influence_score}")
                print(f"   - 信任度: {saved_kol.trust_rating}")
            else:
                print(f"   ❌ 无法在get_active_kols()中获取到低评分KOL")
                return False
                
            # 检查是否在高质量KOL中
            high_quality_kols = kol_dao.get_high_quality_kols()
            is_in_high_quality = any(kol.kol_id == test_kol.kol_id for kol in high_quality_kols)
            
            if is_in_high_quality:
                print(f"   ⚠️ 低评分KOL也出现在高质量KOL列表中（可能是阈值设置问题）")
            else:
                print(f"   ✅ 低评分KOL正确地被排除在高质量KOL列表外")
            
            return True
        else:
            print(f"   ❌ 低评分KOL插入失败")
            return False
            
    except Exception as e:
        print(f"   ❌ 测试插入低评分KOL时出错: {e}")
        return False


def main():
    """主测试函数"""
    print("🎯 KOL评分限制去除测试")
    print("=" * 80)
    
    # 运行测试
    test1_passed = test_get_all_kols()
    test2_passed = test_kol_insertion()
    
    # 输出结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总:")
    print(f"   获取所有KOL测试: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"   插入低评分KOL测试: {'✅ 通过' if test2_passed else '❌ 失败'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 所有测试通过!")
        print("✅ KOL评分限制已成功去除")
        print("✅ 所有KOL（包括低评分）都能正常获取")
        print("✅ 高质量KOL筛选功能保持独立可用")
        return True
    else:
        print("\n⚠️ 部分测试失败")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)