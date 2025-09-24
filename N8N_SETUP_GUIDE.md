# N8N Twitter Topics Analysis 工作流配置指南

## 📋 概述

这个文档详细介绍如何导入和配置 `n8n-twitter-topics-workflow.json` 文件，实现自动化的Twitter主题分析功能。

## 🚀 快速开始

### 1. 导入工作流

1. **打开n8n界面**
   - 访问你的n8n实例 (通常是 `http://localhost:5678`)
   - 登录你的n8n账户

2. **导入工作流文件**
   ```bash
   # 方法1: 在n8n界面中导入
   # 1. 点击右上角的 "+" 按钮
   # 2. 选择 "Import from file"
   # 3. 选择 n8n-twitter-topics-workflow.json 文件
   
   # 方法2: 通过命令行导入（如果有CLI访问权限）
   curl -X POST http://localhost:5678/rest/workflows/import \
     -H "Content-Type: application/json" \
     -d @n8n-twitter-topics-workflow.json
   ```

### 2. 配置必需的凭据

#### 2.1 TweetScout API凭据
```bash
# 在n8n中添加环境变量
TWEETSCOUT_API_KEY=your_tweetscout_api_key_here
```

#### 2.2 OpenAI API凭据
在n8n中创建OpenAI凭据：
- **Credential Type**: OpenAI
- **API Key**: 你的OpenAI API密钥
- **Organization ID**: (可选)

#### 2.3 MySQL数据库凭据
在n8n中创建MySQL凭据：
- **Host**: 你的数据库主机地址
- **Database**: 数据库名称
- **Username**: 数据库用户名
- **Password**: 数据库密码
- **Port**: 数据库端口 (通常是3306)

### 3. 数据库表结构

确保你的MySQL数据库中有以下表结构：

