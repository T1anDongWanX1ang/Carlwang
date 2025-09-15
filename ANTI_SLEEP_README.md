# 防待机服务配置说明

## 问题描述
Twitter爬虫定时任务在电脑待机时会停止运行，这是由于以下原因：

1. **macOS系统的App Nap功能**：系统会自动暂停非活跃的进程
2. **进程优先级问题**：使用nohup启动的进程在系统资源紧张时容易被暂停  
3. **缺少keepalive机制**：没有监控和自动重启机制

## 解决方案

### 1. 防休眠启动
- **macOS**: 使用 `caffeinate -i` 命令防止系统休眠影响进程
- **Linux**: 使用 `nice -n -5` 设置高优先级

### 2. 自动监控机制
- 每5分钟自动检查服务状态
- 检测进程是否存在
- 检测日志文件是否在更新（30分钟内）
- 服务异常时自动重启

### 3. 使用方法

#### 启动服务（推荐）
```bash
./start_service.sh start
```

这将：
- 使用防休眠方式启动服务
- 自动设置监控定时任务
- 每5分钟检查服务状态

#### 查看监控状态
```bash
./start_service.sh monitor
```

#### 查看服务状态  
```bash
./start_service.sh status
```

#### 停止服务
```bash
./start_service.sh stop
```
这将同时移除监控定时任务。

### 4. 监控机制详细说明

#### 检查项目
1. **进程存在性**：检查PID文件和进程是否存在
2. **进程正确性**：验证进程是否为预期的Python服务
3. **活跃性检测**：检查日志文件是否在30分钟内更新过

#### 自动恢复
- 检测到服务异常时，自动停止旧进程
- 清理PID文件和相关资源
- 重新启动服务
- 记录恢复操作到监控日志

#### 日志文件
- 服务日志：`service.log`
- 监控日志：`monitor.log`

### 5. 手动设置cron任务（可选）

如果自动设置失败，可以手动添加：

```bash
# 编辑crontab
crontab -e

# 添加以下行（请替换为实际路径）
*/5 * * * * /path/to/twitter-crawler/service_monitor.sh >/dev/null 2>&1
```

### 6. 故障排除

#### 检查监控是否正常工作
```bash
# 查看cron任务
crontab -l | grep service_monitor

# 查看监控日志
tail -f monitor.log
```

#### 手动测试监控脚本
```bash
./service_monitor.sh
```

#### 检查服务状态
```bash
./start_service.sh status
./start_service.sh monitor
```

### 7. 系统兼容性

#### macOS
- ✅ 支持 `caffeinate` 防休眠
- ✅ 支持 cron 定时任务
- ✅ 自动检测系统类型

#### Linux
- ✅ 支持 `nice` 优先级设置
- ✅ 支持 cron 定时任务
- ✅ 兼容大部分Linux发行版

### 8. 注意事项

1. **权限问题**：确保脚本有执行权限
   ```bash
   chmod +x start_service.sh
   chmod +x service_monitor.sh
   ```

2. **cron权限**：确保当前用户有crontab权限

3. **路径问题**：使用绝对路径避免cron执行时的路径问题

4. **日志轮转**：监控日志会自动保留最近1000行，防止过大

5. **资源占用**：监控脚本每5分钟运行一次，资源占用很少

### 9. 测试建议

启动服务后，可以进行以下测试：

1. **正常情况测试**：
   ```bash
   ./start_service.sh start
   sleep 10
   ./start_service.sh status
   ```

2. **异常恢复测试**：
   ```bash
   # 手动杀死进程，观察是否自动恢复
   kill $(cat twitter-crawler.pid)
   # 等待5分钟后检查
   ./start_service.sh status
   ```

3. **待机测试**：
   - 启动服务
   - 让电脑进入待机/休眠
   - 唤醒后检查服务是否仍在运行

## 总结

通过以上改进，Twitter爬虫服务现在具备了：
- ✅ 防待机能力
- ✅ 自动监控
- ✅ 异常恢复  
- ✅ 详细日志
- ✅ 跨平台兼容

这确保了服务能够7x24小时稳定运行，即使在电脑待机的情况下也能持续工作。