# Ultra-Light Edge Observability Stack

[![Memory](https://img.shields.io/badge/Memory-141MB%20%2F%20300MB-brightgreen)](https://github.com/yourusername/edge-observability-stack)
[![CPU](https://img.shields.io/badge/CPU-0.4%25%20avg-brightgreen)](https://github.com/yourusername/edge-observability-stack)
[![Scrape Success](https://img.shields.io/badge/Scrape%20Success-99%25%2B-brightgreen)](https://github.com/yourusername/edge-observability-stack)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://docs.docker.com/compose/)

A production-grade monitoring stack designed for resource-constrained edge devices. Most observability setups assume abundant memory and CPU — this one doesn't. The entire stack (metrics collection, storage, and dashboarding) runs under **150MB RAM** on a 2-core device, with 99%+ scrape reliability.

---

## The Problem

Running Prometheus + Grafana on edge hardware is non-trivial. Out of the box, a naive deployment will:
- Blow through a 300MB memory budget
- Hit scrape timeouts from CPU-heavy services
- Fail silently due to content-type mismatches between Flask and Prometheus

This project documents the exact issues encountered and the fixes applied to get a stable, lean observability stack running in a constrained environment.

---

## Performance

| Metric | Before | After |
|--------|--------|-------|
| Total Memory | 210–230 MB | **141 MB** (53% under 300MB budget) |
| CPU Usage | 0.6–0.8% (with spikes) | **0.4% avg** (smooth) |
| Scrape Success Rate | 60–70% | **99%+** |
| Prometheus Target Status | DOWN (red) | **UP (green)** |

---

## Hardware Target

```
2-core CPU @ 2 GHz
500 MB usable RAM
Memory Budget: 300 MB maximum
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 Edge Device                      │
│  (2-core CPU, 500MB RAM)                        │
│                                                  │
│  ┌──────────────────┐         ┌──────────────┐ │
│  │  Sensor Service  │────────▶│  Prometheus  │ │
│  │   (Flask App)    │ metrics │  (Scraper)   │ │
│  │   64MB limit     │  :8000  │  128MB limit │ │
│  └──────────────────┘         └──────┬───────┘ │
│                                       │         │
│                                       ▼         │
│                               ┌──────────────┐ │
│                               │   Grafana    │ │
│                               │ (Visualize)  │ │
│                               │  96MB limit  │ │
│                               └──────────────┘ │
└─────────────────────────────────────────────────┘
                                       │
                                       ▼
                              User Dashboard (Browser)
```

---

## Quick Start

**Prerequisites:** Docker Desktop or Docker Engine, Docker Compose, 500MB RAM available

```bash
git clone https://github.com/yourusername/edge-observability-stack
cd edge-observability-stack
docker compose up -d

# Verify containers are running
docker ps

# Check memory usage (should be ~141MB total)
docker stats --no-stream
```

### Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |
| Sensor Service | http://localhost:8000/sensor | — |
| Metrics Endpoint | http://localhost:8000/metrics | — |

---

## Challenges & Solutions

Getting this stack stable on constrained hardware required diagnosing and fixing four distinct issues. Here's what broke and how it was fixed.

---

### 1. Content-Type Mismatch → Scrape Failures

**Symptom:** Prometheus showing "Error scraping target" on every scrape cycle.

```
received unsupported Content-Type 'text/html; charset=utf-8'
and no fallback_scrape_protocol specified for target
```

**Root cause:** Flask's default response wraps bytes in `text/html`, which Prometheus rejects outright.

```python
# BEFORE
return generate_latest()  # Flask silently sets text/html
```

**Fix:** Explicitly return a `Response` object with the correct Prometheus mimetype.

```python
# AFTER
return Response(
    generate_latest(),
    mimetype='text/plain; version=0.0.4; charset=utf-8'
)
```

**Result:** Scrape success rate jumped from 60–70% → 99%+. Prometheus target went from DOWN (red) to UP (green).

**Before — Prometheus showing scrape errors:**

<img width="1920" alt="Prometheus scrape error" src="https://github.com/user-attachments/assets/2da9d048-13b1-4f95-aca6-8d3359e3a9c2" />
<img width="1920" alt="Prometheus target down" src="https://github.com/user-attachments/assets/479cf5ef-5777-44f8-8f7f-86bc54568be0" />

**After — Target UP, no errors:**

<img width="1920" alt="Prometheus target up" src="https://github.com/user-attachments/assets/eb7d2895-0254-4b2d-aba5-6bc83e3647cd" />

---

### 2. CPU Busy-Wait Loop → Scrape Timeouts

**Symptom:** Scrapes timing out, CPU usage elevated and spikey, delayed metrics delivery.

**Root cause:** A 2-million-iteration loop ran on every single scrape request.

```python
# BEFORE — runs on every /metrics request
for _ in range(2000000):
    pass  # serves no purpose, burns CPU
```

**Fix:** Removed entirely — it had no functional purpose.

**Result:** CPU dropped from ~4% to 0.4% (90% reduction). Scrape timeouts eliminated.

---

### 3. 5MB Memory Blob → Memory Spikes

**Symptom:** Regular memory spikes visible in Grafana, up to 15MB per scrape.

**Root cause:** A 5MB static string was allocated at module load, then randomly multiplied on each request.

```python
# BEFORE
data_blob = "X" * 5_000_000          # 5MB baseline
temp_data = data_blob * random.randint(1, 3)  # up to 15MB per request!
```

**Fix:** Replaced with a realistic 1KB payload.

```python
# AFTER
data_blob = "X" * 1_000  # 1KB — reflects realistic sensor data
```

**Result:** 99.98% memory reduction. Spikes disappeared entirely.

---

### 4. Missing Import → /sensor Route Crashes

**Symptom:** Every request to `/sensor` crashed with a `NameError`.

**Root cause:** `jsonify()` was used in the route handler but never imported.

```python
# BEFORE — missing jsonify
from flask import Flask, Response

# AFTER — fixed
from flask import Flask, Response, jsonify
```

**Result:** `/sensor` route works correctly on every request.

---

## Key Optimizations

### Sensor Service

| Issue | Before | After | Impact |
|-------|--------|-------|--------|
| Data blob | 5 MB static | 1 KB realistic | 99.98% reduction |
| CPU loop | 2M iterations/scrape | Removed | Eliminated timeouts |
| Memory | ~80 MB | ~40–50 MB | 37% reduction |
| Content-Type | text/html | Prometheus format | 100% scrape success |

### Prometheus

```yaml
prometheus:
  command:
    - "--storage.tsdb.retention.time=12h"  # down from 48h — saves ~30% memory
    - "--config.file=/etc/prometheus/prometheus.yml"
    - "--web.enable-lifecycle"
  mem_limit: 128m
```

Scrape interval tuned from 5s → 15s — 66% fewer requests with no meaningful data loss for this use case.

### Container Images

Switching from `python:3.10` (~900MB) to `python:3.10-slim` (~150MB) cut the image size by 83%.

---

## Custom Metrics

A custom counter tracks failed sensor events by failure category:

```python
FAILED_EVENTS = Counter(
    "sensor_failed_events_total",
    "Total failed sensor events",
    ["reason"]  # Labels: cpu_spike, route_error
)
```

| Label | Triggered when |
|-------|---------------|
| `cpu_spike` | CPU_SPIKE gauge flips to 1 (simulated degraded state) |
| `route_error` | `/sensor` route throws an exception |

**Example Grafana query:**
```promql
rate(sensor_failed_events_total{reason="cpu_spike"}[1m])
```

Use `rate()` here rather than raw counter values — it shows event frequency over time and makes anomaly detection practical.

---

## Memory Budget

```
NAME                    MEM USAGE / LIMIT
sensor-service-1        ~45MB  / 64MB
prometheus-1            ~55MB  / 128MB
grafana-1               ~55MB  / 96MB
────────────────────────────────────────
TOTAL                   ~141MB / 288MB   ✓ 53% under budget
```

---

## Dashboard: Before vs After

**Before** — CPU 0.6–0.8%, memory spikes at regular intervals, total usage 210–230MB:

<img width="1920" alt="Before optimization - CPU" src="https://github.com/user-attachments/assets/d7e6d870-de84-4d06-bbf3-136db66ab0e4" />
<img width="1920" alt="Before optimization - Memory" src="https://github.com/user-attachments/assets/44ff5d78-369a-41fd-a3e1-0fe7761c1a40" />

**After** — CPU drops to 0.2%, memory stable, spikes gone:

<img width="1920" alt="After optimization - CPU" src="https://github.com/user-attachments/assets/73951169-10a9-4233-a145-17c59c921e12" />
<img width="1920" alt="After optimization - Memory" src="https://github.com/user-attachments/assets/af3a2c8a-f9de-422c-9727-948cae99e461" />

---

## Testing

```bash
# Start services
docker compose up -d

# All containers should be in "Up" state
docker ps

# Total memory should be ~141MB
docker stats --no-stream

# Test sensor endpoint
curl http://localhost:8000/sensor

# Confirm custom metric is present
curl http://localhost:8000/metrics | grep sensor_failed

# Confirm Prometheus target is UP (green)
open http://localhost:9090/targets
```

**Expected results:**
- All containers in "Up" state
- Total memory ~141MB (under 300MB budget)
- Prometheus target status: UP (green)
- Grafana dashboards display data with no gaps
- No content-type errors in Prometheus logs
- CPU stable around 0.4%

---

## Stack

- **[Prometheus](https://prometheus.io/)** — metrics scraping and storage
- **[Grafana](https://grafana.com/)** — visualization and dashboards
- **[Flask](https://flask.palletsprojects.com/) + [prometheus_client](https://github.com/prometheus/client_python)** — sensor service and metrics exposition
- **Docker Compose** — container orchestration
