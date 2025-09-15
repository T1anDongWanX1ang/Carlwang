# Error Handling Strategy

## General Approach
- **Error Model**: 结构化错误响应，统一错误码体系
- **Exception Hierarchy**: 业务异常 > 技术异常 > 系统异常
- **Error Propagation**: 向上传播，在边界层转换为用户友好信息

## Logging Standards
- **Library**: Python logging + Go logrus
- **Format**: JSON结构化日志
- **Levels**: DEBUG < INFO < WARN < ERROR < FATAL
- **Required Context**:
  - Correlation ID: UUID v4格式，全链路追踪
  - Service Context: 服务名称、版本、实例ID
  - User Context: API Key hash，不记录敏感信息

## Error Handling Patterns

### External API Errors
- **Retry Policy**: 指数退避，最大重试3次
- **Circuit Breaker**: 错误率>50%时开启，60s恢复检测
- **Timeout Configuration**: Twitter API 30s，Price API 10s
- **Error Translation**: HTTP状态码映射为内部错误码

### Business Logic Errors  
- **Custom Exceptions**: InvalidKOLException, InsufficientDataException
- **User-Facing Errors**: 统一格式 {"code": "E001", "message": "描述"}
- **Error Codes**: 按模块分类 (T001-推文, K001-KOL, M001-指标)

### Data Consistency
- **Transaction Strategy**: SAGA模式处理跨服务事务
- **Compensation Logic**: 各服务实现补偿操作回滚状态
- **Idempotency**: 所有写操作支持幂等，使用请求ID去重
