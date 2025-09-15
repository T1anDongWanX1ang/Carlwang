# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup configuration (REQUIRED - First time setup)
python setup_config.py

# Test database and API connections
python main.py --mode test

# View help and available commands
python main.py --help
```

### Configuration Setup (Required)

**⚠️ IMPORTANT: You must setup your configuration before running the crawler.**

The repository contains template configuration files for security. You need to setup your actual API keys and database credentials:

```bash
# Interactive configuration setup
python setup_config.py

# Reset configuration to template (if needed)
python setup_config.py reset
```

During setup, you'll be prompted for:
- **TweetScout API Key**: Your API key from TweetScout
- **OpenAI API Key**: Your ChatGPT API key (sk-...)
- **Database Credentials**: Host, database name, username, and password

Alternatively, you can manually edit `config/config.json` and replace:
- `YOUR_TWEETSCOUT_API_KEY` with your actual TweetScout API key
- `YOUR_OPENAI_API_KEY` with your actual OpenAI API key
- `YOUR_DATABASE_HOST`, `YOUR_DATABASE_NAME`, `YOUR_DATABASE_USERNAME`, `YOUR_DATABASE_PASSWORD` with your actual database credentials

### Running the Crawler
```bash
# Single execution (crawl once and exit)
python main.py --mode once

# Continuous scheduling (every 5 minutes by default)
python main.py --mode schedule --interval 5

# Topic analysis (analyze recent tweets for topics)
python main.py --mode topic

# KOL analysis
python main.py --mode kol

# Project analysis  
python main.py --mode project
```

### Service Management (Recommended for Production)
```bash
# Start service with anti-sleep protection
./start_service.sh start

# Check service status
./start_service.sh status

# View service logs
./start_service.sh logs

# Monitor service health and auto-restart capability
./start_service.sh monitor

# Stop service
./start_service.sh stop
```

### Testing and Linting
```bash
# The codebase does not have standardized test/lint commands
# Tests should be run individually if they exist
```

## Architecture Overview

This is a **Twitter data crawler and analysis system** for cryptocurrency social media intelligence. The system crawls Twitter data via TweetScout API, processes it through multiple AI-powered analysis engines, and stores structured data in a MySQL/Doris database.

### Core Components Architecture

**Data Flow Pipeline:**
```
Twitter API → Data Collector → Tweet Enricher → Multi-Engine Analysis → Database Storage
                                      ↓
                              Smart Classifier
                                      ↓
                            Topic/KOL/Project Analysis
```

**Key Modules:**

1. **Main Crawler (`src/crawler.py`)**: Orchestrates the entire data collection and processing pipeline
2. **API Client (`src/api/twitter_api.py`)**: Handles Twitter data fetching via TweetScout API  
3. **Analysis Engines**: 
   - `src/topic_engine.py` - Topic discovery and clustering
   - `src/kol_engine.py` - KOL identification and influence scoring
   - `src/project_engine.py` - Crypto project analysis
4. **AI Processing**:
   - `src/api/chatgpt_client.py` - ChatGPT integration for content analysis
   - `src/utils/smart_classifier.py` - Intelligent content classification
5. **Data Storage**: DAO pattern with `src/database/*.py` modules

### Data Models

**Primary Entities:**
- **Tweet**: Raw Twitter data with engagement metrics and AI-generated sentiment
- **User**: Twitter user profiles with language detection and KOL status
- **Topic**: Clustered conversation topics with popularity metrics
- **KOL**: Key Opinion Leaders with influence scoring and call tracking
- **Project**: Crypto projects with sentiment analysis and community metrics

### Configuration System

Central configuration in `config/config.json`:
- API credentials and endpoints
- Database connections (MySQL/Doris)
- ChatGPT settings and batch processing options
- Field mappings between API responses and database schema

### Anti-Sleep Service Architecture

The system includes sophisticated service management to prevent interruption during system idle/sleep:
- **macOS**: Uses `caffeinate` to prevent system sleep affecting processes
- **Linux**: Uses `nice` for high priority process scheduling
- **Monitoring**: Automatic health checks every 5 minutes with auto-restart capability
- **Cron Integration**: Sets up monitoring tasks automatically

## Critical Implementation Patterns

### Database Operations
- Uses **Doris database** which has specific constraints around primary key updates
- Implements **delete-insert pattern** instead of UPDATE for primary key fields to work around Doris limitations
- All database operations use the DAO (Data Access Object) pattern

### AI Integration Patterns
- **Topic Summary Generation**: Uses structured JSON prompts for consistent output formatting  
- **Language Detection**: Automatic language detection for users based on tweet content and profile descriptions
- **Content Classification**: Multi-stage classification (topic/project/KOL identification)

### Error Handling and Logging
- Comprehensive DEBUG-level logging throughout the pipeline
- Database constraint-aware error handling (especially for Doris upsert operations) 
- Third-party library logging (OpenAI, urllib3) set to WARNING level to reduce noise

### Service Management Considerations
- **Process Persistence**: The system is designed to run continuously with automatic recovery
- **Resource Management**: Includes rate limiting and batch processing for external API calls
- **Data Consistency**: Implements retry mechanisms and transaction-safe operations

## Important Development Notes

### Database Schema Evolution
The system has evolved to handle complex relationships between tweets, users, topics, KOLs, and projects. When modifying schemas:
- Be aware of Doris database limitations around primary key updates
- Use the established DAO pattern for all database access
- Test upsert operations carefully as they use delete-insert patterns

### AI Processing Integration  
- ChatGPT prompts are carefully structured for JSON output consistency
- Language detection uses rule-based algorithms combined with AI fallbacks
- All AI operations include error handling and default fallbacks

### Service Reliability
- The service includes automatic monitoring and restart capabilities
- Log files are structured and rotated automatically
- Process management handles system sleep/idle states gracefully

### Configuration Management
- All sensitive data (API keys, database passwords) should be in `config/config.json`
- The configuration supports environment-specific overrides
- Field mappings between external APIs and internal models are configurable