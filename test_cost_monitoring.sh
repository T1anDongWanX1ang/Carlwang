#!/bin/bash

# 成本监控系统测试脚本
# 测试三个 daily 项目的成本监控功能

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "========================================================"
echo -e "${BLUE}🧪 成本监控系统测试${NC}"
echo "========================================================"
echo ""

# 测试 1: Python 记录器基础功能
echo -e "${YELLOW}[测试 1/4]${NC} 测试 Python 数据库记录器..."
if [ -f "src/utils/cost_db_logger.py" ]; then
    venv/bin/python src/utils/cost_db_logger.py \
        --task-name "test_system" \
        --run-id "$(date +%Y%m%d_%H%M%S)_test" \
        --total-requests 10 \
        --total-cost 0.01 \
        --tweets-fetched 200 \
        --error-count 0 \
        --success-kols 5 \
        --total-kols 5 \
        --cache-hits 3 2>&1

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Python 记录器测试成功${NC}"
    else
        echo -e "${RED}✗ Python 记录器测试失败${NC}"
    fi
else
    echo -e "${RED}✗ 未找到 Python 记录器${NC}"
fi

echo ""

# 测试 2: KOL Following 监控脚本
echo -e "${YELLOW}[测试 2/4]${NC} 测试 KOL Following 监控脚本..."
if [ -f "daily_kol_following_crawler/monitor_daily_cost.sh" ]; then
    echo -e "${BLUE}运行 daily_kol_following_crawler/monitor_daily_cost.sh:${NC}"
    echo "----------------------------------------"
    bash daily_kol_following_crawler/monitor_daily_cost.sh 2>&1 | head -30
    echo "----------------------------------------"
    echo -e "${GREEN}✓ KOL Following 监控脚本执行完成${NC}"
else
    echo -e "${RED}✗ 未找到 KOL Following 监控脚本${NC}"
fi

echo ""

# 测试 3: KOL Tweet 监控脚本
echo -e "${YELLOW}[测试 3/4]${NC} 测试 KOL Tweet 监控脚本..."
if [ -f "daily_kol_tweet_crawler/monitor_daily_cost.sh" ]; then
    echo -e "${BLUE}运行 daily_kol_tweet_crawler/monitor_daily_cost.sh:${NC}"
    echo "----------------------------------------"
    bash daily_kol_tweet_crawler/monitor_daily_cost.sh 2>&1 | head -30
    echo "----------------------------------------"
    echo -e "${GREEN}✓ KOL Tweet 监控脚本执行完成${NC}"
else
    echo -e "${RED}✗ 未找到 KOL Tweet 监控脚本${NC}"
fi

echo ""

# 测试 4: Project Tweet 监控脚本
echo -e "${YELLOW}[测试 4/4]${NC} 测试 Project Tweet 监控脚本..."
if [ -f "daily_tweet_crawler/monitor_daily_cost.sh" ]; then
    echo -e "${BLUE}运行 daily_tweet_crawler/monitor_daily_cost.sh:${NC}"
    echo "----------------------------------------"
    bash daily_tweet_crawler/monitor_daily_cost.sh 2>&1 | head -30
    echo "----------------------------------------"
    echo -e "${GREEN}✓ Project Tweet 监控脚本执行完成${NC}"
else
    echo -e "${RED}✗ 未找到 Project Tweet 监控脚本${NC}"
fi

echo ""

# 测试 5: 验证数据库记录
echo -e "${YELLOW}[验证]${NC} 检查数据库中的测试记录..."
venv/bin/python << 'EOF'
import pymysql
try:
    conn = pymysql.connect(
        host='35.215.99.34',
        port=13215,
        user='alarm_user',
        password='fdf3rw3983nnfl1f4',
        database='tp_alarm'
    )
    cursor = conn.cursor()

    # 查询最近的记录
    cursor.execute("""
        SELECT task_name, COUNT(*) as count, MAX(timestamp) as latest
        FROM api_cost_tracking
        WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
        GROUP BY task_name
        ORDER BY latest DESC
    """)

    rows = cursor.fetchall()
    if rows:
        print("\n最近1小时内的记录:")
        print(f"{'任务名称':<20} {'记录数':<10} {'最新时间'}")
        print('-' * 60)
        for row in rows:
            print(f"{row[0]:<20} {row[1]:<10} {row[2]}")

        # 清理测试数据
        cursor.execute("DELETE FROM api_cost_tracking WHERE task_name = 'test_system'")
        conn.commit()
        print("\n✓ 测试数据已清理")
    else:
        print("\n⚠ 最近1小时内没有新记录")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"\n✗ 数据库查询失败: {e}")
EOF

echo ""
echo "========================================================"
echo -e "${GREEN}✅ 测试完成${NC}"
echo "========================================================"
echo ""
echo "详细文档: COST_MONITORING_GUIDE.md"
echo ""
