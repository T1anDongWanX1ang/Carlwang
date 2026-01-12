# -*- coding: utf-8 -*-
import pymysql
import json
import os
import sys
from datetime import datetime

def load_config():
    """读取 config.json"""
    # 获取脚本所在的绝对路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 定义可能的路径列表
    possible_paths = [
        # 1. 尝试标准路径: ../config/config.json
        os.path.abspath(os.path.join(script_dir, '..', 'config', 'config.json')),
        # 2. 尝试当前目录: ./config/config.json
        os.path.join(script_dir, 'config', 'config.json'),
        # 3. 尝试绝对路径 (基于报错信息推测)
        '/home/centos/Project/Carlwang/config/config.json'
    ]

    print("🔍 正在寻找配置文件...")
    for path in possible_paths:
        if os.path.exists(path):
            print("✅ 找到配置文件: {}".format(path))
            with open(path, 'r') as f:
                return json.load(f)
        else:
            print("   尝试路径不存在: {}".format(path))

    # 如果都找不到，抛出明确错误
    print("\n❌ 错误: 找不到 config.json 文件！")
    print("请确认文件是否在以下位置之一: /home/centos/Project/Carlwang/config/config.json")
    sys.exit(1)

def test_connection():
    try:
        config = load_config()
    except Exception as e:
        print("❌ 读取配置文件失败: {}".format(e))
        return False, None

    cost_conf = config.get('cost_db', {})
    
    print("="*50)
    print("📡 正在测试成本数据库连接...")
    print("Host: {}".format(cost_conf.get('host')))
    print("Port: {}".format(cost_conf.get('port')))
    print("User: {}".format(cost_conf.get('username')))
    print("="*50)
    
    try:
        conn = pymysql.connect(
            host=cost_conf.get('host'),
            port=int(cost_conf.get('port')),
            user=cost_conf.get('username'),
            password=cost_conf.get('password'),
            database=cost_conf.get('database'),
            connect_timeout=10
        )
        print("✅ 连接成功！网络通畅，认证通过。")
        conn.close()
        return True, cost_conf
    except Exception as e:
        print("❌ 连接失败: {}".format(e))
        return False, None

def fix_missing_record(cost_conf):
    """补录刚才漏掉的数据"""
    print("\n🛠️  开始补录遗漏的成本数据...")
    
    try:
        conn = pymysql.connect(
            host=cost_conf.get('host'),
            port=int(cost_conf.get('port')),
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
        
        # 刚才的数据快照
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
        print("✅ 成功补录数据: 成本 $0.8364")
        
    except Exception as e:
        print("❌ 补录失败: {}".format(e))

if __name__ == "__main__":
    success, conf = test_connection()
    
    if success and len(sys.argv) > 1 and sys.argv[1] == "--fix":
        fix_missing_record(conf)
    elif success:
        print("\n提示: 运行 ../venv/bin/python test_cost_db.py --fix 可补录遗漏数据")
