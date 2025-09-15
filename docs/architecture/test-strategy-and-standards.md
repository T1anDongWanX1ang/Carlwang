# Test Strategy and Standards

## Testing Philosophy
- **Approach**: TDD优先，测试金字塔结构
- **Coverage Goals**: 单元测试>80%，集成测试>70%
- **Test Pyramid**: 70%单元测试，20%集成测试，10%端到端测试

## Test Types and Organization

### Unit Tests
- **Framework**: Python pytest 7.4.3, Go testing + testify
- **File Convention**: test_*.py, *_test.go
- **Location**: 与源文件同目录
- **Mocking Library**: Python unittest.mock, Go gomock
- **Coverage Requirement**: 每个公开方法必须测试

**AI Agent Requirements**:
- 为所有公开方法生成测试
- 覆盖边界条件和错误情况
- 遵循AAA模式 (Arrange, Act, Assert)
- Mock所有外部依赖

### Integration Tests
- **Scope**: 服务间API调用，数据库操作，消息队列
- **Location**: tests/integration/
- **Test Infrastructure**:
  - **PostgreSQL**: Testcontainers启动真实数据库
  - **Redis**: 嵌入式Redis实例
  - **Kafka**: Embedded Kafka for tests

### End-to-End Tests  
- **Framework**: Python pytest + requests
- **Scope**: 完整用户场景，跨服务数据流
- **Environment**: 独立测试环境
- **Test Data**: 固定测试数据集，自动清理

## Test Data Management
- **Strategy**: Factory模式 + 固定Fixture
- **Fixtures**: tests/fixtures/目录
- **Factories**: 使用factory_boy生成测试数据
- **Cleanup**: 测试后自动清理，隔离数据污染

## Continuous Testing
- **CI Integration**: PR检查 > 集成测试 > 部署测试
- **Performance Tests**: Locust负载测试，每日运行
- **Security Tests**: SAST (SonarQube) + DAST (OWASP ZAP)
