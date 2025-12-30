# Marco数据计算 - 简化启动指南

## 🚀 快速开始

使用新的简化启动脚本 `run_marco.py`，无需复杂的命令行参数！

### 最常用命令

```bash
# 生成最新数据（推荐）
python run_marco.py

# 查看统计信息
python run_marco.py stats

# 测试连接
python run_marco.py test
```

### 回填历史数据

```bash
# 回填今天的数据
python run_marco.py today

# 回填最近一周数据
python run_marco.py week

# 回填最近一个月数据  
python run_marco.py month
```

### 指定日期回填

```bash
# 回填某一天的数据
python run_marco.py 2025-01-01

# 回填日期范围的数据
python run_marco.py 2025-01-01 2025-01-07
```

## 📊 对比：简化前后

### ❌ 复杂的原始方式
```bash
# 生成最新数据
python generate_marco_data.py --mode latest

# 回填7天数据
python generate_marco_data.py --mode backfill --days 7

# 指定时间段
python generate_marco_data.py --mode period --start "2025-01-01 00:00" --end "2025-01-07 23:59"

# 查看统计
python generate_marco_data.py --mode stats
```

### ✅ 简化后的方式
```bash
# 生成最新数据
python run_marco.py

# 回填7天数据
python run_marco.py week

# 指定时间段
python run_marco.py 2025-01-01 2025-01-07

# 查看统计
python run_marco.py stats
```

## 🎯 简化优势

1. **更简洁**：无需复杂的命令行参数
2. **更直观**：命令含义一目了然
3. **更快捷**：常用操作一条命令搞定
4. **更友好**：内置帮助和错误提示
5. **向下兼容**：原始脚本依然可用

## 📋 完整命令列表

| 命令 | 功能 | 说明 |
|------|------|------|
| `python run_marco.py` | 生成最新数据 | 默认操作 |
| `python run_marco.py now` | 生成最新数据 | 同上 |
| `python run_marco.py today` | 回填今天数据 | 24小时内的数据 |
| `python run_marco.py week` | 回填一周数据 | 最近7天 |
| `python run_marco.py month` | 回填一月数据 | 最近30天 |
| `python run_marco.py stats` | 查看统计信息 | 数据总览 |
| `python run_marco.py test` | 测试连接 | 检查数据库 |
| `python run_marco.py help` | 显示帮助 | 查看用法 |
| `python run_marco.py 2025-01-01` | 回填指定日期 | 单日数据 |
| `python run_marco.py 2025-01-01 2025-01-07` | 回填日期范围 | 多日数据 |

## 🔧 定时任务设置

### 每30分钟生成最新数据（推荐配置）
```bash
# 添加到 crontab - 基于最近4小时推文数据，每30分钟生成一次
*/30 * * * * cd /path/to/twitter-crawler && python run_marco.py

# 查看crontab是否设置成功
crontab -l
```

### 每天凌晨回填前一天数据（可选）
```bash
# 添加到 crontab - 防止数据遗漏
0 1 * * * cd /path/to/twitter-crawler && python run_marco.py today
```

## 📝 使用示例

### 示例1：首次使用
```bash
# 1. 测试连接
python run_marco.py test

# 2. 回填最近一周数据
python run_marco.py week

# 3. 查看结果
python run_marco.py stats
```

### 示例2：日常维护
```bash
# 生成最新数据
python run_marco.py

# 查看最新状态
python run_marco.py stats
```

### 示例3：历史数据补充
```bash
# 补充特定日期的数据
python run_marco.py 2025-01-15

# 补充一个时间段的数据
python run_marco.py 2025-01-01 2025-01-31
```

## 🚨 注意事项

1. **自动时间对齐**：所有时间自动对齐到30分钟间隔
2. **智能跳过**：已存在的数据会自动跳过，避免重复
3. **AI模型**：默认使用真实的ChatGPT API
4. **数据依赖**：需要确保推文数据和KOL数据已存在

## 🔍 故障排除

### 常见错误及解决方案

1. **数据库连接失败**
   ```bash
   python run_marco.py test  # 检查连接
   ```

2. **没有推文数据**
   - 确保已运行推文爬虫
   - 检查数据库中是否有推文数据

3. **API配额不足**
   - 检查ChatGPT API余额
   - 调整生成频率

4. **权限问题**
   - 确保数据库用户有读写权限
   - 检查文件系统权限

## 💡 最佳实践

1. **生产环境**：使用定时任务每30分钟生成一次
2. **开发测试**：先用 `test` 命令检查环境
3. **数据回填**：分批处理大量历史数据
4. **监控运行**：定期查看 `stats` 了解数据状态

---

**提示**：原始的 `generate_marco_data.py` 脚本依然可用，适合需要高级参数控制的场景。新的 `run_marco.py` 脚本专注于简化日常使用。