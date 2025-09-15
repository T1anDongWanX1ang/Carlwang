# Data Models

## Tweet
**Purpose**: 存储Twitter推文的完整信息和基础指标

**Key Attributes**:
- tweet_id: String - Twitter唯一标识符
- content: Text - 推文内容
- created_at: DateTime - 发布时间
- user_id: String - 发布用户ID (外键)
- engagement_metrics: JSON - 互动数据 {likes, retweets, replies, quotes}
- crypto_sentiment: String - crypto情感分析结果
- is_important: Boolean - 重要性判断
- entity_mentions: JSON - 提及的实体ID列表

**Relationships**:
- belongs_to User (多对一)
- relates_to Topic (多对多)
- mentions Project (多对多)

## User  
**Purpose**: 存储Twitter用户基本信息和影响力指标

**Key Attributes**:
- user_id: String - Twitter用户ID
- screen_name: String - 用户名 (@username)
- display_name: String - 显示名称
- bio: Text - 用户简介
- followers_count: Integer - 粉丝数
- following_count: Integer - 关注数
- created_at: DateTime - 账号创建时间
- is_verified: Boolean - 是否认证

**Relationships**:
- has_many Tweets (一对多)
- can_be KOL (一对一)

## KOL
**Purpose**: 关键意见领袖的专业分析和影响力量化

**Key Attributes**:
- kol_id: String - KOL唯一标识
- user_id: String - 关联User ID (外键)
- type: String - KOL类型 (founder/influencer/investor)
- influence_score: Float - 综合影响力评分 (0-100)
- call_accuracy_1h: Float - 1小时喊单准确率
- call_accuracy_24h: Float - 24小时喊单准确率  
- call_accuracy_3d: Float - 3天喊单准确率
- call_accuracy_7d: Float - 7天喊单准确率
- sentiment: String - 当前市场情绪倾向
- trust_rating: Integer - 可信度评级 (1-10)

**Relationships**:
- belongs_to User (一对一)
- interested_in Projects (多对多)
- discussed_in Topics (多对多)

## Topic
**Purpose**: 话题聚类和热度追踪

**Key Attributes**:
- topic_id: String - 话题唯一标识
- name: String - 话题名称
- description: Text - 话题描述
- created_at: DateTime - 创建时间
- popularity: Integer - 热度指标
- propagation_speed_5m: Float - 5分钟传播速度
- propagation_speed_1h: Float - 1小时传播速度
- propagation_speed_4h: Float - 4小时传播速度

**Relationships**:  
- relates_to Tweets (多对多)
- discussed_by KOLs (多对多)
- belongs_to Projects (多对多)

## Project
**Purpose**: 加密项目信息和社区情绪

**Key Attributes**:
- project_id: String - 项目唯一标识
- name: String - 项目名称
- symbol: String - 代币符号
- token_address: String - 代币合约地址
- category: String - 项目分类 (DeFi/Layer1/Layer2等)
- narrative: String - 所属叙事标签
- sentiment_index: Float - 项目情感指数 (0-100)
- popularity: Integer - 项目热度
- created_at: DateTime - 纳入系统时间

**Relationships**:
- belongs_to Narrative (多对一)
- mentioned_in Tweets (多对多)
- discussed_in Topics (多对多)

## Narrative
**Purpose**: 市场叙事和赛道分类

**Key Attributes**:
- narrative_id: String - 叙事唯一标识
- name: String - 叙事名称 (如"AI"、"DeFi"、"Layer2")
- created_at: DateTime - 创建时间
- sentiment_index: Float - 叙事整体情感 (0-100)
- popularity: Integer - 叙事热度
- summary: Text - AI生成的叙事观点总结

**Relationships**:
- has_many Projects (一对多)
- belongs_to Marco (多对一)

## Marco
**Purpose**: 宏观市场情绪和重大事件

**Key Attributes**:
- id: String - 记录唯一标识
- timestamp: DateTime - 时间戳 (每小时记录)
- sentiment_index: Float - 整体市场情感指数 (0-100)
- summary: Text - 市场事件和情绪总结

**Relationships**:
- aggregates_from Narratives (一对多)
