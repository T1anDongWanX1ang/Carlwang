# 代理服务 API 配置指南

## 问题诊断

如果您的 API Key 以 `cr_` 开头，这很可能是某个代理服务的 API Key，而不是标准的 Google Gemini API Key。

**症状：**
- ✅ 本地测试成功
- ❌ 远程服务器测试失败
- ❌ 错误：`API key not valid`

**原因：**
- 本地网络可以访问代理服务
- 远程服务器无法访问代理服务，或代理服务有 IP 限制

## 解决方案

### 方案 1：配置代理服务端点（如果使用代理服务）

如果您使用的是代理服务（如 Cloudflare Workers、自定义 API Gateway 等），需要在配置文件中添加 `base_url`：

```json
{
  "chatgpt": {
    "api_key": "cr_b48a34d986fc8e1cbb9395326e98398f229a99f457137f0dc728e5ce8d5c4ddd",
    "model": "gemini-2.5-flash-lite",
    "base_url": "https://your-proxy-service.com/api/v1",
    "timeout": 30,
    "max_retries": 2,
    "retry_delay": 10
  }
}
```

**如何找到代理服务端点：**
1. 查看代理服务的文档
2. 检查代理服务的配置
3. 联系代理服务提供商

### 方案 2：使用标准的 Gemini API Key（推荐）

如果代理服务不可用，建议使用标准的 Google Gemini API Key：

1. **获取标准 API Key**
   - 访问：https://aistudio.google.com/apikey
   - 创建新的 API Key（格式：`AIza...`，约39个字符）

2. **更新配置**
   ```json
   {
     "chatgpt": {
       "api_key": "AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
       "model": "gemini-2.5-flash-lite",
       "timeout": 30,
       "max_retries": 2,
       "retry_delay": 10
     }
   }
   ```

3. **移除 base_url**（如果之前配置了）
   - 标准 Gemini API 不需要 base_url

## 验证配置

更新配置后，运行测试：

```bash
python test_gemini_api.py
python diagnose_remote_issue.py
```

## 常见问题

### Q: 如何判断我的 key 是代理服务还是标准 Gemini API key？
A: 
- 标准 Gemini API Key：以 `AIza` 开头，约39个字符
- 代理服务 Key：通常以其他前缀开头（如 `cr_`），长度可能不同

### Q: 代理服务不可用时怎么办？
A: 使用标准的 Gemini API Key，这是最可靠的方案。

### Q: 可以同时支持代理和标准 API 吗？
A: 可以，代码已支持。如果配置了 `base_url`，会使用代理；否则使用标准 API。
