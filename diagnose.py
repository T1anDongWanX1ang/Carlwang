#!/usr/bin/env python3
"""
问题诊断脚本
帮助排查和解决常见的运行问题
"""
import sys
import os
import subprocess
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    print("🐍 检查Python版本...")
    version = sys.version_info
    print(f"   Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("   ❌ Python版本过低，需要3.7+")
        return False
    else:
        print("   ✅ Python版本符合要求")
        return True

def check_virtual_environment():
    """检查虚拟环境"""
    print("\n📦 检查虚拟环境...")
    
    # 检查是否在虚拟环境中
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if in_venv:
        print("   ✅ 当前在虚拟环境中")
        return True
    else:
        print("   ❌ 当前不在虚拟环境中")
        
        # 检查venv目录是否存在
        venv_path = Path("venv")
        if venv_path.exists():
            print("   💡 虚拟环境存在，请运行: source venv/bin/activate")
        else:
            print("   💡 虚拟环境不存在，请运行: python3 -m venv venv")
        
        return False

def check_dependencies():
    """检查依赖包"""
    print("\n📚 检查依赖包...")
    
    required_packages = [
        'requests',
        'pymysql', 
        'python-dateutil',
        'openai'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'python-dateutil':
                __import__('dateutil')
            else:
                __import__(package.replace('-', '_'))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n   💡 缺少依赖包: {', '.join(missing_packages)}")
        print("   请运行: pip install -r requirements.txt")
        return False
    else:
        print("   ✅ 所有依赖包已安装")
        return True

def check_configuration():
    """检查配置文件"""
    print("\n⚙️ 检查配置文件...")
    
    config_path = Path("config/config.json")
    
    if not config_path.exists():
        print("   ❌ 配置文件不存在: config/config.json")
        return False
    
    try:
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查关键配置
        required_keys = ['api', 'database', 'chatgpt']
        missing_keys = []
        
        for key in required_keys:
            if key not in config:
                missing_keys.append(key)
            else:
                print(f"   ✅ {key} 配置存在")
        
        if missing_keys:
            print(f"   ❌ 缺少配置: {', '.join(missing_keys)}")
            return False
        
        # 检查API密钥
        api_key = config.get('api', {}).get('headers', {}).get('ApiKey', '')
        chatgpt_key = config.get('chatgpt', {}).get('api_key', '')
        
        if not api_key:
            print("   ❌ TweetScout API密钥未配置")
        else:
            print("   ✅ TweetScout API密钥已配置")
        
        if not chatgpt_key:
            print("   ❌ ChatGPT API密钥未配置")
        else:
            print("   ✅ ChatGPT API密钥已配置")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 配置文件格式错误: {e}")
        return False

def check_database_connection():
    """检查数据库连接"""
    print("\n🗄️ 检查数据库连接...")
    
    try:
        # 添加项目根目录到Python路径
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        
        from src.database.connection import db_manager
        
        success = db_manager.test_connection()
        
        if success:
            print("   ✅ 数据库连接成功")
            
            # 检查表是否存在
            try:
                tweet_count = db_manager.execute_query("SELECT COUNT(*) as count FROM twitter_tweet")[0]['count']
                user_count = db_manager.execute_query("SELECT COUNT(*) as count FROM twitter_user")[0]['count']
                topic_count = db_manager.execute_query("SELECT COUNT(*) as count FROM topics")[0]['count']
                
                print(f"   ✅ 推文表: {tweet_count} 条记录")
                print(f"   ✅ 用户表: {user_count} 条记录")
                print(f"   ✅ 话题表: {topic_count} 条记录")
                
            except Exception as e:
                print(f"   ⚠️ 表查询异常: {e}")
                print("   💡 可能需要创建数据库表")
            
            return True
        else:
            print("   ❌ 数据库连接失败")
            print("   💡 请检查数据库配置和网络连接")
            return False
            
    except Exception as e:
        print(f"   ❌ 数据库连接测试异常: {e}")
        return False

def check_api_connection():
    """检查API连接"""
    print("\n🌐 检查API连接...")
    
    try:
        from src.api.twitter_api import twitter_api
        
        # 简单的API测试
        test_data = twitter_api.fetch_tweets(count=1)
        
        if test_data is not None:
            print("   ✅ TweetScout API连接成功")
            return True
        else:
            print("   ❌ TweetScout API连接失败")
            print("   💡 请检查API密钥和网络连接")
            return False
            
    except Exception as e:
        print(f"   ❌ API连接测试异常: {e}")
        return False

def provide_solutions():
    """提供解决方案"""
    print("\n🔧 常见问题解决方案:")
    print()
    print("1. 模块找不到错误 (ModuleNotFoundError):")
    print("   - 确保激活虚拟环境: source venv/bin/activate")
    print("   - 重新安装依赖: pip install -r requirements.txt")
    print()
    print("2. 数据库连接失败:")
    print("   - 检查网络连接")
    print("   - 验证数据库配置信息")
    print("   - 确保数据库服务正常运行")
    print()
    print("3. API连接失败:")
    print("   - 验证API密钥是否正确")
    print("   - 检查API配额是否用完")
    print("   - 确认网络可以访问API服务")
    print()
    print("4. ChatGPT API问题:")
    print("   - 验证OpenAI API密钥")
    print("   - 检查API配额和计费")
    print("   - 确认模型可用性")
    print()
    print("5. 推荐的运行命令:")
    print("   - 测试连接: ./run.sh test")
    print("   - 单次执行: ./run.sh once")
    print("   - 话题分析: ./run.sh topic")
    print("   - 定时调度: ./run.sh schedule")

def main():
    """主函数"""
    print("🔍 Twitter爬虫问题诊断工具")
    print("=" * 50)
    
    # 运行所有检查
    checks = [
        check_python_version(),
        check_virtual_environment(),
        check_dependencies(),
        check_configuration(),
        check_database_connection(),
        check_api_connection()
    ]
    
    passed_checks = sum(checks)
    total_checks = len(checks)
    
    print(f"\n📊 诊断结果: {passed_checks}/{total_checks} 项检查通过")
    
    if passed_checks == total_checks:
        print("🎉 所有检查都通过，系统运行正常！")
        print("\n可以开始使用:")
        print("  ./run.sh once    # 单次爬取")
        print("  ./run.sh topic   # 话题分析") 
        print("  ./run.sh schedule # 定时调度")
    else:
        print("⚠️ 发现问题，请查看上述检查结果")
        provide_solutions()

if __name__ == '__main__':
    main() 