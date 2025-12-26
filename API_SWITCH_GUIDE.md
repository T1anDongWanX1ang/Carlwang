# AI API 切换指南

## 📊 当前配置

### 当前使用：Qwen3 API ✅

```json
{
  "chatgpt": {
    "api_type": "openai",
    "base_url": "https://api.suanli.cn/v1",
    "api_key": "sk-W0rpStc95T7JVYVwDYc29IyirjtpPPby6SozFMQr17m8KWeo",
    "model": "free:Qwen3-30B-A3B"
  }
}
```

**测试结果**：✅ API正常工作

---

## 🔄 如何切换回 Gemini API

如果需要切换回 Gemini，按以下步骤操作：

### 步骤 1：编辑配置文件

打开 `config/config.json`，找到 `chatgpt` 部分。

### 步骤 2：注释当前的 Qwen 配置

将当前的 `"chatgpt"` 改名为 `"chatgpt_backup_qwen"`：

```json
"chatgpt_backup_qwen": {
  "api_type": "openai",
  "base_url": "https://api.suanli.cn/v1",
  "api_key": "sk-W0rpStc95T7JVYVwDYc29IyirjtpPPby6SozFMQr17m8KWeo",
  "model": "free:Qwen3-30B-A3B",
  ...
}
```

### 步骤 3：恢复 Gemini 配置

将 `"chatgpt_backup_gemini"` 改名为 `"chatgpt"`：

```json
"chatgpt": {
  "api_key": "AIzaSyDd_YnZjk1fz2fg_Ekl_kqjxi_BnnrqgpE",
  "model": "gemini-2.5-flash-lite",
  "timeout": 30,
  "max_retries": 3,
  "retry_delay": 2,
  ...
}
```

**注意**：删除 `"api_type"` 和 `"base_url"` 字段（Gemini不需要这两个字段）

### 步骤 4：测试配置

```bash
# 从项目根目录运行
python test_gemini_api.py  # 如果有的话
# 或者
python test_qwen_api.py    # 修改为测试 Gemini
```

---

## 📋 配置对比

| 配置项 | Qwen3 API | Gemini API |
|--------|-----------|------------|
| `api_type` | `"openai"` | **不需要** |
| `base_url` | `"https://api.suanli.cn/v1"` | **不需要** |
| `api_key` | `sk-W0rp...KWeo` | `AIza...qgpE` |
| `model` | `"free:Qwen3-30B-A3B"` | `"gemini-2.5-flash-lite"` |

---

## ⚙️ 两种 API 的区别

### Qwen3 API (当前)
- ✅ 无地区限制
- ✅ 免费模型可用
- ✅ OpenAI 兼容格式
- ⚠️ 响应可能包含 `<think>` 标签（思考过程）

### Gemini API (备份)
- ⚠️ 有地区限制（中国大陆需要VPN）
- ✅ 响应简洁
- ⚠️ 可能需要付费配额

---

## 🧪 测试命令

### 测试当前 Qwen API
```bash
python test_qwen_api.py
```

### 测试 curl 直接调用
```bash
curl --request POST \
  --url https://api.suanli.cn/v1/chat/completions \
  --header 'Authorization: Bearer sk-W0rpStc95T7JVYVwDYc29IyirjtpPPby6SozFMQr17m8KWeo' \
  --header 'Content-Type: application/json' \
  --data '{
    "model": "free:Qwen3-30B-A3B",
    "messages": [
      {"role": "user", "content": "测试消息"}
    ]
  }'
```

---

## 📝 备注

- 配置文件已备份：`config/config.json.backup_gemini_YYYYMMDD_HHMMSS`
- Gemini 配置保存在 `chatgpt_backup_gemini` 字段中
- Qwen 配置保存在 `chatgpt` 字段中（当前使用）

---

**修改日期**：2025-12-26
**版本**：v1.0
