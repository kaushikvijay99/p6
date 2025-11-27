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
