# AI 提示词文档

本文档记录了 Twitter 数据爬虫项目中所有使用 ChatGPT API 的提示词（Prompts）和相关逻辑。

## 📚 目录

1. [话题分析](#1-话题分析)
2. [情感分析](#2-情感分析)
3. [KOL 分析](#3-kol-分析)
4. [项目分析](#4-项目分析)
5. [Token 与公告分析](#5-token-与公告分析)
6. [配置参数](#6-配置参数)

---

## 1. 话题分析

### 1.1 话题提取 (extract_topic_from_tweet)

**功能**: 从单条推文中提取主要话题名称和简要描述

**System Prompt**:
```
You are a professional cryptocurrency market analyst skilled in identifying and analyzing cryptocurrency-related topics.
```

**User Prompt**:
```
Please analyze the following cryptocurrency-related tweet and extract the main topic:

Tweet content: {tweet_content}

Please provide:
1. topic_name: Concise topic name (5-15 words, highlighting the core theme)
2. brief: Brief topic description (20-50 words, explaining topic content and background)

Notes:
- If the tweet is pure advertising or spam content, return "Invalid Topic"
- Focus on cryptocurrency, blockchain, DeFi, NFT and related themes
- Topic name should be specific and meaningful

Please return in JSON format:
{"topic_name": "Topic Name", "brief": "Topic Description"}
```

**参数**:
- temperature: `0.3`
- max_tokens: `200`

**返回格式**:
```json
{
  "topic_name": "Ethereum Shanghai Upgrade",
  "brief": "Ethereum network's major upgrade enabling ETH withdrawals from staking"
}
```

---

### 1.2 话题总结生成 (generate_topic_summary)

**功能**: 生成话题的 KOL 观点分析总结

**System Prompt**:
```
You are an experienced web3 media editor, skilled at quickly organizing and summarizing KOL opinions from crypto-related trending topics.
```

**User Prompt (新话题)**:
```
You will receive multiple tweets about topic "{topic_name}" in the following format:

Related Tweets:
{tweets_text}

Please summarize the consensus opinions of KOLs on this event (sorted by number of KOLs holding the same opinion, output top 3 opinions, can be less than 3), in the following JSON format:
{
  "topic_id": "{topic_name}",
  "summary": [
    {
      "viewpoint": "Opinion summary",
      "related_tweets": ["Tweet content excerpts reflecting this opinion"]
    }
  ]
}

Output only the above JSON without additional explanation.
```

**User Prompt (更新现有话题)**:
```
Please update the KOL opinion summary for topic "{topic_name}", combining new tweet content:

Existing Summary:
{existing_summary}

New Tweet Content:
{tweets_text}

Please update the KOL consensus opinions in the following JSON format (sorted by number of KOLs holding the same opinion, output top 3 opinions):
{
  "topic_id": "{topic_name}",
  "summary": [
    {
      "viewpoint": "Opinion summary",
      "related_tweets": ["Tweet content excerpts reflecting this opinion"]
    }
  ]
}

Output only the above JSON without additional explanation.
```

**参数**:
- temperature: `0.3`
- max_tokens: `500`

---

## 2. 情感分析

### 2.1 推文情感分析 (analyze_sentiment)

**功能**: 分析推文的情感倾向和置信度

**System Prompt**:
```
You are a professional cryptocurrency sentiment analyst skilled in understanding market sentiment and investor psychology.
```

**User Prompt**:
```
Please analyze the sentiment tendency of the following cryptocurrency-related text:

Text content: {text}

Please evaluate:
1. sentiment: Sentiment direction (positive/negative/neutral)
2. confidence: Confidence level (0.0-1.0, indicating certainty of judgment)
3. reasoning: Reasoning for judgment (brief explanation)

Notes:
- Focus on cryptocurrency market sentiment
- Consider the meaning of technical terms and slang
- positive: bullish, optimistic, supportive
- negative: bearish, pessimistic, critical
- neutral: neutral, objective analysis

Please return in JSON format:
{"sentiment": "positive", "confidence": 0.8, "reasoning": "Reasoning"}
```

**参数**:
- temperature: `0.2`
- max_tokens: `150`

**返回格式**:
```json
{
  "sentiment": "positive",
  "confidence": 0.85,
  "score": 92.5,
  "reasoning": "The tweet expresses strong optimism about the project's technical progress"
}
```

**Score 计算逻辑**:
- **positive**: `score = 50 + (confidence * 50)` → 范围 [50-100]
- **negative**: `score = 50 - (confidence * 50)` → 范围 [0-50]
- **neutral**: `score = 50` → 固定值 50

---

### 2.2 项目情感指数 (calculate_project_sentiment)

**功能**: 根据多条推文计算项目的整体情感指数 (0-100)

**System Prompt**:
```
You are a professional cryptocurrency sentiment analysis expert skilled in quantifying community sentiment.
```

**User Prompt**:
```
Please analyze the overall sentiment tendency of the following tweets toward the cryptocurrency project:

Tweet Content:
{tweets_text}

Analysis Framework:
- Positive sentiment (70-100 points): bullish predictions, technical breakthroughs, partnership news, institutional adoption
- Neutral sentiment (30-70 points): objective analysis, technical discussion, neutral reporting
- Negative sentiment (0-30 points): bearish predictions, risk warnings, technical issues, negative news

Please consider comprehensively:
1. Emotional tone and language of tweets
2. Price predictions and market expectations
3. Technical development and project progress
4. Risk factors and concerns
5. Community activity and engagement

Please return a sentiment index score from 0-100 with a brief explanation of the rating.

Format:
{
  "sentiment_index": 75.5,
  "reasoning": "Overall sentiment is positive, mainly based on technical progress and market expectations..."
}
```

**参数**:
- temperature: `0.2`
- max_tokens: `200`
- 推文样本: 最多 15 条

**返回**: float (0-100)

---

### 2.3 散户观点方向 (analyze_mob_opinion_direction)

**功能**: 分析散户整体观点方向

**System Prompt**:
```
You are a professional market sentiment analyst skilled in analyzing collective emotions of retail investors.
```

**User Prompt**:
```
Please analyze the overall opinion direction of retail investors in the following tweets:

Tweet content:
{tweets_text}

Please evaluate the overall sentiment tendency of retail investors:
- positive: Overall optimistic, bullish, supportive
- negative: Overall pessimistic, bearish, critical
- neutral: Divided opinions or neutral

Return only one word: positive, negative or neutral
```

**参数**:
- temperature: `0.1`
- max_tokens: `10`
- 推文样本: 最多 20 条

**返回**: `"positive"` | `"negative"` | `"neutral"`

---

## 3. KOL 分析

### 3.1 KOL 特征分析 (analyze_kol_profile)

**功能**: 分析用户是否为加密货币 KOL，并提供详细分析

**System Prompt**:
```
你是一个专业的加密货币KOL识别和分析专家，擅长评估影响力和专业度。
```

**User Prompt**:
```
请分析以下Twitter用户是否为加密货币KOL，并提供详细分析：

用户信息:
- 用户名: @{screen_name}
- 显示名: {name}
- 粉丝数: {followers_count}
- 关注数: {friends_count}
- 推文数: {statuses_count}
- 简介: {description}

最近推文内容:
{tweets_text}

请提供以下分析：
1. type: KOL类型（founder/influencer/investor/trader/analyst 或 "not_kol"）
2. tags: 多个标签列表，必须包含语言标签，格式要求：
   - 语言标签：根据推文主要语言选择"English"或"Chinese"（必须包含）
   - 专业标签：基于推文内容的专业领域，如BTC/ETH/DeFi/NFT/Meme/AI/Gaming/Layer2/RWA等
   - 可以有2-5个标签
3. sentiment: 市场情感倾向（bullish/bearish/neutral）
4. summary: 简要总结（50-100字，描述其观点特点和影响力）
5. trust_rating: 可信度评级（1-10，基于专业度和一致性）

注意：
- 如果不是加密货币相关KOL，type返回 "not_kol"
- tags必须是数组格式，第一个标签必须是语言标签
- 专注于加密货币、区块链领域的影响力
- 考虑粉丝数、互动质量和内容专业度

请以JSON格式返回：
{
    "type": "influencer",
    "tags": ["{language_tag}", "DeFi", "BTC"],
    "sentiment": "bullish",
    "summary": "专业的DeFi分析师，经常分享技术分析...",
    "trust_rating": 8
}
```

**参数**:
- temperature: `0.3`
- max_tokens: `300`
- 推文样本: 最多 10 条

**返回格式**:
```json
{
  "type": "influencer",
  "tag": "English,DeFi,Layer2",
  "sentiment": "bullish",
  "summary": "专业的DeFi分析师，经常分享技术分析和市场洞察",
  "trust_rating": 8
}
```

**KOL 类型**:
- `founder`: 项目创始人
- `influencer`: 影响者/意见领袖
- `investor`: 投资者
- `trader`: 交易员
- `analyst`: 分析师
- `not_kol`: 非KOL

**语言检测逻辑**:
- 统计中文字符占比 > 30% → `Chinese`
- 其他 → `English`

**备用分析** (当 ChatGPT 不可用时):
使用基于关键词的规则引擎 (`_fallback_kol_analysis`)

---

### 3.2 KOL 总结生成 (generate_kol_summary)

**功能**: 为 KOL 生成专业观点总结

**System Prompt**:
```
你是一个专业的加密货币市场分析师，擅长分析KOL的观点和影响力。
```

**User Prompt**:
```
请为以下加密货币KOL生成专业总结：

KOL信息:
- 用户名: @{screen_name}
- 类型: {kol_type}
- 粉丝数: {followers_count}

最近推文:
{tweets_text}

请提供KOL的观点总结，包括：
1. 主要关注的项目和赛道
2. 市场观点和预测倾向
3. 影响力和专业特点
4. 近期重要观点

要求：
- 客观专业的语调
- 100-200字以内
- 突出其独特观点和影响力

请直接返回总结文本。
```

**参数**:
- temperature: `0.4`
- max_tokens: `250`
- 推文样本: 最多 15 条

---

## 4. 项目分析

### 4.1 项目识别与分类 (analyze_projects_in_tweets)

**功能**: 从推文中识别和分析加密货币项目

**System Prompt**:
```
You are a professional cryptocurrency project analysis expert skilled in identifying projects from tweets and conducting in-depth analysis.
```

**User Prompt**:
```
You are a professional cryptocurrency project analysis expert. Please identify, analyze and classify cryptocurrency projects from the following tweets.

Tweet content:
{tweets_content}

Please analyze according to the following rules:

1. **Project Identification Rules**:
- Identify complete project names (e.g., "Ethereum", "Uniswap")
- Identify token symbols (e.g., "ETH", "UNI", "BTC")
- Identify aliases (e.g., "Ethereum", "Bitcoin", "ETH")
- Confirm genuine cryptocurrency project discussions

2. **Project Classification System**:
- Layer1: Bitcoin, Ethereum, Solana, Cardano
- Layer2: Arbitrum, Optimism, Polygon, Base
- DeFi: Uniswap, AAVE, Compound, MakerDAO
- GameFi: Axie Infinity, The Sandbox
- NFT: OpenSea, Blur, LooksRare
- Infrastructure: Chainlink, The Graph
- Meme: Dogecoin, Shiba Inu, PEPE
- AI: Fetch.ai, SingularityNET
- Privacy: Monero, Zcash

3. **Narrative Tag System**:
- Technical narratives: "Scalability", "Interoperability", "Privacy"
- Application narratives: "DeFi Summer", "NFT Boom", "GameFi", "RWA"
- Ecosystem narratives: "Ethereum Killers", "Multi-chain"
- Emerging narratives: "AI+Crypto", "DePin", "Liquid Staking"

4. **Sentiment Analysis Framework**:
- Positive sentiment (70-100 points): bullish, recommendation, technical breakthrough
- Neutral sentiment (30-70 points): objective analysis, technical discussion
- Negative sentiment (0-30 points): bearish, risk warning

Please return analysis results in JSON format:
{
    "projects": [
        {
            "project_id": "ethereum_eth",
            "name": "Ethereum",
            "symbol": "ETH",
            "category": "Layer1",
            "narratives": ["Smart Contract Platform", "DeFi"],
            "sentiment_index": 75.5,
            "popularity_score": 850,
            "summary": "Ethereum discussions mainly focus on technical upgrades...",
            "confidence_score": 0.95,
            "total_mentions": 5
        }
    ],
    "analysis_summary": {
        "total_projects_identified": 3,
        "dominant_narratives": ["DeFi", "Layer2"],
        "overall_market_sentiment": "bullish"
    }
}
```

**参数**:
- temperature: `0.3`
- max_tokens: `2000`
- 推文样本: 最多 20 条

---

### 4.2 项目总结生成 (generate_project_summary)

**功能**: 生成项目的社区讨论总结

**System Prompt**:
```
You are a professional cryptocurrency project analyst skilled in analyzing project community sentiment and market performance.
```

**User Prompt**:
```
Please generate a professional summary for the cryptocurrency project:

Project Information:
- Name: {name}
- Symbol: {symbol}
- Category: {category}
- Narratives: {narratives}

Related Tweet Discussions:
{tweets_text}

Please provide a community discussion summary for the project, including:
1. Main discussion focus and trending topics
2. Community sentiment and market expectations
3. KOL opinions and professional analysis
4. Project development updates and technical progress
5. Risk factors and concerns

Requirements:
- Objective and professional tone
- 120-150 words
- Highlight the project's unique value and market position
- Reflect latest community discussion trends

Please return the summary text directly.
```

**参数**:
- temperature: `0.4`
- max_tokens: `350`
- 推文样本: 最多 10 条

---

## 5. Token 与公告分析

### 5.1 Token 符号提取 (extract_token_symbols_from_tweet)

**功能**: 从推文中提取加密货币 token symbols

**System Prompt**:
```
You are a professional cryptocurrency analyst skilled in identifying token symbols from social media content.
```

**User Prompt**:
```
Please analyze the following cryptocurrency-related tweet and extract all mentioned token symbols.

Tweet content: {tweet_content}

Please identify:
1. All cryptocurrency token symbols mentioned (e.g., BTC, ETH, SOL, USDT)
2. Include symbols with $ prefix (e.g., $BTC, $ETH)
3. Include full names that can be mapped to symbols (e.g., "Bitcoin" -> BTC, "Ethereum" -> ETH)

Requirements:
- Only extract valid cryptocurrency token symbols (2-10 uppercase letters)
- Exclude common words that look like symbols but are not (e.g., "TO", "FOR", "AND")
- Return empty list if no valid symbols found
- Return at most 10 symbols

Please return in JSON format:
{"symbols": ["BTC", "ETH", "SOL"]}

If no valid symbols found, return:
{"symbols": []}
```

**参数**:
- temperature: `0.1`
- max_tokens: `150`

**返回格式**:
```json
["BTC", "ETH", "UNI"]
```

**后处理逻辑**:
1. 移除 `$` 前缀
2. 转换为大写
3. 验证长度 2-10 字符
4. 去重
5. 限制最多 10 个

---

### 5.2 公告分类识别 (classify_tweet_announcement)

**功能**: 判断推文是否为重要公告

**System Prompt**:
```
You are a professional crypto content analyst skilled in identifying important announcements from project tweets.
```

**User Prompt**:
```
You are given the content of a tweet from the official account of a crypto project.
Your task is to determine whether the tweet falls into one or more of the following categories:

* **key ecosystem partners & collaborations**: announcements about strategic partners, ecosystem alliances, collaborations with other projects or companies.
* **Community space and other events**: announcements about AMA sessions, Twitter Spaces, conferences, hackathons, offline/online meetups, or community-related activities.
* **Major Tech Updates**: announcements about new product releases, protocol upgrades, mainnet/testnet launches, technical milestones, or major software updates.

Tweet content: {tweet_content}

Please analyze the tweet and determine if it matches ANY of the above categories.

Return in JSON format:
{"is_announcement": true or false, "categories": ["category1", "category2"], "reason": "brief explanation"}

If the tweet does NOT match any category, return:
{"is_announcement": false, "categories": [], "reason": "brief explanation"}
```

**参数**:
- temperature: `0.1`
- max_tokens: `200`

**返回**:
- `1`: 是重要公告
- `0`: 不是重要公告

**公告类别**:
1. **key ecosystem partners & collaborations** - 重要生态合作伙伴
2. **Community space and other events** - 社区活动
3. **Major Tech Updates** - 重大技术更新

---

### 5.3 公告总结生成 (summarize_announcement)

**功能**: 生成简洁的公告总结 (最多 50 字或 50 词)

**System Prompt**:
```
You are a professional crypto announcement editor skilled in creating concise, formal summaries from social media posts.
```

**User Prompt**:
```
You are a professional crypto project announcement editor. Your task is to transform the following tweet into a concise, professional announcement summary.

Original tweet: {tweet_content}

Requirements:
1. Rewrite the tweet to sound like an official announcement rather than a casual social media post
2. Keep it concise: maximum 50 characters in Chinese OR 50 words in English
3. Focus on the key announcement content (what is happening, when, who is involved)
4. Use professional and formal tone
5. Remove casual language, emojis, and unnecessary details
6. Preserve important information like dates, partner names, event names, or technical updates

Return ONLY the summary text without any additional explanation or formatting.

Example:
Input: "🎉 Excited to announce our partnership with @ABC! This is huge for our ecosystem! Stay tuned for more details 🚀"
Output: "Partnership announced with ABC to expand ecosystem capabilities"

Now generate the summary:
```

**参数**:
- temperature: `0.3`
- max_tokens: `100`

**示例**:
```
Input: "🎉 Excited to announce our partnership with Chainlink! This is huge! 🚀"
Output: "Partnership announced with Chainlink to enhance oracle capabilities"
```

---

## 6. 配置参数

### 6.1 通用配置

**模型设置** (config/config.json):
```json
{
  "chatgpt": {
    "api_key": "YOUR_API_KEY",
    "model": "gpt-3.5-turbo",
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 2
  }
}
```

### 6.2 批处理优化

**批处理配置**:
```json
{
  "batch_processing": {
    "content_merge_threshold": 2000
  },
  "optimization": {
    "enable_batch_consolidation": true,
    "max_prompt_tokens": 3000,
    "enable_response_caching": true,
    "cache_ttl_hours": 24
  }
}
```

**功能说明**:
- **批处理合并**: 相似推文合并处理，减少 API 调用
- **响应缓存**: 缓存结果 24 小时，避免重复请求
- **相似度阈值**: Jaccard 相似度 > 30% 视为相似内容

### 6.3 Temperature 参数说明

| 功能 | Temperature | 说明 |
|------|-------------|------|
| Token 提取 | 0.1 | 需要高准确性 |
| 公告分类 | 0.1 | 需要明确判断 |
| 散户观点 | 0.1 | 简单分类 |
| 情感分析 | 0.2 | 相对准确 |
| 项目情感 | 0.2 | 数值计算 |
| 话题提取 | 0.3 | 平衡创造性 |
| KOL 分析 | 0.3 | 需要分析 |
| 项目识别 | 0.3 | 复杂分类 |
| 公告总结 | 0.3 | 创造性改写 |
| KOL 总结 | 0.4 | 需要创造性 |
| 项目总结 | 0.4 | 综合分析 |

---

## 7. 最佳实践

### 7.1 错误处理

所有 AI 调用都包含：
1. **重试机制**: 最多 3 次重试
2. **超时处理**: 30 秒超时
3. **速率限制**: 自动延迟重试
4. **备用逻辑**: KOL 分析有基于规则的备用方案

### 7.2 JSON 清理

所有 JSON 响应都经过清理：
```python
# 移除 markdown 代码块标记
if cleaned_response.startswith('```json'):
    cleaned_response = cleaned_response[7:]
if cleaned_response.startswith('```'):
    cleaned_response = cleaned_response[3:]
if cleaned_response.endswith('```'):
    cleaned_response = cleaned_response[:-3]
```

### 7.3 成本优化

1. **批处理合并**: 相似内容合并处理
2. **响应缓存**: 24 小时缓存避免重复
3. **推文限制**: 限制每次处理的推文数量
4. **Token 控制**: max_tokens 参数严格控制

---

## 8. 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2025-11-08 | 1.0 | 初始版本，完整记录所有 AI 提示词 |

---

## 9. 相关文件

- `src/api/chatgpt_client.py` - ChatGPT 客户端实现
- `src/utils/smart_classifier.py` - 智能分类器
- `src/utils/tweet_enricher.py` - 推文增强器
- `config/config.json` - 配置文件
