# Coding Standards

## Core Standards
- **Languages & Runtimes**: Python 3.11.7, Go 1.21.5 (严格版本控制)
- **Style & Linting**: Python (black + flake8), Go (gofmt + golint)
- **Test Organization**: 测试文件与源文件同目录，_test.py/_test.go后缀

## Critical Rules
- **日志规范**: 生产代码禁用print()，必须使用logger
- **API响应格式**: 所有API必须使用标准ResponseWrapper类型
- **数据库访问**: 必须使用Repository模式，禁止直接ORM查询
- **密钥管理**: 禁止硬编码任何密钥，必须通过配置服务获取
- **错误处理**: 外部API调用必须包含超时和重试机制
- **并发安全**: 共享状态访问必须使用锁或原子操作
