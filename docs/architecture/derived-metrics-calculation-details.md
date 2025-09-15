# Derived Metrics Calculation Details

## Sentiment Index计算引擎

**算法设计**:

1. **Tweet级别Sentiment Index**:
```python
def calculate_tweet_sentiment(tweet_content: str) -> float:
    # LLM推理获取情感分类和置信度
    sentiment_result = llm_inference_client.analyze_sentiment(
        text=tweet_content,
        domain="cryptocurrency",
        output_format="score_and_confidence"
    )
    
    # 转换为0-100分数
    if sentiment_result.label == "positive":
        base_score = 50 + (sentiment_result.confidence * 50)
    elif sentiment_result.label == "negative": 
        base_score = 50 - (sentiment_result.confidence * 50)
    else:  # neutral
        base_score = 50
    
    # 重要性权重调整
    if tweet.is_important:
        importance_weight = 1.2
    else:
        importance_weight = 1.0
        
    return min(100, max(0, base_score * importance_weight))
```

2. **KOL级别Sentiment Index**:
```python  
def calculate_kol_sentiment(kol_id: str, timeframe: str = "24h") -> float:
    # 获取KOL在时间窗口内的所有推文
    tweets = get_kol_tweets(kol_id, timeframe)
    
    # 加权平均计算，recent tweets权重更高
    total_weight = 0
    weighted_sentiment = 0
    
    for tweet in tweets:
        # 时间衰减权重 (越新权重越大)
        time_weight = calculate_time_decay_weight(tweet.created_at)
        # 互动量权重
        engagement_weight = calculate_engagement_weight(tweet.engagement_metrics)
        
        final_weight = time_weight * engagement_weight
        weighted_sentiment += tweet.sentiment_index * final_weight
        total_weight += final_weight
    
    return weighted_sentiment / total_weight if total_weight > 0 else 50
```

3. **Project级别Sentiment Index**:
```python
def calculate_project_sentiment(project_id: str, timeframe: str = "24h") -> float:
    # 获取项目相关的所有推文和KOL观点
    project_tweets = get_project_tweets(project_id, timeframe)
    kol_opinions = get_kol_opinions_on_project(project_id, timeframe)
    
    # KOL观点权重 (70%) + 普通推文权重 (30%)
    kol_sentiment = 0
    kol_weight = 0
    
    for opinion in kol_opinions:
        influence_weight = opinion.kol.influence_score / 100
        kol_sentiment += opinion.sentiment_index * influence_weight
        kol_weight += influence_weight
    
    avg_kol_sentiment = kol_sentiment / kol_weight if kol_weight > 0 else 50
    
    # 普通推文情感
    general_sentiment = sum(t.sentiment_index for t in project_tweets) / len(project_tweets)
    
    return avg_kol_sentiment * 0.7 + general_sentiment * 0.3
```

## Popularity指标计算引擎

**多维度Popularity计算**:

```python
def calculate_topic_popularity(topic_id: str) -> int:
    # 获取话题相关数据
    topic_tweets = get_topic_tweets(topic_id, "24h")
    topic_kols = get_topic_kols(topic_id, "24h")
    
    # 1. 推文数量基础分 (40%)
    tweet_count_score = min(1000, len(topic_tweets))
    
    # 2. 互动质量分 (30%)  
    total_engagement = sum(
        t.like_count + t.retweet_count * 2 + t.reply_count * 1.5 
        for t in topic_tweets
    )
    engagement_score = min(1000, total_engagement / 10)
    
    # 3. KOL参与度分 (20%)
    kol_participation = 0
    for kol in topic_kols:
        kol_participation += kol.influence_score * len(kol.topic_tweets)
    kol_score = min(1000, kol_participation / 100)
    
    # 4. 传播速度加成 (10%)
    propagation_bonus = calculate_propagation_bonus(topic_id)
    
    popularity = int(
        tweet_count_score * 0.4 + 
        engagement_score * 0.3 + 
        kol_score * 0.2 + 
        propagation_bonus * 0.1
    )
    
    return popularity

def calculate_propagation_bonus(topic_id: str) -> float:
    # 获取传播速度数据
    speed_5m = get_propagation_speed(topic_id, "5m")
    speed_1h = get_propagation_speed(topic_id, "1h") 
    
    # 病毒式传播检测
    if speed_5m > 50 and speed_1h > 100:
        return 500  # 病毒式传播加成
    elif speed_5m > 20:
        return 200  # 快速传播加成
    else:
        return 0
```

## Summary AI总结生成引擎

**分层总结策略**:

