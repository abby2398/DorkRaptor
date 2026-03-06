# 🦖 DorkRaptor — OSINT & Google Dork Intelligence Platform

> Automated Google dorking, OSINT discovery, and threat intelligence for security professionals

![DorkRaptor](https://img.shields.io/badge/DorkRaptor-v1.0.0-00ff9d?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-3d8bff?style=for-the-badge)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge)

---
<img width="1621" height="831" alt="image" src="https://github.com/user-attachments/assets/59114104-56c8-491e-bba5-3b6260b971c5" />

## Overview

DorkRaptor automates the entire Google dorking and OSINT reconnaissance workflow. Enter a domain, and the platform automatically runs 300+ dorks across multiple search engines, scans GitHub for leaks, checks cloud storage exposure, and uses AI to classify findings by severity.

**Built for:**
- Penetration testers
- Bug bounty hunters
- Vulnerability assessment teams
- Security operations centers
- Security researchers

---

## Features

### 🔍 Google Dork Engine
- **300+ categorized dorks** across 12 threat categories
- Sensitive files, admin panels, directory listings, backup files
- Configuration files, credentials, database dumps, API endpoints
- Runs across **Bing + DuckDuckGo** (Google optional)
- Rotating user agents, randomized delays, retry logic

### 🐙 GitHub Leak Detection
- Scans GitHub for domain-related credential leaks
- Detects API keys, passwords, tokens, private keys
- Supports GitHub API (with token) or web-based search

### ☁️ Cloud Exposure Scanner
- Checks AWS S3 buckets, Azure Blob, Google Cloud Storage
- Tests 20+ common bucket naming patterns
- Flags public buckets as CRITICAL

### 🤖 AI Analysis
- OpenAI-powered risk classification (falls back to rule-based)
- Natural language explanations for every finding
- Severity: CRITICAL / HIGH / MEDIUM / LOW / INFO

### 📊 Intelligence Dashboard
- Real-time scan progress
- Severity distribution charts
- Category breakdown
- Filterable findings with expandable detail view
- Full scan history with comparison

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) OpenAI API key
- (Optional) GitHub Personal Access Token

### 1. Clone and configure

```bash
git clone https://github.com/abby2398/DorkRaptor.git
cd dorkraptor
cp .env.example .env
# Edit .env with your API keys (optional)
```

### 2. Start with Docker Compose

```bash
docker-compose up -d
```

### 3. Access the platform

| Service | URL |
|---------|-----|
| Web Dashboard | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Celery Monitor | http://localhost:5555 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     DorkRaptor                          │
├──────────────────┬──────────────────────────────────────┤
│  React Frontend  │  FastAPI Backend                     │
│  (Port 3000)     │  (Port 8000)                         │
│                  │                                       │
│  • Dashboard     │  • REST API                          │
│  • Scan View     │  • Background Tasks (Celery)         │
│  • History       │  • Search Orchestrator               │
│  • Settings      │  • AI Analyzer                       │
└──────────────────┴────────────────────────────────────┬─┘
                                                         │
         ┌──────────────────────────────────────────────┤
         │                                              │
    ┌────▼─────┐   ┌──────────┐   ┌──────────────────┐ │
    │PostgreSQL│   │  Redis   │   │  Celery Workers  │ │
    │  (Data)  │   │ (Queue)  │   │   (Scan Tasks)   │ │
    └──────────┘   └──────────┘   └──────────────────┘ │
                                                         │
    ┌────────────────────────────────────────────────────┘
    │
    ▼  External Services
    ├── Bing Search (dorking)
    ├── DuckDuckGo (dorking)
    ├── GitHub API/Search (leaks)
    ├── Cloud providers (bucket check)
    └── OpenAI API (AI analysis)
```

---

## Dork Categories

| Category | Count | Examples |
|----------|-------|---------|
| Sensitive Files | 45+ | `.env`, `.key`, `wp-config.php` |
| Credentials | 35+ | `password`, `api_key`, `access_token` |
| Admin Panels | 35+ | `inurl:admin`, `inurl:cpanel` |
| Login Pages | 20+ | `inurl:login`, `inurl:signin` |
| Directory Listings | 18+ | `intitle:"index of"` |
| Backup Files | 20+ | `ext:bak`, `ext:zip`, `ext:tar` |
| Database Dumps | 20+ | `ext:sql`, `mysqldump` |
| Config Files | 23+ | `ext:yaml`, `ext:ini` |
| Documents | 20+ | `filetype:pdf`, `filetype:xlsx` |
| API Endpoints | 22+ | `inurl:swagger`, `inurl:graphql` |
| Cloud Storage | 16+ | `s3.amazonaws.com` |
| Development | 18+ | `inurl:staging`, `inurl:dev` |

---

## API Reference

### Scans

```
POST   /api/v1/scans/          Create new scan
GET    /api/v1/scans/          List all scans
GET    /api/v1/scans/{id}      Get scan details
GET    /api/v1/scans/{id}/progress  Real-time progress
DELETE /api/v1/scans/{id}      Delete scan
```

### Results

```
GET /api/v1/results/scan/{id}           Get findings (filterable)
GET /api/v1/results/scan/{id}/stats     Aggregated statistics
GET /api/v1/results/{finding_id}        Single finding detail
```

### Start a scan via API

```bash
curl -X POST http://localhost:8000/api/v1/scans/ \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "openai_key": "sk-...",
    "github_token": "ghp_..."
  }'
```

---

## Development Setup

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Worker
```bash
cd backend
celery -A app.tasks.scan_tasks:celery_app worker --loglevel=info
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Enables AI analysis |
| `GITHUB_TOKEN` | — | Enhances GitHub scanning |
| `SEARCH_DELAY_MIN` | 2.0 | Min delay between requests (sec) |
| `SEARCH_DELAY_MAX` | 5.0 | Max delay between requests (sec) |
| `DEBUG` | false | Enable debug logging |

---

## Ethical Use

DorkRaptor uses only **publicly indexed data sources**. It does not:
- Exploit vulnerabilities
- Access non-public data
- Perform active attacks

**Only use DorkRaptor on domains you own or have explicit written permission to test.**

---

## Roadmap

- [ ] Subdomain intelligence module
- [ ] Shodan/Censys integration
- [ ] Breach database search
- [ ] Dark web monitoring feeds
- [ ] PDF/CSV report export
- [ ] Scheduled recurring scans
- [✔] Multi-user support with auth
- [✔] Webhook notifications

---

## License

MIT — See LICENSE for details
