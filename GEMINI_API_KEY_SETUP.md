# 如何获取 Google Gemini API Key

## 步骤 1：访问 Google AI Studio

访问：https://aistudio.google.com/apikey

## 步骤 2：登录 Google 账号

使用你的 Google 账号登录

## 步骤 3：创建 API Key

1. 点击 "Create API Key" 或 "Get API Key"
2. 选择要使用的 Google Cloud 项目（如果没有项目，会提示创建）
3. 复制生成的 API Key

## 步骤 4：验证 API Key 格式

标准的 Gemini API Key：
- ✅ 以 `AIza` 开头
- ✅ 长度约 39 个字符
- ✅ 格式示例：`AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

## 步骤 5：更新配置

### 方法 1：更新配置文件

编辑 `config/config.json`：
```json
{
  "chatgpt": {
    "api_key": "AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "model": "gemini-2.5-flash-lite"
  }
}
```

### 方法 2：使用环境变量（推荐用于生产环境）

```bash
export GEMINI_API_KEY=AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export GEMINI_MODEL=gemini-2.5-flash-lite
```

## 步骤 6：测试 API Key

```bash
python test_gemini_api.py
```

## 注意事项

- ⚠️ API Key 是敏感信息，不要提交到 Git
- ⚠️ 如果 API Key 泄露，立即在 Google Cloud Console 中撤销
- ✅ 配置文件 `config/config.json` 已被 `.gitignore` 排除
- ✅ 生产环境建议使用环境变量

## 常见问题

### Q: 为什么我的 key 以 `cr_` 开头？
A: `cr_` 前缀的 key 不是标准的 Gemini API key，可能是其他服务的 key。请使用从 Google AI Studio 获取的标准 API key。

### Q: API Key 有使用限制吗？
A: 是的，免费层有配额限制。可以在 Google Cloud Console 中查看和管理配额。

### Q: 如何查看 API 使用情况？
A: 访问 Google Cloud Console > APIs & Services > Dashboard