```python
def generate_kol_summary(kol_id: str, timeframe: str = "24h") -> str:
    # 获取KOL最新观点推文
    recent_tweets = get_kol_important_tweets(kol_id, timeframe, limit=10)
    
    # 构建专用prompt
    prompt = f"""
    作为crypto市场分析师，请总结以下KOL在过去{timeframe}的主要观点：
    
    KOL类型: {kol.type}
    影响力评分: {kol.influence_score}
    
    相关推文:
    {format_tweets_for_analysis(recent_tweets)}
    
    请提供:
    1. 核心观点摘要 (50字以内)
    2. 市场态度倾向 (bullish/bearish/neutral)
    3. 重点关注的项目或叙事
    
    输出格式: 简洁的中文总结，突出关键信息。
    """
    
    summary = llm_inference_client.generate_text(
        prompt=prompt,
        max_tokens=200,
        temperature=0.3
    )
    
    return summary.strip()

def generate_project_summary(project_id: str, timeframe: str = "24h") -> str:
    # 获取项目相关讨论
    project_tweets = get_project_tweets(project_id, timeframe)
    kol_opinions = get_project_kol_opinions(project_id, timeframe)
    
    # 统计关键数据
    sentiment_stats = calculate_sentiment_distribution(project_tweets)
    top_topics = get_project_top_topics(project_id, timeframe)
    
    prompt = f"""
    请总结项目 {project.name} ({project.symbol}) 在过去{timeframe}的社区讨论情况：
    
    讨论数据:
    - 相关推文数量: {len(project_tweets)}
    - 情感分布: {sentiment_stats}
    - 热门话题: {top_topics}
    - KOL观点数: {len(kol_opinions)}
    
    重要讨论内容:
    {format_discussions_for_analysis(project_tweets[:5])}
    
    请提供简洁的项目社区情绪和讨论焦点总结。
    """
    
    summary = llm_inference_client.generate_text(
        prompt=prompt,
        max_tokens=300,
        temperature=0.2
    )
    
    return summary.strip()
```

## KOL影响力评分算法

**综合影响力计算**:

```python
def calculate_influence_score(kol_id: str) -> float:
    kol = get_kol_by_id(kol_id)
    user = get_user_by_id(kol.user_id)
    
    # 1. 基础影响力 (30%) - 基于粉丝数和账号质量
    follower_score = min(30, math.log10(user.followers_count + 1) * 3)
    
    # 2. 内容质量 (25%) - 基于原创性和重要性
    recent_tweets = get_user_tweets(user.user_id, "30d")
    important_tweets = [t for t in recent_tweets if t.is_important]
    quality_score = (len(important_tweets) / len(recent_tweets)) * 25
    
    # 3. 互动质量 (20%) - 基于真实互动vs bot互动
    engagement_quality = calculate_engagement_quality(recent_tweets)
    interaction_score = engagement_quality * 20
    
    # 4. 预测准确性 (15%) - 基于喊单历史表现
    accuracy_score = 0
    if kol.call_accuracy_24h:
        accuracy_score = kol.call_accuracy_24h * 0.15
    
    # 5. 网络影响力 (10%) - 基于被其他KOL引用/转发的频率
    network_influence = calculate_network_influence(kol_id)
    network_score = network_influence * 10
    
    total_score = (follower_score + quality_score + interaction_score + 
                  accuracy_score + network_score)
    
    return min(100, max(0, total_score))

def calculate_engagement_quality(tweets: List[Tweet]) -> float:
    # 计算互动质量，检测bot互动模式
    total_quality = 0
    
    for tweet in tweets:
        # 互动比例分析 - 正常用户互动模式
        total_engagement = (tweet.like_count + tweet.retweet_count + 
                          tweet.reply_count)
        
        if total_engagement == 0:
            quality = 0
        else:
            # 正常比例: likes > retweets > replies
            like_ratio = tweet.like_count / total_engagement
            retweet_ratio = tweet.retweet_count / total_engagement
            
            # 异常模式检测 (可能的bot行为)
            if retweet_ratio > 0.8:  # 异常高转发比例
                quality = 0.3
            elif like_ratio < 0.3:  # 异常低点赞比例
                quality = 0.5
            else:
                quality = 1.0
                
        total_quality += quality
    
    return total_quality / len(tweets) if tweets else 0
```

## 传播速度计算引擎

**实时传播分析**:

```python
def calculate_propagation_speed(topic_id: str, timeframe: str) -> float:
    # 获取时间窗口
    if timeframe == "5m":
        window_minutes = 5
    elif timeframe == "1h":
        window_minutes = 60
    elif timeframe == "4h":
        window_minutes = 240
    else:
        raise ValueError("Invalid timeframe")
    
    # 获取话题在时间窗口内的推文
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=window_minutes)
    
    topic_tweets = get_topic_tweets_in_range(topic_id, start_time, end_time)
    
    if len(topic_tweets) < 2:
        return 0.0
    
    # 按时间排序
    topic_tweets.sort(key=lambda x: x.created_at)
    
    # 计算传播速度指标
    unique_users = set(t.user_id for t in topic_tweets)
    total_engagement = sum(
        t.like_count + t.retweet_count + t.reply_count 
        for t in topic_tweets
    )
    
    # 传播速度 = (参与用户数 * 总互动数) / 时间窗口(分钟)
    base_speed = (len(unique_users) * total_engagement) / window_minutes
    
    # KOL加速器 - KOL参与会显著提升传播速度
    kol_tweets = [t for t in topic_tweets if is_kol_user(t.user_id)]
    kol_multiplier = 1 + (len(kol_tweets) * 0.5)  # 每个KOL参与+50%
    
    # 病毒式传播检测
    time_intervals = []
    for i in range(1, len(topic_tweets)):
        interval = (topic_tweets[i].created_at - topic_tweets[i-1].created_at).seconds / 60
        time_intervals.append(interval)
    
    avg_interval = sum(time_intervals) / len(time_intervals)
    if avg_interval < 1:  # 平均间隔小于1分钟
        viral_multiplier = 2.0
    elif avg_interval < 5:
        viral_multiplier = 1.5
    else:
        viral_multiplier = 1.0
    
    final_speed = base_speed * kol_multiplier * viral_multiplier
    
    return round(final_speed, 2)
```
