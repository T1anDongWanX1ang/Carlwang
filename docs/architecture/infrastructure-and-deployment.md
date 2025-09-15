# Infrastructure and Deployment

## Infrastructure as Code
- **Tool**: Terraform 1.6.6
- **Location**: `infrastructure/terraform/`
- **Approach**: 模块化IaC，按环境分离配置

## Deployment Strategy
- **Strategy**: 蓝绿部署 + 金丝雀发布
- **CI/CD Platform**: GitHub Actions
- **Pipeline Configuration**: `.github/workflows/`

## Environments
- **Development**: 本地开发环境 - Docker Compose + 简化版数据
- **Staging**: 预生产环境 - 完整功能测试，真实数据子集
- **Production**: 生产环境 - 多区域部署，完整监控告警

## Environment Promotion Flow
```
Development → Staging → Production
     ↑            ↑          ↑
   本地测试    集成测试    生产监控
   单元测试    性能测试    回滚准备
```

## Rollback Strategy
- **Primary Method**: Kubernetes滚动回滚 + 蓝绿切换
- **Trigger Conditions**: 错误率>5%, 响应时间>1s, 健康检查失败
- **Recovery Time Objective**: < 5分钟
