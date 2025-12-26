# List Members Following 获取工具使用指南

## 📁 文件说明

### 新创建的文件
1. **check_progress.py** - 查看处理进度的工具
2. **fetch_list_members_followings.py** - 从`twitter_list_members_seed`表获取members的following

### 备份文件
- `backup_20251217/fetch_kol_followings.py.backup` - 原始脚本备份

---

## 🚀 快速开始

### 1. 查看当前进度

```bash
cd /Users/qmk/Documents/QC/twitter/Carlwang
python check_progress.py

# 查看指定List的进度
python check_progress.py --list-id "1996467877948600431"
```

**输出示例：**
```
==============================================
List Members Following 获取进度
List ID: 1996467877948600431
===============================================

📊 总体进度:
  总Member数:        1636
  已获取Following:    150
  剩余未处理:        1486
  完成度:            9.17%

💾 缓存进度:
  缓存记录:           150 个已完成
===============================================
```

### 2. 测试模式（推荐先运行）

```bash
# 不调用API，不入库，验证脚本逻辑
python fetch_list_members_followings.py --test
```

### 3. 小规模测试

```bash
# 测试1个member（真实调用API但不入库）
python fetch_list_members_followings.py --dry-run --limit 1

# 正式处理5个member
python fetch_list_members_followings.py --limit 5
```

### 4. 正式运行

```bash
# 处理20个members
python fetch_list_members_followings.py --limit 20

# 处理所有剩余的members（自动跳过已完成的）
python fetch_list_members_followings.py

# 指定不同的List ID
python fetch_list_members_followings.py --list-id "另一个ListID" --limit 20
```

---

## 🔄 断点续传示例

### 场景：每天处理一部分

```bash
# Day 1: 处理前20个
python fetch_list_members_followings.py --limit 20
# 完成：1-20

# Day 2: 运行同样的命令，自动从第21个开始
python fetch_list_members_followings.py --limit 20
# 完成：21-40

# Day 3: 继续
python fetch_list_members_followings.py --limit 20
# 完成：41-60
```

### 场景：中途中断后恢复

```bash
# 运行到第15个时，按了Ctrl+C
python fetch_list_members_followings.py --limit 20
^C  # 中断

# 重新运行，会从第15个继续（不是从头开始！）
python fetch_list_members_followings.py --limit 20
```

### 场景：API成功但入库失败

```bash
# 假设第10个member的API调用成功，但数据库挂了
python fetch_list_members_followings.py --limit 20
# 错误：第10个入库失败，但数据已缓存

# 修复数据库后，使用resume模式（不调用API，直接从缓存入库）
python fetch_list_members_followings.py --resume
```

---

## 📊 进度查看

### 方法1：使用check_progress.py
```bash
python check_progress.py
```

### 方法2：查看缓存文件
```bash
# 查看已完成的数量
cat .kol_cache/progress.json | grep -c "completed"

# 或直接查看内容
cat .kol_cache/progress.json
```

### 方法3：使用脚本的缓存状态命令
```bash
python fetch_list_members_followings.py --cache-status
```

---

## 🗂️ 数据流向

```
twitter_list_members_seed (1636个members)
    ↓
    ↓ (每个member调用API获取following)
    ↓
twitter_kol_all (存储所有following用户)
```

---

## ⚙️ 常用命令参考

```bash
# 查看进度
python check_progress.py

# 测试模式
python fetch_list_members_followings.py --test

# 处理指定数量
python fetch_list_members_followings.py --limit 20

# 从缓存恢复
python fetch_list_members_followings.py --resume

# 查看缓存状态
python fetch_list_members_followings.py --cache-status

# 清理所有缓存（慎用！）
python fetch_list_members_followings.py --clear-cache

# 查看帮助
python fetch_list_members_followings.py --help
```

---

## 🔍 如何知道处理到哪了？

### 快速查看
```bash
# 最简单的方式
python check_progress.py

# 输出会显示：
# - 总共多少个members
# - 已处理多少个
# - 剩余多少个
# - 完成百分比
```

### 数据库查询
```sql
-- 查看每个member的following收集情况
SELECT
    m.username,
    m.followers_count,
    COUNT(DISTINCT f.id) as following_collected
FROM public_data.twitter_list_members_seed m
LEFT JOIN public_data.twitter_kol_all f
    ON f.source_user_id = m.twitter_user_id
WHERE m.source_list_id = '1996467877948600431'
GROUP BY m.twitter_user_id, m.username, m.followers_count
ORDER BY following_collected DESC;
```

---

## ⚠️ 注意事项

1. **自动记忆进度**
   - 脚本会自动记住已完成的members
   - 重新运行会自动跳过已完成的
   - 不需要手动指定从哪里开始

2. **缓存机制**
   - API数据会立即缓存
   - 入库成功后自动删除缓存
   - 失败时保留缓存，可重试

3. **不要删除 `.kol_cache/` 目录**
   - 包含进度记录
   - 包含失败时的缓存数据
   - 删除会导致重新开始

4. **API费用**
   - 每个member调用一次API
   - 缓存机制避免重复调用
   - 建议分批处理

---

## 📝 文件位置

```
/Users/qmk/Documents/QC/twitter/Carlwang/
├── check_progress.py                    # 进度查看工具
├── fetch_list_members_followings.py     # Following获取脚本
├── fetch_kol_followings.py              # 原始脚本（保留）
├── backup_20251217/
│   └── fetch_kol_followings.py.backup   # 原始备份
└── .kol_cache/
    ├── progress.json                    # 进度记录
    └── *.json                           # API缓存文件
```

---

## 🆘 常见问题

### Q: 如何知道还剩多少没处理？
**A:** 运行 `python check_progress.py`

### Q: 脚本会重复处理已完成的吗？
**A:** 不会，脚本会自动跳过已完成的members

### Q: 中断后如何继续？
**A:** 直接运行同样的命令，会自动继续

### Q: API调用成功但入库失败怎么办？
**A:** 运行 `python fetch_list_members_followings.py --resume`

### Q: 如何清理缓存重新开始？
**A:** 运行 `python fetch_list_members_followings.py --clear-cache`（慎用！）

---

## 📞 需要帮助？

查看详细帮助：
```bash
python fetch_list_members_followings.py --help
```
