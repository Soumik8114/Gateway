# 🌐 Gateway

A **multi-tenant API Gateway** built with a split-architecture design — a **Django Control Plane** for management and a **FastAPI Data Plane** for high-performance request proxying, authentication, and rate limiting.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Database Setup](#database-setup)
  - [Running the Services](#running-the-services)
  - [Running with Docker (Compose)](#running-with-docker-compose)
- [Usage](#usage)
  - [Register a Tenant](#register-a-tenant)
  - [Register an API](#register-an-api)
  - [Generate an API Key](#generate-an-api-key)
  - [Proxy a Request](#proxy-a-request)
- [Rate Limiting](#rate-limiting)
- [Test Data](#test-data)
- [Running Tests](#running-tests)

---

## Overview

Gateway is a self-hosted API gateway that lets you register upstream APIs behind a unified proxy layer. Each tenant (organization) can register multiple APIs, generate API keys with custom rate-limit plans, and route traffic through the gateway — all with built-in authentication, per-minute and per-month rate limiting, and usage tracking.

---

## Architecture

The project follows a **two-plane architecture**:

```
┌─────────────────────────────────┐      ┌──────────────────────────────────┐
│         CONTROL PLANE           │      │          DATA PLANE              │
│         (Django)                │      │          (FastAPI)               │
│                                 │      │                                  │
│  • Tenant registration/login    │      │  • Reverse proxy to upstream     │
│  • API registration             │      │  • API key authentication        │
│  • API key generation           │      │  • Per-minute rate limiting      │
│  • Billing plan management      │      │  • Per-month rate limiting       │
│  • Dashboard UI                 │      │  • Usage tracking (Redis)        │
│  • Django Admin                 │      │  • Client ID-based routing       │
│                                 │      │                                  │
│  Port: 8000                     │      │  Port: 7000                      │
└────────────┬────────────────────┘      └──────────────┬───────────────────┘
             │                                          │
             └──────────── Shared SQLite DB ────────────┘
                                  +
                            Redis (usage/rate limits)
```

---

## Features

- **Multi-Tenancy** — Each user registers as a tenant with a unique slug. Tenants are fully isolated.
- **API Registration** — Register upstream APIs with a name, slug, and base URL. Access them through the gateway at `/{tenant_slug}/{api_slug}/{path}`.
- **API Key Authentication** — SHA-256 hashed API keys passed via the `X-API-Key` header. Keys are shown only once on creation.
- **Client ID Support** — Optional `X-Client-ID` header for per-client rate limiting within a tenant.
- **Billing Plans** — Create plans with configurable `requests_per_minute` and `requests_per_month` limits.
- **Rate Limiting** — Redis-backed per-minute and per-month rate limiting enforced at the data plane.
- **Usage Tracking** — Asynchronous background usage recording to Redis.
- **Dashboard UI** — Dark-themed tenant dashboard to manage APIs, keys, and plans.
- **Graceful Fallback** — Falls back to `fakeredis` if Redis is unavailable, so development works without Redis.

---

## Project Structure

```
Gateway/
├── control_plane/              # Django management app (port 8000)
│   ├── control_plane/          # Django project settings & URLs
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── tenants/                # Tenant registration, login, dashboard
│   │   ├── models.py           # Tenant model
│   │   ├── views.py            # Auth views, dashboard, API/key creation
│   │   ├── forms.py            # RegisterForm, APIForm, APIKeyForm
│   │   ├── urls.py
│   │   ├── tests.py
│   │   ├── templates/          # Dashboard, login, register HTML
│   │   └── static/             # CSS styles
│   ├── apis/                   # API & APIKey models and views
│   │   ├── models.py           # API, APIKey, Client models
│   │   ├── views.py
│   │   └── templates/
│   ├── billing/                # Billing plan model
│   │   └── models.py           # Plan model (RPM & RPM limits)
│   ├── usage/                  # Usage tracking app
│   ├── setup_test_data.py      # Script to seed test data
│   └── manage.py
├── data_plane/                 # FastAPI proxy app (port 7000)
│   └── fastapi_app/
│       ├── main.py             # FastAPI app factory
│       ├── proxy.py            # Reverse proxy + auth + rate limiting
│       ├── dependencies.py     # X-API-Key header extraction
│       ├── tables.py           # SQLAlchemy table definitions
│       ├── config.py           # Database & Redis URL configuration
│       ├── lifespan.py         # App startup/shutdown (DB, Redis, HTTP)
│       ├── state.py            # AppState dataclass
│       └── usage.py            # Async usage recording
├── requirements.txt
└── .gitignore
```

---

## Tech Stack

| Layer         | Technology                          |
|---------------|-------------------------------------|
| Control Plane | Django 5.2, SQLite                  |
| Data Plane    | FastAPI, Uvicorn, httpx, SQLAlchemy |
| Rate Limiting | Redis (with fakeredis fallback)     |
| Database      | SQLite (shared between planes)      |
| Templating    | Django Templates, Tailwind CSS      |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Redis (optional — falls back to `fakeredis` for development)
- Docker + Docker Compose (optional — for the fully dockerized setup)

### Installation

```bash
# Clone the repository
git clone https://github.com/Soumik8114/Gateway.git
cd Gateway

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### Database Setup

```bash
cd control_plane

# Run migrations
python manage.py migrate

# Create a superuser (for Django Admin)
python manage.py createsuperuser
```

### Running the Services

**Terminal 1 — Control Plane (Django):**

```bash
cd control_plane
python manage.py runserver 8000
```

**Terminal 2 — Data Plane (FastAPI):**

```bash
uvicorn data_plane.fastapi_app.main:app --host 0.0.0.0 --port 7000 --reload
```

---

### Running with Docker (Compose)

This repo includes a `docker-compose.yml` that runs the full stack:

- `control_plane` (Django) on `http://localhost:8000`
- `data_plane` (FastAPI) on `http://localhost:7000`
- `redis` on `localhost:6379`

The Control Plane and Data Plane share the same SQLite DB via a named Docker volume mounted at `/data/db.sqlite3`.

**Start (foreground):**

```bash
docker compose up --build
```

**Start (background):**

```bash
docker compose up --build -d
```

**Stop:**

```bash
docker compose down
```

**Stop and remove volumes (clears Redis + SQLite data):**

```bash
docker compose down -v
```

#### Django management commands (Docker)

The `control_plane` container runs migrations automatically on startup, but you’ll still likely want a superuser for Django Admin.

**Create a superuser:**

```bash
docker compose exec control_plane python manage.py createsuperuser
```

**Run migrations manually (optional):**

```bash
docker compose exec control_plane python manage.py migrate
```

**Seed test data:**

```bash
docker compose exec control_plane python setup_test_data.py
```

**Run tests:**

```bash
docker compose exec control_plane python manage.py test
```

---

## Usage

### Register a Tenant

1. Navigate to `http://localhost:8000/register/`
2. Fill in your username, email, tenant name, and password
3. You'll be redirected to the tenant dashboard

### Register an API

From the dashboard, register an upstream API:

| Field              | Example                      |
|--------------------|------------------------------|
| Name               | My API                       |
| Slug               | my-api                       |
| Upstream Base URL  | https://httpbin.org          |
| Auth Header Name   | X-API-Key                    |

### Generate an API Key

From the dashboard, create an API key with a billing plan:

| Field               | Example       |
|---------------------|---------------|
| Plan Name           | Starter Plan  |
| Requests per Minute | 60            |
| Requests per Month  | 10000         |

> ⚠️ **The raw API key is shown only once.** Save it securely.

### Proxy a Request

Send requests through the gateway:

```bash
curl -H "X-API-Key: <your-api-key>" \
     http://localhost:7000/{tenant-slug}/{api-slug}/get
```

**Example:**

```bash
curl -H "X-API-Key: secret_key_12345" \
     http://localhost:7000/test-tenant/test-api/get
```

This proxies the request to `https://httpbin.org/get`.

---

## Rate Limiting

Rate limits are enforced at the data plane using Redis:

| Limit Type     | Scope                     | Response on Exceed            |
|----------------|---------------------------|-------------------------------|
| Per-Minute     | Per API Key or Client ID  | `429 Rate limit exceeded`     |
| Per-Month      | Per API Key or Client ID  | `429 Monthly rate limit exceeded` |

If an `X-Client-ID` header is provided, rate limits are applied per client rather than per API key.

---

## Test Data

Seed the database with sample data for development:

```bash
cd control_plane
python setup_test_data.py
```

This creates:

| Resource   | Value                            |
|------------|----------------------------------|
| User       | `testuser` / `password`          |
| Tenant     | `test-tenant`                    |
| API        | `test-api` → `https://httpbin.org` |
| Plan       | 5 req/min, 100 req/month         |
| API Key    | `secret_key_12345`               |

---

## Running Tests

```bash
cd control_plane
python manage.py test
```

---