import time
import random
from flask import Flask, Response, jsonify
from prometheus_client import Counter, Gauge, Histogram, generate_latest


app = Flask(__name__)

data_blob = "X" * 1_000

REQUEST_COUNT = Counter("sensor_requests_total", "Total sensor requests")
CPU_SPIKE = Gauge("sensor_cpu_spike", "Simulated CPU spike state")
PROCESS_LATENCY = Histogram("sensor_processing_latency_seconds", "Processing time")
FAILED_EVENTS = Counter("sensor_failed_events_total", "Total failed sensor events", ["reason"])

@app.route("/metrics")
def metrics():
    start = time.time()
    PROCESS_LATENCY.observe(time.time() - start)
    is_spiking = random.randint(0, 1)
    CPU_SPIKE.set(is_spiking)
    if is_spiking:
        FAILED_EVENTS.labels(reason="cpu_spike").inc()
    REQUEST_COUNT.inc()
    return Response(generate_latest(), mimetype='text/plain; version=0.0.4; charset=utf-8')

@app.route("/sensor")
def sensor():
    try:
        if random.random() < 0.2:
            return jsonify({"data": data_blob})
        return jsonify({"status": "ok"})
    except Exception as e:
        FAILED_EVENTS.labels(reason="route_error").inc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)