```sql
CREATE TABLE IF NOT EXISTS `topics` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `timestamp` datetime NOT NULL COMMENT '时间戳（30分钟对齐）',
  `topic_summary` text COMMENT '主要话题摘要',
  `topics_json` longtext COMMENT '详细话题数据(JSON格式)',
  `sentiment_data` text COMMENT '情感分析数据(JSON格式)',
  `sentiment_score` decimal(5,3) DEFAULT '0.000' COMMENT '情感得分(-1到1)',
  `categories_json` text COMMENT '类别分析数据(JSON格式)',
  `total_tweets` int(11) DEFAULT '0' COMMENT '分析的推文总数',
  `high_quality_tweets` int(11) DEFAULT '0' COMMENT '高质量推文数量',
  `avg_engagement` decimal(10,2) DEFAULT '0.00' COMMENT '平均互动数',
  `trend_score` decimal(8,2) DEFAULT '0.00' COMMENT '趋势得分',
  `confidence_score` decimal(5,3) DEFAULT '0.000' COMMENT '分析置信度',
  `status` varchar(50) DEFAULT 'pending' COMMENT '处理状态',
  `processing_info` text COMMENT '处理信息(JSON格式)',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_timestamp` (`timestamp`),
  KEY `idx_timestamp` (`timestamp`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Twitter话题分析结果表';
```

## ⚙️ 详细配置

### 环境变量配置

在n8n的环境变量中添加以下配置：

```bash
# 必需变量
TWEETSCOUT_API_KEY=678dd1dd-d278-46e9-a6f1-a28dea950469
OPENAI_API_KEY=sk-your-openai-api-key-here

# 可选变量
WEBHOOK_NOTIFICATION_URL=https://your-webhook-url.com/notify
ERROR_WEBHOOK_URL=https://your-error-monitoring-url.com/webhook
```

### 工作流节点详细配置

#### 1. Schedule Trigger (定时触发器)
- **触发频率**: 每30分钟
- **时区**: Asia/Shanghai
- **自动激活**: 是

#### 2. Fetch Twitter Data (HTTP请求)
- **URL**: `https://api.tweetscout.io/v2/list-tweets`
- **方法**: GET
- **认证**: Header认证
- **重试次数**: 3次
- **超时时间**: 30秒

#### 3. Preprocess Data (代码节点)
- **功能**: 过滤和预处理推文数据
- **过滤条件**: 
  - 转发数 > 5
  - 文本长度 50-2000字符
  - 移除无效数据

#### 4. Clean Text (代码节点)
- **功能**: 文本清洗和标准化
- **处理内容**:
  - 移除URL链接
  - 移除@用户名
  - 标准化空格和特殊字符
  - 计算质量分数

#### 5. AI Topic Analysis (OpenAI节点)
- **模型**: gpt-3.5-turbo
- **温度**: 0.3
- **最大tokens**: 500
- **响应格式**: JSON对象

#### 6. Aggregate Topics (代码节点)
- **功能**: 聚合分析结果
- **输出字段**:
  - 热门话题排行
  - 情感分布统计
  - 类别分析
  - 质量指标

#### 7. Save to Database (MySQL节点)
- **操作**: 插入记录
- **表名**: topics
- **批处理**: 单条记录

#### 8. Send Notification (HTTP请求 - 可选)
- **功能**: 发送完成通知
- **格式**: JSON格式的webhook

## 🔧 高级配置

### 自定义参数调整

1. **修改分析频率**
   ```json
   // 在Schedule Trigger节点中修改
   "interval": [
     {
       "field": "minutes",
       "minutesInterval": 15  // 改为15分钟
     }
   ]
   ```

2. **调整推文过滤条件**
   ```javascript
   // 在Preprocess Data节点中修改
   .filter(tweet => {
     const retweetCount = tweet.public_metrics?.retweet_count || 0;
     const textLength = (tweet.text || '').length;
     return retweetCount > 10 && textLength > 100; // 提高质量标准
   })
   ```

3. **自定义AI提示词**
   ```json
   // 在AI Topic Analysis节点中修改system message
   {
     "role": "system",
     "content": "你的自定义提示词内容..."
   }
   ```

### 错误处理配置

1. **启用重试机制**
   - HTTP请求节点设置重试次数
   - 添加指数退避延迟

2. **错误通知**
   - 配置错误webhook URL
   - 设置邮件/Slack通知

3. **降级策略**
   - API失败时使用备用数据源
   - 分析失败时使用基础算法

## 📊 监控和维护

### 工作流监控

1. **执行历史**
   - 在n8n界面查看执行日志
   - 监控成功/失败率
   - 分析性能指标

2. **数据质量检查**
   ```sql
   -- 检查最近的topics数据
   SELECT 
     timestamp,
     total_tweets,
     status,
     confidence_score,
     created_at
   FROM topics 
   ORDER BY created_at DESC 
   LIMIT 10;
   
   -- 检查成功率
   SELECT 
     status,
     COUNT(*) as count,
     ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
   FROM topics 
   WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
   GROUP BY status;
   ```

3. **性能优化**
   - 监控执行时间
   - 优化AI提示词长度
   - 调整批处理大小

### 常见问题排查

1. **API配额超限**
   - 检查TweetScout API使用量
   - 调整请求频率
   - 考虑使用多个API密钥轮换

2. **数据库连接问题**
   - 验证数据库凭据
   - 检查网络连接
   - 监控数据库性能

3. **AI分析失败**
   - 检查OpenAI API配额
   - 优化提示词
   - 添加fallback机制

## 🚀 部署建议

### 生产环境配置

1. **高可用性**
   ```bash
   # 使用Docker Compose部署n8n
   version: '3.8'
   services:
     n8n:
       image: n8nio/n8n
       ports:
         - "5678:5678"
       environment:
         - DB_TYPE=postgresdb
         - DB_POSTGRESDB_HOST=postgres
         - DB_POSTGRESDB_USER=n8n
         - DB_POSTGRESDB_PASSWORD=n8n
       volumes:
         - n8n_data:/home/node/.n8n
       restart: unless-stopped
   ```

2. **安全配置**
   - 使用HTTPS
   - 配置防火墙规则
   - 定期更新密钥
   - 启用访问日志

3. **备份策略**
   - 定期备份工作流配置
   - 备份数据库数据
   - 版本控制工作流文件

## 📞 技术支持

如果在配置过程中遇到问题：

1. **检查日志**
   - n8n执行日志
   - 数据库错误日志
   - API响应日志

2. **测试连接**
   - 手动测试各个API
   - 验证数据库连接
   - 检查网络连通性

3. **参考文档**
   - [n8n官方文档](https://docs.n8n.io/)
   - [TweetScout API文档](https://tweetscout.io/docs)
   - [OpenAI API文档](https://platform.openai.com/docs)

通过以上配置，你就可以成功运行这个自动化的Twitter主题分析工作流了！