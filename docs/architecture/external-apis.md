# External APIs

## Twitter API v2
- **Purpose**: 获取实时推文数据和用户信息
- **Documentation**: https://developer.twitter.com/en/docs/twitter-api
- **Base URL(s)**: https://api.twitter.com/2/
- **Authentication**: Bearer Token (OAuth 2.0)
- **Rate Limits**: 300 requests/15分钟 (Standard), 1000 requests/15分钟 (Enterprise)

**Key Endpoints Used**:
- `GET /2/tweets/search/stream` - 实时推文流采集
- `GET /2/users/by` - 批量用户信息获取
- `GET /2/tweets` - 推文详情查询

**Integration Notes**: 需要Enterprise级别订阅以支持大规模数据采集需求

## CoinGecko API
- **Purpose**: 获取加密货币价格数据，用于KOL喊单效果计算
- **Documentation**: https://www.coingecko.com/en/api/documentation
- **Base URL(s)**: https://api.coingecko.com/api/v3/
- **Authentication**: API Key (Pro Plan)
- **Rate Limits**: 10,000 calls/月 (Free), 500 calls/分钟 (Pro)

**Key Endpoints Used**:
- `GET /simple/price` - 当前价格查询
- `GET /coins/{id}/history` - 历史价格数据
- `GET /coins/list` - 币种列表

**Integration Notes**: 用于计算KOL喊单后的价格变化效果
