"""
sample-app: a tiny Flask service instrumented with all three pillars.

  METRICS -> prometheus_client, exposed at /metrics
  LOGS    -> JSON lines on stdout (with trace_id / span_id)
  TRACES  -> OpenTelemetry SDK, exported via OTLP to the OTel Collector
"""
import json
import logging
import random
import sys
import time

from flask import Flask, Response, jsonify, request
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge, Histogram,
                               generate_latest)

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# ------------------------------------------------------------------
# TRACES: set up OpenTelemetry (endpoint comes from
# OTEL_EXPORTER_OTLP_ENDPOINT, service name from OTEL_SERVICE_NAME)
# ------------------------------------------------------------------
provider = TracerProvider(resource=Resource.create({"service.version": "1.0.0",
                                                    "deployment.environment": "lab"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(insecure=True)))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("sample-app")


# ------------------------------------------------------------------
# LOGS: structured JSON with the current trace context
# ------------------------------------------------------------------
class JsonFormatter(logging.Formatter):
    def format(self, record):
        ctx = trace.get_current_span().get_span_context()
        entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if ctx.is_valid:
            entry["trace_id"] = format(ctx.trace_id, "032x")
            entry["span_id"] = format(ctx.span_id, "016x")
        entry.update(getattr(record, "extra_fields", {}))
        return json.dumps(entry)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
log = logging.getLogger("sample-app")
log.setLevel(logging.INFO)
log.addHandler(handler)
logging.getLogger("werkzeug").setLevel(logging.WARNING)


def log_info(msg, level=logging.INFO, **fields):
    log.log(level, msg, extra={"extra_fields": fields})


# ------------------------------------------------------------------
# METRICS: RED metrics + one business metric
# ------------------------------------------------------------------
REQUESTS = Counter("http_requests_total", "Total HTTP requests",
                   ["method", "route", "status"])
LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency",
                    ["route"], buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5))
IN_PROGRESS = Gauge("http_requests_in_progress", "Requests being served right now")
ORDERS = Counter("orders_created_total", "Orders successfully created", ["payment_method"])

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)


@app.before_request
def _start():
    request._start = time.perf_counter()
    IN_PROGRESS.inc()


@app.after_request
def _record(response):
    route = request.url_rule.rule if request.url_rule else "unknown"
    if route != "/metrics":
        elapsed = time.perf_counter() - request._start
        REQUESTS.labels(request.method, route, str(response.status_code)).inc()
        LATENCY.labels(route).observe(elapsed)
    IN_PROGRESS.dec()
    return response


@app.route("/")
def index():
    return jsonify(service="sample-app", status="ok",
                   try_these=["/api/orders", "/api/slow", "/metrics", "/healthz"])


@app.route("/healthz")
def healthz():
    return "ok"


@app.route("/api/orders")
def create_order():
    # child span 1: pretend database query
    with tracer.start_as_current_span("db.query") as span:
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.statement", "SELECT * FROM carts WHERE user_id = $1")
        time.sleep(random.uniform(0.01, 0.08))

    # child span 2: pretend payment provider call (sometimes fails)
    method = random.choice(["card", "card", "paypal"])
    with tracer.start_as_current_span("payment.charge") as span:
        span.set_attribute("payment.method", method)
        time.sleep(random.uniform(0.02, 0.15))
        if random.random() < 0.10:  # ~10% of orders fail
            span.set_status(trace.Status(trace.StatusCode.ERROR, "card declined"))
            log_info("payment failed", logging.ERROR, route="/api/orders",
                     payment_method=method, reason="card declined")
            return jsonify(error="payment failed"), 502

    order_id = random.randint(1000, 9999)
    ORDERS.labels(method).inc()
    log_info("order created", route="/api/orders", order_id=order_id, payment_method=method)
    return jsonify(order_id=order_id, status="created")


@app.route("/api/slow")
def slow():
    delay = random.choice([0.1, 0.2, 0.3, 1.5])  # sometimes very slow
    with tracer.start_as_current_span("report.generate") as span:
        span.set_attribute("report.delay_seconds", delay)
        time.sleep(delay)
    if delay > 1:
        log_info("slow report generated", logging.WARNING, route="/api/slow", delay_s=delay)
    return jsonify(delay=delay)


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/webhook/alerts", methods=["POST"])
def alert_webhook():
    """Alertmanager posts here, so you can SEE alerts arrive in the app logs."""
    payload = request.get_json(silent=True) or {}
    for alert in payload.get("alerts", []):
        log_info("ALERT RECEIVED", logging.WARNING,
                 alertname=alert.get("labels", {}).get("alertname"),
                 alert_status=alert.get("status"),
                 summary=alert.get("annotations", {}).get("summary"))
    return "", 204


if __name__ == "__main__":
    log_info("sample-app starting", port=8000)
    app.run(host="0.0.0.0", port=8000, threaded=True)
