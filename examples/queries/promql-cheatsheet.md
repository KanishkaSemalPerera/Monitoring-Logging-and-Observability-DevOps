# PromQL Cheat Sheet

Paste these into Prometheus (http://localhost:9090) or Grafana Explore while the lab is running.

## Selectors

```promql
http_requests_total                                   # all series of this metric
http_requests_total{job="sample-app"}                 # exact match
http_requests_total{status=~"5.."}                    # regex match (500-599)
http_requests_total{route!="/healthz"}                # not equal
http_requests_total{status!~"2.."}                    # regex not match
http_requests_total[5m]                               # range vector: last 5 minutes of samples
http_requests_total offset 1h                         # value 1 hour ago
```

## Counters: always wrap in rate() or increase()

```promql
rate(http_requests_total[5m])                         # per-second average over 5m
irate(http_requests_total[5m])                        # per-second, last 2 samples (spiky)
increase(http_requests_total[1h])                     # total increase over 1 hour
sum(rate(http_requests_total[5m]))                    # total RPS for everything
sum by (route) (rate(http_requests_total[5m]))        # RPS per route
```

## RED for a service

```promql
# Rate
sum(rate(http_requests_total{job="sample-app"}[5m]))

# Errors (ratio 0..1)
sum(rate(http_requests_total{job="sample-app",status=~"5.."}[5m]))
/
sum(rate(http_requests_total{job="sample-app"}[5m]))

# Duration (p95 from a histogram)
histogram_quantile(0.95,
  sum by (le) (rate(http_request_duration_seconds_bucket{job="sample-app"}[5m])))

# Average latency
sum(rate(http_request_duration_seconds_sum[5m]))
/
sum(rate(http_request_duration_seconds_count[5m]))
```

## USE for a Linux host (node_exporter)

```promql
# CPU utilization %
100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])))

# Memory utilization %
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)

# Disk space used %
100 * (1 - node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"}
          / node_filesystem_size_bytes{fstype!~"tmpfs|overlay"})

# Saturation: load average per CPU
node_load1 / count without (cpu, mode) (node_cpu_seconds_total{mode="idle"})

# Network received bytes/sec
rate(node_network_receive_bytes_total{device!="lo"}[5m])

# Will the disk fill in the next 4 hours?
predict_linear(node_filesystem_avail_bytes[1h], 4 * 3600) < 0
```

## Aggregation operators

| Operator | Example |
|----------|---------|
| `sum` | `sum by (route) (rate(x[5m]))` |
| `avg` / `min` / `max` | `max by (instance) (node_load1)` |
| `count` | `count(up == 1)` = number of healthy targets |
| `topk` / `bottomk` | `topk(5, sum by (route) (rate(x[5m])))` |
| `quantile` | `quantile(0.9, node_load1)` |
| `without` | `sum without (instance) (rate(x[5m]))` drop a label |

## Useful functions

| Function | Use |
|----------|-----|
| `rate()` | per-second rate of a counter |
| `increase()` | total increase of a counter over a range |
| `histogram_quantile()` | percentile from histogram buckets |
| `predict_linear()` | forecast a gauge |
| `delta()` / `deriv()` | change of a gauge |
| `avg_over_time()` / `max_over_time()` | aggregate a gauge over time |
| `absent()` | alert when a metric disappears completely |
| `changes()` | how often a value changed (e.g. restarts) |
| `label_replace()` | rename / build labels |
| `clamp_min()` / `clamp_max()` | bound a value |

## Kubernetes (kube-state-metrics + cAdvisor)

```promql
# Pods not Running
sum by (namespace) (kube_pod_status_phase{phase!~"Running|Succeeded"})

# Container restarts in last hour
increase(kube_pod_container_status_restarts_total[1h]) > 0

# Container CPU usage (cores)
sum by (pod) (rate(container_cpu_usage_seconds_total{container!=""}[5m]))

# Memory working set vs limit
sum by (pod) (container_memory_working_set_bytes{container!=""})
/
sum by (pod) (kube_pod_container_resource_limits{resource="memory"})
```

## Common mistakes

| Mistake | Fix |
|---------|-----|
| `sum(http_requests_total)` | Counters need `rate()` first: `sum(rate(http_requests_total[5m]))` |
| `rate(sum(x)[5m])` | `rate` first, then `sum`: `sum(rate(x[5m]))` |
| `histogram_quantile(0.95, rate(x_bucket[5m]))` across many pods | aggregate keeping `le`: `sum by (le) (...)` |
| Range shorter than 2 scrape intervals | use at least `4 × scrape_interval`, e.g. `[1m]` for 15s |
| `avg` of percentiles | you cannot average p95s; recompute from buckets |
