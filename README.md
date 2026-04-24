# TN2026 — Tamil Nadu Election Intelligence System

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EC2 t2.micro                             │
│                  (1 vCPU · 1 GB RAM · Docker)                   │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │   CONTAINER 1│    │  CONTAINER 2 │    │   CONTAINER 3    │  │
│  │   Frontend   │    │   Backend    │    │    MongoDB       │  │
│  │  (Nginx+React│◄───│  (FastAPI)   │◄───│   (Lightweight)  │  │
│  │   Port 80)   │    │  Port 8000   │    │   Port 27017     │  │
│  └──────────────┘    └──────┬───────┘    └──────────────────┘  │
│                             │                                   │
│                    ┌────────▼────────┐                          │
│                    │  ML Module      │                          │
│                    │  (scikit-learn) │                          │
│                    │  models/*.pkl   │                          │
│                    └────────┬────────┘                          │
│                             │                                   │
│                    ┌────────▼────────┐                          │
│                    │  Data Pipeline  │                          │
│                    │  Cron: 6h cycle │                          │
│                    │  scrape→clean   │                          │
│                    │  →store→predict │                          │
│                    └─────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘

DATA FLOW:
Scrapers → Raw JSON → Normalizer → MongoDB → ML Training
                                      │
                              FastAPI (cached) → React Dashboard

ELECTION DAY (LIVE MODE):
Mock Results → WebSocket → Live Seat Counter → Dashboard
```

## Folder Structure
```
tn2026/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── api/
│   │   │   ├── trends.py        # /trends endpoint
│   │   │   ├── prediction.py    # /prediction endpoint
│   │   │   ├── constituency.py  # /constituency/{id}
│   │   │   ├── region.py        # /region/{name}
│   │   │   └── live.py          # /live-results
│   │   ├── ml/
│   │   │   ├── predictor.py     # Load & run models
│   │   │   ├── features.py      # Feature engineering
│   │   │   └── ensemble.py      # Weighted ensemble
│   │   ├── pipeline/
│   │   │   ├── scheduler.py     # APScheduler cron
│   │   │   └── pipeline.py      # scrape→clean→store→predict
│   │   └── utils/
│   │       ├── db.py            # MongoDB client
│   │       ├── cache.py         # In-memory cache
│   │       └── logger.py        # Minimal logging
│   ├── models/                  # Saved .pkl files
│   ├── data/
│   │   ├── raw/                 # Scraped JSONs
│   │   ├── processed/           # Cleaned CSVs
│   │   └── seed_data.json       # Bootstrap data
│   ├── train.py                 # Offline training script
│   ├── requirements.txt
│   └── Dockerfile
├── scraper/
│   ├── base_scraper.py
│   ├── ndtv_scraper.py
│   ├── news18_scraper.py
│   ├── abp_scraper.py
│   └── normalizer.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── VoteTrendChart.jsx
│   │   │   ├── SeatProjection.jsx
│   │   │   ├── ConstituencySelector.jsx
│   │   │   ├── RegionBreakdown.jsx
│   │   │   ├── LiveResults.jsx
│   │   │   └── PredictionCard.jsx
│   │   ├── hooks/
│   │   │   └── useElectionData.js
│   │   └── utils/
│   │       └── api.js
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── nginx/
│   └── nginx.conf
├── scripts/
│   ├── deploy.sh
│   └── post_analysis.py
├── docker-compose.yml
└── README.md
```

## Quick Start
```bash
# 1. Clone & enter
git clone <repo> && cd tn2026

# 2. Train models (offline, once)
docker-compose run --rm backend python train.py

# 3. Launch all services
docker-compose up -d

# 4. Access dashboard
http://<EC2-IP>
```
