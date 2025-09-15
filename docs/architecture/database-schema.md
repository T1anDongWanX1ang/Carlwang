# Database Schema

## PostgreSQL Schema (关系数据)

```sql
-- Users表
CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    screen_name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100),
    bio TEXT,
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    statuses_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_verified BOOLEAN DEFAULT FALSE
);

-- Tweets表  
CREATE TABLE tweets (
    tweet_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_quote BOOLEAN DEFAULT FALSE,
    in_reply_to_id VARCHAR(50),
    quote_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    retweet_count INTEGER DEFAULT 0,
    favorite_count INTEGER DEFAULT 0,
    bookmark_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    crypto_sentiment VARCHAR(20),
    is_important BOOLEAN DEFAULT FALSE,
    entity_mentions JSONB,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- KOLs表
CREATE TABLE kols (
    kol_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES users(user_id),
    type VARCHAR(20) NOT NULL CHECK (type IN ('founder', 'influencer', 'investor')),
    influence_score DECIMAL(5,2) DEFAULT 0,
    call_accuracy_1h DECIMAL(5,2),
    call_accuracy_24h DECIMAL(5,2), 
    call_accuracy_3d DECIMAL(5,2),
    call_accuracy_7d DECIMAL(5,2),
    sentiment VARCHAR(20) DEFAULT 'neutral',
    trust_rating INTEGER CHECK (trust_rating >= 1 AND trust_rating <= 10),
    is_kol100 BOOLEAN DEFAULT FALSE,
    tags VARCHAR(200),
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Topics表
CREATE TABLE topics (
    topic_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    popularity INTEGER DEFAULT 0,
    propagation_speed_5m DECIMAL(8,4),
    propagation_speed_1h DECIMAL(8,4),
    propagation_speed_4h DECIMAL(8,4),
    kol_opinion TEXT,
    kol_opinion_direction VARCHAR(20),
    mob_opinion_direction VARCHAR(20),
    summary TEXT
);

-- Projects表
CREATE TABLE projects (
    project_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    symbol VARCHAR(20),
    token_address VARCHAR(100),
    twitter_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    category VARCHAR(50),
    narrative VARCHAR(100),
    sentiment_index DECIMAL(5,2) DEFAULT 0,
    popularity INTEGER DEFAULT 0,
    summary TEXT
);

-- Narratives表  
CREATE TABLE narratives (
    narrative_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sentiment_index DECIMAL(5,2) DEFAULT 0,
    popularity INTEGER DEFAULT 0,
    summary TEXT
);

-- Marco表 (宏观市场数据)
CREATE TABLE marco_snapshots (
    id VARCHAR(50) PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    sentiment_index DECIMAL(5,2) DEFAULT 0,
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 关系表
CREATE TABLE tweet_topics (
    tweet_id VARCHAR(50) REFERENCES tweets(tweet_id),
    topic_id VARCHAR(50) REFERENCES topics(topic_id),
    PRIMARY KEY (tweet_id, topic_id)
);

CREATE TABLE tweet_projects (
    tweet_id VARCHAR(50) REFERENCES tweets(tweet_id), 
    project_id VARCHAR(50) REFERENCES projects(project_id),
    PRIMARY KEY (tweet_id, project_id)
);

CREATE TABLE kol_calls (
    call_id VARCHAR(50) PRIMARY KEY,
    kol_id VARCHAR(50) REFERENCES kols(kol_id),
    tweet_id VARCHAR(50) REFERENCES tweets(tweet_id),
    project_id VARCHAR(50) REFERENCES projects(project_id),
    prediction_type VARCHAR(20), -- 'bullish', 'bearish'
    call_price DECIMAL(20,8),
    call_time TIMESTAMP WITH TIME ZONE,
    price_1h DECIMAL(20,8),
    price_24h DECIMAL(20,8),
    price_3d DECIMAL(20,8), 
    price_7d DECIMAL(20,8),
    accuracy_1h DECIMAL(5,2),
    accuracy_24h DECIMAL(5,2),
    accuracy_3d DECIMAL(5,2),
    accuracy_7d DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引优化
CREATE INDEX idx_tweets_created_at ON tweets(created_at);
CREATE INDEX idx_tweets_user_id ON tweets(user_id);
CREATE INDEX idx_tweets_sentiment ON tweets(crypto_sentiment);
CREATE INDEX idx_kols_influence_score ON kols(influence_score DESC);
CREATE INDEX idx_kols_type ON kols(type);
CREATE INDEX idx_projects_narrative ON projects(narrative);
CREATE INDEX idx_marco_timestamp ON marco_snapshots(timestamp);
```

## InfluxDB Schema (时序指标数据)

```
# Measurement: sentiment_index
# 存储各实体的情感指数时序数据
sentiment_index,entity_type=tweet,entity_id=123456789 value=75.5 1640995200000000000
sentiment_index,entity_type=kol,entity_id=kol_001 value=82.3 1640995200000000000
sentiment_index,entity_type=project,entity_id=project_btc value=68.7 1640995200000000000

# Measurement: popularity
# 存储各实体的热度指标时序数据  
popularity,entity_type=topic,entity_id=topic_defi value=1250 1640995200000000000
popularity,entity_type=project,entity_id=project_eth value=2100 1640995200000000000

# Measurement: propagation_speed
# 存储话题传播速度数据
propagation_speed,topic_id=topic_001,timeframe=5m value=15.7 1640995200000000000
propagation_speed,topic_id=topic_001,timeframe=1h value=45.2 1640995200000000000

# Measurement: kol_metrics
# 存储KOL相关指标时序数据
kol_metrics,kol_id=kol_001,metric=influence_score value=85.4 1640995200000000000
kol_metrics,kol_id=kol_001,metric=call_accuracy_24h value=72.8 1640995200000000000

# Measurement: system_metrics
# 存储系统性能指标
system_metrics,service=api_gateway,metric=requests_per_second value=8540 1640995200000000000
system_metrics,service=llm_engine,metric=inference_latency value=1.8 1640995200000000000
```
