# Delivery Monitoring — Complete, Fixed, Working Guide

This repository contains a complete, corrected, and working setup to simulate delivery metrics with a Python app, scrape them with Prometheus, visualize them in Grafana, and run the stack with Docker Compose. It also includes a Jenkinsfile to run the stack from Jenkins (Jenkins agent must have Docker).

What I fixed and why (short)
- Fixed typos and filename inconsistencies (prometheus.yml, alert_rules.yml).
- Made Prometheus scrape the delivery app by container name (reliable) and included a docker-compose for stable networking.
- Added a Dockerfile and requirements.txt for the Python app.
- Hardened the Prometheus alert rule for average delivery time to avoid divide-by-zero.
- Made it easy to simulate alerts via an environment variable (PENDING_MODE).
- Provided a Jenkinsfile that checks out the repo and uses docker-compose (agent must have Docker).

Repository layout (how to organize files)
- delivery_monitoring/
  - README.md  (this file)
  - Dockerfile
  - delivery_metrics.py
  - requirements.txt
  - docker-compose.yml
  - prometheus.yml
  - alert_rules.yml
  - Jenkinsfile

Quick start (Docker Compose; recommended)
1. Clone or copy the files into a directory (e.g., `delivery_monitoring`).
2. From that directory, run:
   ```
   docker-compose up --build -d
   ```
3. Wait for services to start (a few seconds). Then open:
   - Delivery metrics: http://localhost:8000/metrics
   - Prometheus UI: http://localhost:9090
   - Grafana UI: http://localhost:3000

Grafana default login:
- Username: `admin`
- Password: `admin`
(You will be prompted to change; you may skip for testing.)

Stop and remove:
```
docker-compose down
```

Files — copy these into your directory as named below.

1) delivery_metrics.py
```python
# delivery_metrics.py
from prometheus_client import start_http_server, Summary, Gauge
import random
import time
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Metrics
total_deliveries = Gauge("total_deliveries", "Total number of deliveries")
pending_deliveries = Gauge("pending_deliveries", "Number of pending deliveries")
on_the_way_deliveries = Gauge("on_the_way_deliveries", "Number of deliveries on the way")
average_delivery_time = Summary("average_delivery_time", "Average delivery time in seconds")

def simulate_delivery(pending_mode="normal"):
    if pending_mode == "high":
        pending = random.randint(50, 100)
    else:
        pending = random.randint(10, 20)

    on_the_way = random.randint(5, 20)
    delivered = random.randint(30, 70)
    avg_time = random.uniform(15, 45)

    total = pending + on_the_way + delivered

    logging.info(f"Total deliveries: {total} | Pending: {pending} | On-the-way: {on_the_way} | AvgTime: {avg_time:.2f}s")

    total_deliveries.set(total)
    pending_deliveries.set(pending)
    on_the_way_deliveries.set(on_the_way)
    average_delivery_time.observe(avg_time)

if __name__ == "__main__":
    port = int(os.getenv("METRICS_PORT", "8000"))
    pending_mode = os.getenv("PENDING_MODE", "normal")  # set to 'high' to simulate alerts
    logging.info(f"Starting metrics HTTP server on port {port} (PENDING_MODE={pending_mode})")
    start_http_server(port, addr="0.0.0.0")
    while True:
        simulate_delivery(pending_mode=pending_mode)
        time.sleep(1)
```

2) requirements.txt
```
prometheus-client>=0.14.1
```

3) Dockerfile
```
FROM python:3.11-slim

WORKDIR /app
COPY delivery_metrics.py requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["python", "delivery_metrics.py"]
```

4) prometheus.yml
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "delivery_service"
    static_configs:
      # When using docker-compose, Prometheus and delivery_metrics are on the same network
      # so we can scrape by container/service name.
      - targets: ["delivery_metrics:8000"]

rule_files:
  - /etc/prometheus/alert_rules.yml
```

5) alert_rules.yml
```yaml
groups:
  - name: delivery_alerts
    rules:
      - alert: HighPendingDeliveries
        expr: pending_deliveries > 10
        for: 15s
        labels:
          severity: warning
        annotations:
          summary: "High pending deliveries"
          description: "Pending deliveries are above 10 for the last 15 seconds."

      - alert: HighAverageDeliveryTime
        # Guard count > 0 before dividing to avoid invalid results
        expr: (average_delivery_time_count > 0) and ((average_delivery_time_sum / average_delivery_time_count) > 30)
        for: 15s
        labels:
          severity: critical
        annotations:
          summary: "High average delivery time"
          description: "Average delivery time is above 30 seconds for the last 15 seconds."
