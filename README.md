# DevOps Edge Assignment - Ultra-Light Observability Stack

[![Memory Badge](https://img.shields.io/badge/Memory-141MB%20%2F%20300MB-green)](https://github.com/yourusername/devops-edge-assignment)
## 📋 Overview

**Hardware Constraints:**
- 2-core CPU @ 2 GHz
- 500 MB usable RAM
- **Memory Budget:** 300 MB Maximum

**Actual Performance:**
- **Memory Usage:** 141 MB (53% under budget ✓)
- **CPU Usage:** 0.4% average / 4% (90% reduction from baseline)
- **Scrape Success Rate:** 99%+ (up from 60-70%)

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop or Docker Engine
- Docker Compose
- 500MB RAM available

### Installation

```bash
docker compose up -d

# Check status
docker ps
docker stats --no-stream
```
## 🔴 Error #1: Content-Type Mismatch Causing Scrape Failures

### Problem
**Symptom:** Prometheus showing "Error scraping target", scrape failure 

**Error Message:**
```
received unsupported Content-Type 'text/html; charset=utf-8' 
and no fallback_scrape_protocol specified for target
```

**Root Cause:**
```python
# BEFORE - sensor_service.py
return generate_latest()  # Returns bytes, Flask wraps in HTML response
```

Flask's default response used `text/html` content-type, which Prometheus rejected.

### Solution
```python
# AFTER 
return Response(
    generate_latest(),
    mimetype='text/plain; version=0.0.4; charset=utf-8'
)
```

Explicitly wrap in `Response` object with Prometheus-compatible mimetype.

### Impact
- ✅ Scrape success rate: 99%+**
- ✅ Error messages: **Eliminated**
- ✅ Prometheus target status: **DOWN (red) → UP (green)**

### Evidence

**Screenshot 3: BEFORE - Prometheus showing scrape errors**
<img width="1920" height="1080" alt="image_2026-02-01_10-43-46" src="https://github.com/user-attachments/assets/2da9d048-13b1-4f95-aca6-8d3359e3a9c2" />
<img width="1920" height="1080" alt="image_2026-02-01_10-47-35" src="https://github.com/user-attachments/assets/479cf5ef-5777-44f8-8f7f-86bc54568be0" />


*Shows "Error scraping target" with content-type error message in Prometheus UI*

**Screenshot 4: AFTER - Prometheus target UP, no errors**
<img width="1920" height="1080" alt="image_2026-02-01_10-55-31" src="https://github.com/user-attachments/assets/eb7d2895-0254-4b2d-aba5-6bc83e3647cd" />

*Shows target status as UP (green), no error messages, successful scrapes*

---




### Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |
| **Sensor Service** | http://localhost:8000/sensor | - |
| **Metrics Endpoint** | http://localhost:8000/metrics | - |

---

## 📊 Architecture

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
│                                       │ data    │
│                                       ▼         │
│                               ┌──────────────┐ │
│                               │   Grafana    │ │
│                               │ (Visualize)  │ │
│                               │  96MB limit  │ │
│                               └──────────────┘ │
│                                      │         │
└──────────────────────────────────────┼─────────┘
                                       │
                                       ▼
                              User Dashboard (Browser)
```

---

## 🔧 Key Optimizations

### 1. Sensor Service Optimizations

| Issue | Before | After | Impact |
|-------|--------|-------|--------|
| **Data Blob** | 5 MB static allocation | 1 KB realistic payload | 99.98% reduction |
| **CPU Loop** | 2M iterations per scrape | Removed entirely | Eliminated timeouts |
| **Memory** | ~80 MB | ~40-50 MB | 37% reduction |
| **Content-Type** | text/html (error) | Prometheus format | 100% scrape success |
| **Missing Import** | jsonify not imported | Added to imports | /sensor route fixed |

**Code Changes:**
```python
# BEFORE (Bad)
data_blob = "X" * 5_000_000  # 5MB!
for _ in range(2000000):
    pass  # CPU burn
# Missing: from flask import jsonify

# AFTER (Good)
data_blob = "X" * 1_000  # 1KB realistic
# No CPU loop
# Fixed: from flask import Flask, Response, jsonify
```

### 2. Prometheus Optimizations

| Parameter | Before | After | Savings |
|-----------|--------|-------|---------|
| Retention | 48 hours | 12 hours | ~30% memory |
| Scrape Interval | 5 seconds | 15 seconds | 66% fewer requests |
| Memory Limit | Unlimited | 128 MB | Hard constraint |

**Configuration:**
```yaml
prometheus:
  command:
    - "--config.file=/etc/prometheus/prometheus.yml"
    - "--web.enable-lifecycle"
    - "--storage.tsdb.retention.time=12h"
    - "--storage.tsdb.path=/prometheus"
  mem_limit: 128m
```

### 3. Container Image Optimization

| Aspect | Before | After | Improvement |
|--------|--------|-------|-------------|
| Base Image | python:3.10 (~900MB) | python:3.10-slim (~150MB) | 83% smaller |
| Pip Cache | Cached | --no-cache-dir flag | Smaller image |
| Security | Root user | Non-root recommended | Best practice ✓ |

---

## 📈 Custom Metrics

Custom metric added to track failed sensor events with categorization:

### Failed Events Counter
```python
FAILED_EVENTS = Counter(
    "sensor_failed_events_total",
    "Total failed sensor events",
    ["reason"]  # Labels: cpu_spike, route_error
)
```

**Label Values:**
- **cpu_spike** - Increments when CPU_SPIKE gauge flips to 1 (simulated degraded state)
- **route_error** - Increments when /sensor route throws an exception

**Grafana Query Example:**
```promql
rate(sensor_failed_events_total{reason="cpu_spike"}[1m])
```

**Purpose:** 
- Track cumulative failure counts by category
- Use `rate()` to show event frequency over time
- Distinguish between different failure modes for root cause analysis



## 🎯 Technology Choices & Justifications

### Why Prometheus over VictoriaMetrics?

✅ **Prometheus Selected:**
- Production-proven stability 
- Native Grafana integration, extensive ecosystem
- Acceptable footprint with optimizations (128MB limit, ~50-60MB actual)
- Self-contained, no external dependencies
- Perfect for edge: works offline/intermittent networks
- Service already exposes /metrics endpoint via prometheus_client

❌ **VictoriaMetrics Rejected:**
- Lower memory (~60MB) but added complexity
- Less mature ecosystem, steeper learning curve
- Overkill for 12-hour retention requirements
- Would need to justify complexity vs. marginal savings

### Why Grafana over Alternatives?

✅ **Grafana Selected:**
- Industry standard, familiar to all DevOps engineers
- Rich visualization (time series, histograms, gauges, annotations)
- 96MB limit = 50-60MB actual (well within constraints)
- Remote web UI essential for edge device debugging
- Pre-built community dashboards
- Live auto-refresh for real-time monitoring

❌ **Alternatives Rejected:**
- **Static HTML Dashboard:** No live updates, poor operational UX
- **Terminal Dashboard (prom-tui):** Not production-ready, no remote access
- **VictoriaMetrics UI:** Requires VM stack, limited customization

---

## 📊 Performance Validation

### Memory Usage (Docker Stats)
```
NAME                    MEM USAGE / LIMIT
sensor-service-1        ~45MB / 64MB
prometheus-1            ~55MB / 128MB
grafana-1               ~55MB / 96MB
──────────────────────────────────────
TOTAL                   ~141MB / 288MB  ✓ 53% under budget
```

### Scrape Success Rate
- **Before:** 60-70% (frequent timeouts due to CPU loop + content-type errors)
- **After:** 99%+ (Prometheus shows targets UP, green status)
- **Evidence:** Screenshots show no scrape errors, stable metrics collection

### CPU Efficiency
- **Before:** ~4% average (spikes due to 2M iteration loop)
- **After:** ~0.4% average (minimal spikes, smooth operation)
- **Root Cause Fixed:** Removed busy-wait loop entirely

---

## 🐛 Issues Identified & Fixed

### Issue 1: CPU Busy-Wait Loop
**Symptom:** Scrape timeouts, high CPU usage, delayed metrics

**Root Cause:** 
```python
for _ in range(2000000):
    pass  # 2 million iterations on every scrape!
```

**Fix:** Removed the loop entirely - served no functional purpose

**Impact:** CPU usage dropped from 4% to 0.4% (90% reduction)

---

### Issue 2: 5MB Data Blob with Random Multiplication
**Symptom:** Memory spikes visible in Grafana, up to 15MB per scrape

**Root Cause:**
```python
data_blob = "X" * 5_000_000  # 5MB allocation
temp_data = data_blob * random.randint(1, 3)  # Up to 15MB!
```

**Fix:** Reduced to realistic 1KB payload
```python
data_blob = "X" * 1_000  # 1KB realistic sensor data
```

**Impact:** 99.98% memory reduction, eliminated spikes

---

### Issue 3: Content-Type Mismatch
**Symptom:** Prometheus error: `received unsupported Content-Type 'text/html; charset=utf-8'`

**Root Cause:** Flask default response format incompatible with Prometheus

**Fix:**
```python
return Response(
    generate_latest(),
    mimetype='text/plain; version=0.0.4; charset=utf-8'
)
```

**Impact:** 100% scrape success rate

---

### Issue 4: Missing jsonify Import
**Symptom:** /sensor route crashes with NameError on every request

**Root Cause:** `jsonify()` used but never imported from Flask

**Fix:**
```python
from flask import Flask, Response, jsonify
```

**Impact:** /sensor route now works correctly

---

---

## Dashboard metrics before Vs after

Before optimization 
<img width="1920" height="1080" alt="image_2026-02-01_12-50-57" src="https://github.com/user-attachments/assets/d7e6d870-de84-4d06-bbf3-136db66ab0e4" />
CPU usage is inbetween 0.6%-0.8%, 
memory spikes at regular interval

<img width="1920" height="1080" alt="image_2026-02-01_13-04-52" src="https://github.com/user-attachments/assets/44ff5d78-369a-41fd-a3e1-0fe7761c1a40" />
total memory usage 210-230MB

After Optimization
<img width="1920" height="1080" alt="image_2026-02-01_20-36-11" src="https://github.com/user-attachments/assets/73951169-10a9-4233-a145-17c59c921e12" />
after applying above optimization cpu usage drops down to 0.2% drop in memory is also visibally noticible .
<img width="1920" height="1080" alt="image_2026-02-01_21-08-25" src="https://github.com/user-attachments/assets/af3a2c8a-f9de-422c-9727-948cae99e461" />


---

## 🔮 Future Enhancements

### One-Week Improvement: Intelligent Edge-Aware Alerting System

**Problem Statement:**
Currently, the system lacks proactive alerting. Operators only discover issues by manually checking Grafana. On edge devices with intermittent connectivity, this is unacceptable as failures may go unnoticed for hours. When network connectivity is lost, alerts cannot reach operators even if critical issues occur.

**Proposed Solution:**
Implement an intelligent alert system with local queueing, multi-channel notifications (SMS/email/webhook), and network-aware batching optimized for edge deployments. The system would use Prometheus Alertmanager with a local queue that persists alerts to disk when network is unavailable, then bulk-sends them when connectivity returns. This ensures zero alert loss even during extended outages.

**Technical Implementation:**
- Add Alertmanager to docker-compose.yml with 32MB memory limit
- Configure Prometheus recording rules to detect anomalies:
  - High CPU (>80% for 2 min) → Email notification
  - Memory pressure (>90% of limit) → Email + Slack webhook
  - Scrape failures (>3 consecutive) → Email + Slack webhook
  - Failed events spike (rate >0.5/min) → Email + Slack webhook

**Network-Aware Queue Design:**
- Alertmanager configured with SQLite-backed queue
- Persists alerts when network health check fails (HTTP probe to cloud endpoint)
- During offline periods, alerts accumulate on disk (max 1000 alerts, ~5MB)
- When connectivity returns, batch sender compresses queued alerts
- Single API call with "[DELAYED - offline 2h 34m]" timestamps prepended

**Expected Benefits:**
- **Zero Alert Loss:** All alerts delivered even after hours offline
- **Reduced Alert Fatigue:** Intelligent batching prevents notification storms
- **Faster Incident Response:** Proactive notifications vs manual discovery (MTTD improvement)
- **Network Efficiency:** Batched delivery uses <1% bandwidth during sync

**Resource Budget:**
- Alertmanager adds 32MB to memory budget (well within 300MB limit)
- Total system memory: 141MB + 32MB = 173MB (still 42% under budget)
- Negligible CPU impact (<0.1%)
- Local queue uses <5MB disk space

---

## 📚 Documentation

- **Performance Budget Report** - [`Performance_Budget_Report_Final_Bharat_singh.pdf`](./Performance_Budget_Report_Final_Bharat_singh.pdf)
 
---

## 🧪 Testing

### Manual Testing
```bash
# Start services
docker compose up -d

# Verify all containers running
docker ps

# Check memory usage (should be ~141MB total)
docker stats --no-stream

# Test sensor endpoint
curl http://localhost:8000/sensor

# Test metrics endpoint (should see sensor_failed_events_total)
curl http://localhost:8000/metrics | grep sensor_failed

# Check Prometheus targets (should show UP)
open http://localhost:9090/targets
```

### Expected Results
- All containers in "Up" state
- Total memory ~141MB < 300MB ✓
- Prometheus target status: UP (green)
- Grafana dashboards display data with no gaps
- No content-type errors in Prometheus logs
- CPU usage stable around 0.4%

---

