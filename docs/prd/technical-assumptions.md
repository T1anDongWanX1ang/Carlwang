# Technical Assumptions

## Repository Structure: Monorepo

**选择理由**: 基于7层实体架构的复杂性和服务间的紧密关系，Monorepo能够：
- 简化跨实体服务的依赖管理和版本控制
- 便于代码复用和一致性维护（如共享的LLM推理逻辑）
- 支持原子性部署和回滚操作
- 减少微服务间的网络延迟和数据传输成本

## Service Architecture

**混合架构：领域微服务 + 共享核心**

核心架构设计：
- **7个实体微服务**: 每个实体（Tweet、Topic、User、KOL、Project、Narrative、Marco）独立微服务
- **共享服务层**: LLM推理引擎、数据采集引擎、存储抽象层作为共享服务
- **API网关**: 统一的外部API访问入口和认证授权
- **消息总线**: 基于Apache Kafka的事件驱动架构，支持实体间数据流转

**技术栈选择**:
- **后端服务**: Python (FastAPI) + Go (高性能API服务)
- **数据处理**: Apache Flink (实时流处理) + Apache Spark (批处理)
- **LLM推理**: 自部署Llama2/3 + GPU集群优化
- **容器化**: Docker + Kubernetes (生产环境)

## Testing Requirements

**全面测试金字塔策略**:
- **单元测试**: 覆盖率≥80%，重点测试业务逻辑和数据转换
- **集成测试**: 测试微服务间的API交互和数据一致性
- **端到端测试**: 模拟完整的数据流从Twitter采集到API输出
- **性能测试**: 负载测试确保满足10,000+ QPS需求
- **AI模型测试**: 专门的准确率测试和A/B测试框架

**测试工具选择**:
- **Python**: pytest, unittest, factory_boy
- **Go**: go test, testify
- **API测试**: Postman/Newman, pytest-httpx
- **性能测试**: Locust, k6
- **数据质量测试**: Great Expectations

## Additional Technical Assumptions and Requests

**数据存储策略**:
- **时间序列数据**: InfluxDB用于历史指标存储和查询优化
- **关系数据**: PostgreSQL用于实体关系和元数据
- **缓存层**: Redis用于热数据缓存和会话管理
- **对象存储**: AWS S3用于原始推文内容和模型文件

**部署和基础设施**:
- **云平台**: AWS为主平台，GCP作为多云备份
- **容器编排**: Kubernetes + Helm charts
- **CI/CD**: GitHub Actions + ArgoCD
- **监控告警**: Prometheus + Grafana + PagerDuty
- **日志管理**: ELK Stack (Elasticsearch + Logstash + Kibana)

**安全和合规**:
- **认证授权**: OAuth 2.0 + JWT tokens
- **API安全**: Rate limiting + API key management
- **数据加密**: TLS 1.3传输加密 + AES-256静态数据加密
- **合规框架**: GDPR和CCPA数据处理合规

**成本优化技术假设**:
- **自动伸缩**: HPA (Horizontal Pod Autoscaler) 基于CPU/内存使用率
- **GPU资源池**: 共享GPU集群用于LLM推理，支持动态调度
- **存储分层**: 热数据SSD + 温数据HDD + 冷数据Glacier
- **CDN加速**: CloudFlare用于静态资源和API响应缓存
