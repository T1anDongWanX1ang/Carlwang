# Source Tree

```plaintext
ct_data_pipeline/
├── services/                           # 微服务目录
│   ├── data-collector/                 # 数据采集服务
│   │   ├── src/
│   │   │   ├── collectors/            # Twitter API采集器
│   │   │   ├── processors/            # 数据预处理
│   │   │   └── publishers/            # Kafka发布者
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── llm-inference/                  # LLM推理服务
│   │   ├── src/
│   │   │   ├── models/               # 模型加载和管理
│   │   │   ├── inference/            # 推理引擎
│   │   │   └── cache/                # 推理结果缓存
│   │   ├── models/                   # 预训练模型文件
│   │   └── requirements.txt
│   ├── metrics-engine/                # 指标计算引擎
│   │   ├── src/
│   │   │   ├── calculators/          # 各类指标计算器
│   │   │   ├── aggregators/          # 数据聚合器
│   │   │   └── schedulers/           # 定时任务调度
│   │   └── flink-jobs/               # Flink作业定义
│   ├── tweet-service/                 # Tweet实体服务
│   │   ├── src/
│   │   │   ├── handlers/             # HTTP处理器
│   │   │   ├── models/               # 数据模型
│   │   │   ├── repositories/         # 数据访问层
│   │   │   └── events/               # 事件处理
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   ├── kol-service/                   # KOL服务
│   │   ├── src/
│   │   │   ├── identification/       # KOL识别算法
│   │   │   ├── influence/           # 影响力计算
│   │   │   ├── tracking/            # 喊单追踪
│   │   │   └── classification/      # KOL分类
│   │   └── requirements.txt
│   ├── user-service/                  # 用户服务
│   ├── topic-service/                 # 话题服务
│   ├── project-service/               # 项目服务
│   ├── narrative-service/             # 叙事服务
│   ├── marco-service/                 # 宏观服务
│   └── api-gateway/                   # API网关
│       ├── src/
│       │   ├── routes/               # 路由定义
│       │   ├── middleware/           # 中间件
│       │   ├── auth/                 # 认证授权
│       │   └── rate-limiting/        # 限流控制
│       ├── go.mod
│       └── Dockerfile
├── shared/                            # 共享库和工具
│   ├── models/                       # 共享数据模型
│   ├── events/                       # 事件定义
│   ├── clients/                      # 外部API客户端
│   ├── utils/                        # 工具函数
│   └── config/                       # 配置管理
├── infrastructure/                    # 基础设施代码
│   ├── terraform/                    # Terraform IaC
│   │   ├── environments/
│   │   │   ├── dev/
│   │   │   ├── staging/
│   │   │   └── production/
│   │   ├── modules/
│   │   │   ├── kubernetes/
│   │   │   ├── databases/
│   │   │   └── networking/
│   │   └── main.tf
│   ├── kubernetes/                   # K8s资源定义
│   │   ├── base/
│   │   └── overlays/
│   └── docker-compose/               # 本地开发环境
│       ├── docker-compose.yml
│       └── docker-compose.override.yml
├── scripts/                          # 构建和部署脚本
│   ├── build.sh
│   ├── deploy.sh
│   ├── migrate.sh
│   └── seed-data.sh
├── docs/                             # 文档目录
│   ├── api/                          # API文档
│   ├── architecture/                 # 架构文档
│   └── deployment/                   # 部署指南
├── tests/                            # 集成测试
│   ├── e2e/                         # 端到端测试
│   ├── integration/                 # 集成测试
│   └── load/                        # 负载测试
├── .github/                          # GitHub Actions
│   └── workflows/
│       ├── ci.yml
│       ├── cd.yml
│       └── security-scan.yml
├── go.work                           # Go workspace配置
├── docker-compose.yml                # 开发环境
├── Makefile                          # 构建命令
└── README.md
```