```

6) docker-compose.yml
```yaml
version: "3.8"

services:
  delivery_metrics:
    build: .
    container_name: delivery_metrics
    environment:
      - PENDING_MODE=normal   # change to 'high' to trigger pending alert
    ports:
      - "8000:8000"
    networks:
      - monitoring

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./alert_rules.yml:/etc/prometheus/alert_rules.yml:ro
    command:
      - --config.file=/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    networks:
      - monitoring
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

networks:
  monitoring:
    driver: bridge
```

7) Jenkinsfile (optional — use if you want Jenkins to build & run the stack)
```groovy
pipeline {
  agent any
  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build images & Start stack') {
      steps {
        script {
          // Ensure this Jenkins node has docker and docker-compose installed and the Jenkins user has permission.
          if (fileExists('docker-compose.yml')) {
            sh 'docker-compose -f docker-compose.yml up -d --build'
          } else {
            error 'docker-compose.yml not found. Place it in the repo root.'
          }
        }
      }
    }
  }
  post {
    always {
      echo 'Pipeline finished. Inspect container logs if needed.'
    }
  }
}
```

How to verify everything is working

1. Metrics
   - Open http://localhost:8000/metrics or:
     ```
     curl http://localhost:8000/metrics | head -n 50
     ```
   - You should see `total_deliveries`, `pending_deliveries`, `on_the_way_deliveries`, and `average_delivery_time_*` metrics.

2. Prometheus
   - Open http://localhost:9090
   - Status -> Targets: you should see `delivery_service` target UP for `delivery_metrics:8000`.
   - Use the "Graph" tab to query `pending_deliveries` or `total_deliveries`.

3. Grafana
   - Open http://localhost:3000
   - Login: admin/admin
   - Add data source:
     - Type: Prometheus
     - URL: http://prometheus:9090
     - Save & Test
   - Create a dashboard with panels:
     - total_deliveries
     - pending_deliveries
     - on_the_way_deliveries
     - Average delivery time: use expression `average_delivery_time_sum / average_delivery_time_count`

4. Alerts
   - Prometheus configuration loads `alert_rules.yml`. In Prometheus UI, go to Alerts — you should see rules defined.
   - To force the pending deliveries alert, update the service (or docker-compose environment) to set `PENDING_MODE=high`. With docker-compose:
     ```
     docker-compose down
     # Edit docker-compose.yml: set PENDING_MODE=high under delivery_metrics.service.environment
     docker-compose up -d --build
     ```
   - Prometheus evaluates rules every `scrape_interval` (15s by default) and alerts will fire if conditions hold for the `for:` time (15s).

Troubleshooting & notes
- Networking:
  - The docker-compose network makes Prometheus able to reach delivery_metrics via `delivery_metrics:8000`. If you run containers manually, ensure they share a user-defined network and use container name in prometheus.yml.
  - host.docker.internal is not required with this compose setup.
- Prometheus alert expression:
  - The rule for average delivery time avoids dividing by zero by checking `average_delivery_time_count > 0`.
- Jenkins:
  - Jenkinsfile expects Docker and docker-compose on the Jenkins agent. If Jenkins runs in a container, the container needs Docker socket access (or use a Docker-enabled agent).
- Resource usage:
  - This demo scrapes every 15s and the app pushes metrics every second. Adjust sleep and scrape_interval for lower resource usage in constrained environments.

Example quick commands summary
```
# Build and run locally
docker-compose up --build -d

# Check logs
docker-compose logs -f prometheus

# Simulate alert (set PENDING_MODE to high)
# Edit docker-compose.yml or:
docker-compose down
# set PENDING_MODE=high in the file, then:
docker-compose up -d --build
```

If you want, I can:
- Generate these files as a Git patch or open a PR in a repo you specify.
- Provide a minimal `docker run` sequence (without docker-compose) for your OS (Linux vs Mac/Windows).
- Add a Grafana dashboard JSON export for quick import.

Let me know which of the above you'd like me to produce next.