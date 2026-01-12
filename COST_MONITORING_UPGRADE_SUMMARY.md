# 成本监控系统升级总结

## 📋 已完成的工作

### 1. 创建数据库记录器 ✅
**文件**: `src/utils/cost_db_logger.py`
- 通用的 Python 模块，用于记录成本数据到数据库
- 支持命令行调用和 Python 导入使用
- 自动计算衍生指标（平均成本、成功率等）
- 支持元数据扩展（JSON 格式）

### 2. 升级/创建成本监控脚本 ✅

#### KOL Following 监控脚本
**文件**: `daily_kol_following_crawler/monitor_daily_cost.sh`
- ✅ **已升级**：添加数据库记录功能
- 统计：API 调用、缓存命中、KOL 处理、Following 数据
- 记录字段：task_name="kol_following"

#### KOL Tweet 监控脚本
**文件**: `daily_kol_tweet_crawler/monitor_daily_cost.sh`
- ✅ **新创建**：完整的成本监控和数据库记录
- 统计：API 调用、推文获取、智能早停触发
- 记录字段：task_name="kol_tweet"

#### Project Tweet 监控脚本
**文件**: `daily_tweet_crawler/monitor_daily_cost.sh`
- ✅ **已升级**：添加数据库记录功能
- 统计：运行次数、推文获取、成本预估
- 记录字段：task_name="project_tweet"

### 3. 创建文档和测试工具 ✅
- `COST_MONITORING_GUIDE.md` - 完整的使用指南
- `test_cost_monitoring.sh` - 自动化测试脚本

---

## 🎯 功能特性

### 自动化记录
- 每次运行监控脚本时自动记录到数据库
- 失败不影响统计显示（容错设计）
- 记录运行时间、服务器主机名等

### 智能计算
- 平均每次请求成本
- 平均每条推文成本
- 成功率百分比
- 月成本预估

### 灵活扩展
- 支持自定义元数据（JSON 格式）
- 可记录额外的业务指标
- 支持多服务器部署追踪

---

## 📊 数据库信息

**数据库**: `tp_alarm`
**表名**: `api_cost_tracking`
**连接信息**:
- Host: 35.215.99.34
- Port: 13215
- User: alarm_user
- Password: fdf3rw3983nnfl1f4

**记录的数据**:
| 任务名称 | 说明 |
|---------|------|
| kol_following | KOL Following 爬取服务 |
| kol_tweet | KOL 推文爬取服务 |
| project_tweet | 项目推文爬取服务 |

---

## 🚀 使用方法

### 查看成本统计
```bash
# KOL Following 服务
cd daily_kol_following_crawler
./monitor_daily_cost.sh

# KOL Tweet 服务
cd daily_kol_tweet_crawler
./monitor_daily_cost.sh

# Project Tweet 服务
cd daily_tweet_crawler
./monitor_daily_cost.sh
```

### 运行测试
```bash
# 测试所有监控脚本
./test_cost_monitoring.sh
```

### 查询数据库
```sql
-- 查看最近记录
SELECT * FROM api_cost_tracking
ORDER BY timestamp DESC LIMIT 10;

-- 按任务统计
SELECT
    task_name,
    COUNT(*) as runs,
    SUM(total_cost_usd) as total_cost,
    AVG(cost_per_tweet) as avg_tweet_cost
FROM api_cost_tracking
GROUP BY task_name;

-- 每日成本趋势
SELECT
    DATE(timestamp) as date,
    task_name,
    SUM(total_cost_usd) as daily_cost
FROM api_cost_tracking
WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY DATE(timestamp), task_name
ORDER BY date DESC;
```

---

## 📝 修改的文件清单

### 新建文件
1. `src/utils/cost_db_logger.py` - 数据库记录器
2. `daily_kol_tweet_crawler/monitor_daily_cost.sh` - KOL Tweet 监控脚本
3. `COST_MONITORING_GUIDE.md` - 使用指南
4. `test_cost_monitoring.sh` - 测试脚本
5. `COST_MONITORING_UPGRADE_SUMMARY.md` - 本文件

### 修改文件
1. `daily_kol_following_crawler/monitor_daily_cost.sh` - 添加数据库记录
2. `daily_tweet_crawler/monitor_daily_cost.sh` - 添加数据库记录

---

## ✅ 测试验证

已验证功能：
- ✅ Python 记录器可以成功写入数据库
- ✅ 自动计算的字段（avg_cost_per_request, cost_per_tweet, success_rate）正确
- ✅ 元数据（metadata）JSON 格式正确存储
- ✅ 监控脚本能正确解析日志并提取统计数据
- ✅ 数据库连接和错误处理正常

---

## 🔧 故障排查

### 如果数据库写入失败
1. 检查网络连接到 35.215.99.34:13215
2. 验证数据库凭证是否正确
3. 确认 tp_alarm 数据库存在且有写入权限

### 如果监控脚本报错
1. 确保虚拟环境 `venv` 存在
2. 检查 Python 路径是否正确
3. 验证日志文件是否存在且可读

### 如果统计数据不准确
1. 检查日志格式是否发生变化
2. 调整脚本中的正则表达式匹配规则
3. 查看日志文件中的实际内容格式

---

## 📌 注意事项

1. **不影响现有功能**：即使数据库写入失败，统计显示仍然正常
2. **向后兼容**：保留了原有的所有统计功能
3. **性能影响**：数据库写入时间约 0.1-0.5 秒，可忽略不计
4. **数据清理**：建议定期清理 90 天以上的旧数据

---

## 🎉 升级优势

### 之前：只能查看日志
- ✗ 成本数据分散在日志中
- ✗ 难以进行长期趋势分析
- ✗ 无法跨服务对比
- ✗ 查询历史数据困难

### 现在：数据库 + 日志双保险
- ✅ 成本数据结构化存储
- ✅ 支持 SQL 查询和分析
- ✅ 可视化成本趋势
- ✅ 跨任务对比分析
- ✅ 快速定位成本异常
- ✅ 支持告警和监控集成

---

## 📈 下一步建议

### 可选增强功能
1. **成本告警**：当日成本超过阈值时发送通知
2. **可视化仪表板**：使用 Grafana 展示成本趋势
3. **自动优化建议**：基于历史数据提供成本优化建议
4. **预算管理**：设置月度预算并跟踪使用情况
5. **成本归因分析**：细化到每个 list_id 的成本

---

## 📞 技术支持

如有问题，请查看：
1. `COST_MONITORING_GUIDE.md` - 详细使用文档
2. `src/utils/cost_db_logger.py` - 代码实现
3. 运行 `./test_cost_monitoring.sh` 进行诊断

---

**升级完成日期**: 2025-12-31
**升级版本**: v1.0
**状态**: ✅ 已测试通过，可以投入使用
