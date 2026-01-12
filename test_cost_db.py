import pymysql
import json
import os
import sys
from datetime import datetime

def load_config():
    """读取 config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def test_connection():
    config = load_config()
    cost_conf = config.get('cost_db', {})
    
    print("="*50)
    print("📡 正在测试成本数据库连接...")
    print(f"Host: {cost_conf.get('host')}")
    print(f"Port: {cost_conf.get('port')}")
    print(f"User: {cost_conf.get('username')}")
    print("="*50)
    
    try:
        conn = pymysql.connect(
            host=cost_conf.get('host'),
            port=cost_conf.get('port'),
            user=cost_conf.get('username'),
            password=cost_conf.get('password'),
            database=cost_conf.get('database')
        )
        print("✅ 连接成功！网络通畅，认证通过。")
        conn.close()
        return True, cost_conf
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False, None

def fix_missing_record(cost_conf):
    """补录刚才漏掉的数据"""
    print("\n🛠️  开始补录遗漏的成本数据...")
    
    # 刚才的数据快照
    # 2026-01-08 07:48:03
    # API请求数: 57
    # 总成本: $0.836400 USD
    # 获取推文: 5576
    
    try:
        conn = pymysql.connect(
            host=cost_conf.get('host'),
            port=cost_conf.get('port'),
            user=cost_conf.get('username'),
            password=cost_conf.get('password'),
            database=cost_conf.get('database')
        )
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO api_cost_tracking (
                timestamp, task_name, run_id, 
                total_requests, tweets_fetched, error_count,
                total_cost_usd, avg_cost_per_request, cost_per_tweet,
                server_host, success_rate, metadata
            ) VALUES (
                %s, %s, %s, 
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s
            )
        """
        
        # 构造数据
        timestamp = datetime.strptime("2026-01-08 07:48:03", "%Y-%m-%d %H:%M:%S")
        task_name = "update_metrics"
        run_id = "20260108_MANUAL_FIX"
        total_requests = 57
        tweets_fetched = 5576
        error_count = 0
        total_cost_usd = 0.8364
        avg_cost = total_cost_usd / total_requests
        cost_per_tweet = total_cost_usd / tweets_fetched
        server_host = "MANUAL_FIX_SCRIPT"
        success_rate = 100.0
        metadata = '{"reason": "manual fix for connection issue"}'
        
        cursor.execute(sql, (
            timestamp, task_name, run_id,
            total_requests, tweets_fetched, error_count,
            total_cost_usd, avg_cost, cost_per_tweet,
            server_host, success_rate, metadata
        ))
        
        conn.commit()
        conn.close()
        print(f"✅ 成功补录数据: 成本 ${total_cost_usd}")
        
    except Exception as e:
        print(f"❌ 补录失败: {e}")

if __name__ == "__main__":
    success, conf = test_connection()
    
    if success and len(sys.argv) > 1 and sys.argv[1] == "--fix":
        fix_missing_record(conf)
    elif success:
        print("\n提示: 运行 python test_cost_db.py --fix 可补录刚才遗漏的 $0.8364 数据")
