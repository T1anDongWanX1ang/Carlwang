# Tech Stack

## Cloud Infrastructure
- **Provider**: AWS (主平台) + GCP (多云备份)
- **Key Services**: EKS、RDS、ElastiCache、S3、Lambda、SQS/SNS
- **Deployment Regions**: us-east-1 (主), eu-west-1 (备)

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **Runtime** | Python | 3.11.7 | 数据处理和ML服务 | 丰富的数据科学生态，LLM集成支持 |
| **Runtime** | Go | 1.21.5 | 高性能API服务 | 并发性能优异，适合高QPS要求 |
| **Web Framework** | FastAPI | 0.104.1 | Python API服务框架 | 异步支持，自动API文档生成 |
| **Web Framework** | Gin | 1.9.1 | Go API服务框架 | 轻量级，高性能路由 |
| **Message Queue** | Apache Kafka | 3.6.0 | 事件流处理 | 高吞吐量，持久化消息存储 |
| **Stream Processing** | Apache Flink | 1.18.0 | 实时数据流处理 | 低延迟流处理，状态管理 |
| **Batch Processing** | Apache Spark | 3.5.0 | 历史数据批处理 | 大规模数据处理，ML支持 |
| **Database** | PostgreSQL | 16.1 | 关系数据存储 | ACID事务，复杂查询支持 |
| **Time Series DB** | InfluxDB | 2.7.4 | 指标历史数据 | 时序数据优化，高压缩比 |
| **Cache** | Redis | 7.2.3 | 热数据缓存 | 高性能键值存储，支持数据结构 |
| **Object Storage** | AWS S3 | - | 原始数据存储 | 无限扩展，成本效益 |
| **LLM Framework** | vLLM | 0.2.6 | LLM推理加速 | GPU优化，批处理支持 |
| **ML Model** | Llama-2-13B | 13B | 情感分析和NER | 开源，可fine-tune |
| **Container** | Docker | 24.0.7 | 容器化 | 标准化部署环境 |
| **Orchestration** | Kubernetes | 1.28.4 | 容器编排 | 自动扩缩容，服务发现 |
| **API Gateway** | Kong | 3.4.2 | API管理 | 认证，限流，路由 |
| **Monitoring** | Prometheus | 2.48.0 | 指标监控 | 时序指标收集 |
| **Visualization** | Grafana | 10.2.2 | 监控面板 | 灵活的仪表板 |
| **Logging** | ELK Stack | 8.11.0 | 日志管理 | 集中化日志搜索分析 |
| **CI/CD** | GitHub Actions | - | 持续集成 | 与代码仓库集成 |
| **IaC** | Terraform | 1.6.6 | 基础设施代码 | 可重复基础设施部署 |
