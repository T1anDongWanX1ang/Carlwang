#!/usr/bin/env python3
"""
Twitter数据爬取服务管理器
提供服务的启动、停止、监控等功能
"""
import sys
import os
import time
import signal
import psutil
import argparse
from pathlib import Path
from datetime import datetime
import json

class TwitterCrawlerService:
    """Twitter爬虫服务管理器"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.pid_file = self.script_dir / "twitter-crawler.pid"
        self.log_file = self.script_dir / "service.log"
        self.config_file = self.script_dir / "service_config.json"
        
        # 默认配置
        self.default_config = {
            "interval": 5,
            "max_pages": 3,
            "page_size": 100,
            "auto_restart": True,
            "max_memory_mb": 500,
            "max_cpu_percent": 80
        }
        
    def load_config(self):
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                return {**self.default_config, **config}
            except Exception as e:
                print(f"❌ 加载配置失败: {e}")
        return self.default_config
    
    def save_config(self, config):
        """保存配置"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"✅ 配置已保存到: {self.config_file}")
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
    
    def get_pid(self):
        """获取服务PID"""
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    return int(f.read().strip())
            except:
                return None
        return None
    
    def is_running(self):
        """检查服务是否运行"""
        pid = self.get_pid()
        if pid:
            try:
                process = psutil.Process(pid)
                if 'python' in process.name().lower() and 'main.py' in ' '.join(process.cmdline()):
                    return True, process
            except psutil.NoSuchProcess:
                pass
        return False, None
    
    def stop_service(self):
        """停止服务"""
        print("🛑 正在停止Twitter数据爬取服务...")
        
        running, process = self.is_running()
        if running:
            try:
                # 优雅停止
                process.terminate()
                process.wait(timeout=10)
                print("✅ 服务已停止")
            except psutil.TimeoutExpired:
                print("⚠️  进程未响应，强制终止")
                process.kill()
            except Exception as e:
                print(f"❌ 停止服务时出错: {e}")
        else:
            print("ℹ️  服务未运行")
        
        # 清理PID文件
        if self.pid_file.exists():
            self.pid_file.unlink()
        
        # 停止所有相关进程
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if (proc.info['name'] and 'python' in proc.info['name'].lower() and 
                    proc.info['cmdline'] and any('main.py' in arg for arg in proc.info['cmdline']) and
                    any('schedule' in arg for arg in proc.info['cmdline'])):
                    proc.terminate()
                    print(f"🔄 终止进程 PID: {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    def start_service(self, interval=None, max_pages=None, page_size=None):
        """启动服务"""
        config = self.load_config()
        
        # 使用传入的参数或配置中的默认值
        interval = interval or config['interval']
        max_pages = max_pages or config['max_pages']
        page_size = page_size or config['page_size']
        
        # 检查服务是否已运行
        running, _ = self.is_running()
        if running:
            print("❌ 服务已在运行，请先停止服务")
            return False
        
        print("🚀 启动Twitter数据爬取服务...")
        print(f"📋 配置: 间隔={interval}分钟, 页数={max_pages}, 每页={page_size}条")
        
        try:
            # 构建启动命令
            cmd = [
                sys.executable, "main.py",
                "--mode", "schedule",
                "--interval", str(interval),
                "--max-pages", str(max_pages),
                "--page-size", str(page_size)
            ]
            
            # 启动进程
            import subprocess
            with open(self.log_file, 'a') as log_f:
                log_f.write(f"\n=== 服务启动 {datetime.now()} ===\n")
                process = subprocess.Popen(
                    cmd,
                    cwd=self.script_dir,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )
            
            # 保存PID
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # 等待验证启动
            time.sleep(3)
            running, proc = self.is_running()
            
            if running:
                print(f"✅ 服务启动成功 (PID: {process.pid})")
                print(f"📝 日志文件: {self.log_file}")
                return True
            else:
                print("❌ 服务启动失败")
                self.pid_file.unlink()
                return False
                
        except Exception as e:
            print(f"❌ 启动服务时出错: {e}")
            return False
    
    def get_status(self):
        """获取服务状态"""
        running, process = self.is_running()
        
        status = {
            "running": running,
            "pid": None,
            "memory_mb": 0,
            "cpu_percent": 0,
            "start_time": None,
            "uptime": None
        }
        
        if running:
            try:
                status["pid"] = process.pid
                status["memory_mb"] = round(process.memory_info().rss / 1024 / 1024, 2)
                status["cpu_percent"] = round(process.cpu_percent(interval=1), 2)
                start_time = datetime.fromtimestamp(process.create_time())
                status["start_time"] = start_time.strftime("%Y-%m-%d %H:%M:%S")
                uptime = datetime.now() - start_time
                status["uptime"] = str(uptime).split('.')[0]
            except Exception as e:
                print(f"⚠️  获取进程信息时出错: {e}")
        
        return status
    
    def monitor_service(self):
        """监控服务状态"""
        config = self.load_config()
        
        print("📊 开始监控Twitter数据爬取服务...")
        print("按 Ctrl+C 停止监控\n")
        
        try:
            while True:
                status = self.get_status()
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                if status["running"]:
                    print(f"[{timestamp}] 🟢 运行中 | PID: {status['pid']} | "
                          f"内存: {status['memory_mb']}MB | CPU: {status['cpu_percent']}% | "
                          f"运行时长: {status['uptime']}")
                    
                    # 检查资源使用情况
                    if status['memory_mb'] > config.get('max_memory_mb', 500):
                        print(f"⚠️  内存使用过高: {status['memory_mb']}MB")
                    
                    if status['cpu_percent'] > config.get('max_cpu_percent', 80):
                        print(f"⚠️  CPU使用率过高: {status['cpu_percent']}%")
                        
                else:
                    print(f"[{timestamp}] 🔴 服务未运行")
                    if config.get('auto_restart', True):
                        print("🔄 自动重启服务...")
                        self.start_service()
                
                time.sleep(10)
                
        except KeyboardInterrupt:
            print("\n📊 监控已停止")
    
    def show_logs(self, lines=50):
        """显示日志"""
        if self.log_file.exists():
            print(f"📝 显示最新 {lines} 行日志:")
            print("=" * 80)
            
            with open(self.log_file, 'r') as f:
                all_lines = f.readlines()
                for line in all_lines[-lines:]:
                    print(line.rstrip())
        else:
            print("⚠️  日志文件不存在")
    
    def run_once(self, max_pages=None, page_size=None):
        """执行单次爬取"""
        config = self.load_config()
        
        # 使用传入的参数或配置中的默认值
        max_pages = max_pages or config['max_pages']
        page_size = page_size or config['page_size']
        
        print("🚀 开始执行单次推文数据爬取...")
        print(f"📋 配置: 页数={max_pages}, 每页={page_size}条")
        
        try:
            # 构建启动命令
            cmd = [
                sys.executable, "main.py",
                "--mode", "once",
                "--max-pages", str(max_pages),
                "--page-size", str(page_size)
            ]
            
            # 执行命令并实时显示输出
            import subprocess
            print("⏳ 正在爬取数据，请稍候...")
            
            start_time = time.time()
            process = subprocess.Popen(
                cmd,
                cwd=self.script_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 实时显示输出
            output_lines = []
            while True:
                line = process.stdout.readline()
                if line:
                    line = line.rstrip()
                    print(f"📝 {line}")
                    output_lines.append(line)
                    
                    # 同时写入日志文件
                    with open(self.log_file, 'a') as log_f:
                        log_f.write(f"{datetime.now()} - ONCE - {line}\n")
                        
                if process.poll() is not None:
                    break
            
            # 获取剩余输出
            remaining_output = process.stdout.read()
            if remaining_output:
                for line in remaining_output.strip().split('\n'):
                    if line:
                        print(f"📝 {line}")
                        output_lines.append(line)
            
            end_time = time.time()
            duration = round(end_time - start_time, 2)
            
            if process.returncode == 0:
                print(f"✅ 单次爬取完成 (耗时: {duration}秒)")
                
                # 简单统计
                success_lines = [line for line in output_lines if '成功' in line or 'SUCCESS' in line]
                error_lines = [line for line in output_lines if '失败' in line or 'ERROR' in line or 'Exception' in line]
                
                if success_lines:
                    print(f"📊 成功操作: {len(success_lines)}项")
                if error_lines:
                    print(f"⚠️  发现错误: {len(error_lines)}项")
                    
                return True
            else:
                print(f"❌ 单次爬取失败 (退出码: {process.returncode}, 耗时: {duration}秒)")
                return False
                
        except Exception as e:
            print(f"❌ 执行单次爬取时出错: {e}")
            return False
    
    def show_status(self):
        """显示详细状态"""
        config = self.load_config()
        status = self.get_status()
        
        print("📊 Twitter数据爬取服务状态")
        print("=" * 50)
        
        if status["running"]:
            print(f"🟢 状态: 运行中")
            print(f"📋 PID: {status['pid']}")
            print(f"💾 内存使用: {status['memory_mb']} MB")
            print(f"⚡ CPU使用: {status['cpu_percent']}%")
            print(f"🕒 启动时间: {status['start_time']}")
            print(f"⏱️  运行时长: {status['uptime']}")
        else:
            print(f"🔴 状态: 未运行")
        
        print(f"\n⚙️  当前配置:")
        print(f"   间隔: {config['interval']} 分钟")
        print(f"   页数: {config['max_pages']}")
        print(f"   每页: {config['page_size']} 条")
        print(f"   自动重启: {config['auto_restart']}")
        
        print(f"\n📁 文件位置:")
        print(f"   PID文件: {self.pid_file}")
        print(f"   日志文件: {self.log_file}")
        print(f"   配置文件: {self.config_file}")

def main():
    parser = argparse.ArgumentParser(description="Twitter数据爬取服务管理器")
    parser.add_argument("command", choices=["start", "stop", "restart", "status", "monitor", "logs", "config", "once"], 
                       help="要执行的命令")
    parser.add_argument("--interval", type=int, help="爬取间隔(分钟)")
    parser.add_argument("--max-pages", type=int, help="最大页数")
    parser.add_argument("--page-size", type=int, help="每页条数")
    parser.add_argument("--lines", type=int, default=50, help="显示日志行数")
    
    args = parser.parse_args()
    service = TwitterCrawlerService()
    
    if args.command == "start":
        service.start_service(args.interval, args.max_pages, args.page_size)
    elif args.command == "stop":
        service.stop_service()
    elif args.command == "restart":
        service.stop_service()
        time.sleep(2)
        service.start_service(args.interval, args.max_pages, args.page_size)
    elif args.command == "status":
        service.show_status()
    elif args.command == "monitor":
        service.monitor_service()
    elif args.command == "logs":
        service.show_logs(args.lines)
    elif args.command == "once":
        service.run_once(args.max_pages, args.page_size)
    elif args.command == "config":
        config = service.load_config()
        print("📋 当前配置:")
        print(json.dumps(config, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()