# 🚀 快速开始 - 5分钟上手

## 第一步：创建数据库表 (1分钟)

```bash
cd /Users/qmk/Documents/QC/twitter/Carlwang

# 方法1: 使用MySQL命令行
mysql -h 35.215.99.34 -P 13216 -u tele -p'tele_sb268fg@cg5wH9dgW' public_data < sql/create_list_members_seed_table.sql

# 方法2: 或者复制SQL内容，在你习惯的数据库工具中执行
cat sql/create_list_members_seed_table.sql
```

## 第二步：测试脚本 (1分钟)

```bash
# 测试模式（不调用API）
python fetch_list_members.py --test

# 应该看到：
# ✓ 数据库连接成功
# 【测试模式 - 不调用API，不入库】
# 处理完成！
```

## 第三步：处理第一个List (3分钟)

```bash
# 模拟运行（查看会获取多少数据）
python fetch_list_members.py \
    --list-id "1996467877948600431" \
    --list-name "KOL_CMC_top100" \
    --dry-run

# 如果看起来正常，执行正式入库
python fetch_list_members.py \
    --list-id "1996467877948600431" \
    --list-name "KOL_CMC_top100"
```

## 第四步：查看结果

```bash
# 查看统计
python fetch_list_members.py --stats

# 或者直接查询数据库
mysql -h 35.215.99.34 -P 13216 -u tele -p'tele_sb268fg@cg5wH9dgW' public_data -e "
SELECT COUNT(*) as total,
       AVG(followers_count) as avg_followers
FROM twitter_list_members_seed;
"
```

## 完成！🎉

你现在已经完成了**KOL扩充阶段1**！

### 下一步：

1. **处理其他9个List**:
   ```bash
   python fetch_list_members.py --list-id "1996305216485150751" --list-name "List_02"
   python fetch_list_members.py --list-id "1996038927162245632" --list-name "List_03"
   # ... 以此类推
   ```

2. **或者批量处理所有List**:
   ```bash
   python fetch_list_members.py --batch
   ```

3. **进入阶段2 - 获取Followings**:
   参考 `README_KOL_FOLLOWINGS.md`，使用 `fetch_kol_followings.py`

---

## 🆘 遇到问题？

### API返回错误
```bash
# 检查API Key是否正确
grep "X-API-Key" fetch_list_members.py
```

### 数据库连接失败
```bash
# 测试数据库连接
mysql -h 35.215.99.34 -P 13216 -u tele -p'tele_sb268fg@cg5wH9dgW' -e "SELECT 1;"
```

### 查看详细日志
```bash
tail -f logs/twitter_crawler.log
```

---

**详细文档**: [README_FETCH_LIST_MEMBERS.md](./README_FETCH_LIST_MEMBERS.md)
