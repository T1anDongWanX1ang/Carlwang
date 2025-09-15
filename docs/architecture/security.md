# Security

## Input Validation
- **Validation Library**: Python Pydantic, Go validator
- **Validation Location**: API边界层统一验证
- **Required Rules**:
  - 所有外部输入必须验证
  - API边界验证优于业务逻辑验证  
  - 白名单方式优于黑名单

## Authentication & Authorization
- **Auth Method**: JWT Token + API Key双重认证
- **Session Management**: 无状态JWT，Redis存储撤销列表
- **Required Patterns**:
  - API Key用于服务识别和计费
  - JWT Token用于用户会话和权限

## Secrets Management
- **Development**: .env文件 + git-secret加密
- **Production**: AWS Secrets Manager
- **Code Requirements**:
  - 绝不硬编码密钥
  - 仅通过配置服务访问
  - 日志和错误消息中不包含密钥

## API Security  
- **Rate Limiting**: Kong Gateway实现，按API Key限流
- **CORS Policy**: 严格域名白名单
- **Security Headers**: HSTS, CSP, X-Frame-Options等
- **HTTPS Enforcement**: 全站HTTPS，HTTP自动重定向

## Data Protection
- **Encryption at Rest**: AES-256数据库加密
- **Encryption in Transit**: TLS 1.3强制加密
- **PII Handling**: 用户数据脱敏，最小化收集
- **Logging Restrictions**: 禁止记录密钥、个人信息、完整IP

## Dependency Security
- **Scanning Tool**: Snyk + GitHub Dependabot
- **Update Policy**: 安全补丁7天内更新
- **Approval Process**: 新依赖需架构师审批

## Security Testing
- **SAST Tool**: SonarQube代码静态分析
- **DAST Tool**: OWASP ZAP动态安全测试  
- **Penetration Testing**: 季度第三方渗透测试

---

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>