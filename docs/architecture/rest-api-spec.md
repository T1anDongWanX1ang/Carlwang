# REST API Spec

```yaml
openapi: 3.0.0
info:
  title: Crypto Twitter Data Pipeline API
  version: 1.0.0
  description: RESTful API for crypto social media data and analytics

servers:
  - url: https://api.cryptotwitterdata.com/v1
    description: Production API server

components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
  
  schemas:
    Tweet:
      type: object
      properties:
        tweet_id:
          type: string
        content:
          type: string
        created_at:
          type: string
          format: date-time
        user_id:
          type: string
        sentiment_index:
          type: number
          minimum: 0
          maximum: 100
        is_important:
          type: boolean
        engagement_metrics:
          type: object
          properties:
            likes:
              type: integer
            retweets:
              type: integer
            replies:
              type: integer
            quotes:
              type: integer
    
    KOL:
      type: object
      properties:
        kol_id:
          type: string
        user_id:
          type: string
        type:
          type: string
          enum: [founder, influencer, investor]
        influence_score:
          type: number
          minimum: 0
          maximum: 100
        call_accuracy_24h:
          type: number
          minimum: 0
          maximum: 100
        sentiment:
          type: string
          enum: [bullish, bearish, neutral]

security:
  - ApiKeyAuth: []

paths:
  /tweets:
    get:
      summary: Get tweets with filtering options
      parameters:
        - name: user_id
          in: query
          schema:
            type: string
        - name: sentiment
          in: query
          schema:
            type: string
            enum: [positive, negative, neutral]
        - name: start_time
          in: query
          schema:
            type: string
            format: date-time
        - name: limit
          in: query
          schema:
            type: integer
            default: 100
            maximum: 1000
      responses:
        '200':
          description: List of tweets
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Tweet'
                  pagination:
                    type: object
                    properties:
                      page:
                        type: integer
                      total:
                        type: integer
                      has_more:
                        type: boolean
  
  /kols:
    get:
      summary: Get KOL rankings and information
      parameters:
        - name: type
          in: query
          schema:
            type: string
            enum: [founder, influencer, investor]
        - name: sort_by
          in: query
          schema:
            type: string
            enum: [influence_score, call_accuracy_24h]
            default: influence_score
        - name: limit
          in: query
          schema:
            type: integer
            default: 50
            maximum: 500
      responses:
        '200':
          description: List of KOLs
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/KOL'
  
  /metrics/sentiment_index:
    get:
      summary: Get sentiment index for different entities
      parameters:
        - name: entity_type
          in: query
          required: true
          schema:
            type: string
            enum: [tweet, kol, project, narrative, marco]
        - name: entity_id
          in: query
          schema:
            type: string
        - name: timerange
          in: query
          schema:
            type: string
            enum: [1h, 24h, 7d, 30d]
            default: 24h
      responses:
        '200':
          description: Sentiment index data
          content:
            application/json:
              schema:
                type: object
                properties:
                  entity_type:
                    type: string
                  entity_id:
                    type: string
                  current_sentiment:
                    type: number
                  historical_data:
                    type: array
                    items:
                      type: object
                      properties:
                        timestamp:
                          type: string
                          format: date-time
                        value:
                          type: number
```
