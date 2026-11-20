# LogQL Cheat Sheet (Grafana Loki)

Use in Grafana → Explore → data source **Loki** while the lab is running.

## Log stream selector (always required)

```logql
{service_name="sample-app"}                          # one stream
{service_name=~"sample-app|loadgen"}                 # regex
{service_name="sample-app", level="error"}           # several labels
```

## Line filters (fast, like grep)

```logql
{service_name="sample-app"} |= "payment"             # contains
{service_name="sample-app"} != "healthz"             # does not contain
{service_name="sample-app"} |~ "timeout|refused"     # regex
{service_name="sample-app"} !~ "GET /metrics"        # regex not
```

## Parsers + label filters

```logql
{service_name="sample-app"} | json                                   # extract JSON fields
{service_name="sample-app"} | json | level="error"
{service_name="sample-app"} | json | route="/api/orders" | payment_method="paypal"
{service_name="sample-app"} | logfmt                                 # key=value logs
{job="nginx"} | pattern `<ip> - - [<_>] "<method> <path> <_>" <status> <_>` | status >= 500
{service_name="sample-app"} | json | line_format "{{.level}} {{.msg}} trace={{.trace_id}}"
```

## Find all logs for one trace

```logql
{service_name="sample-app"} |= "4bf92f3577b34da6a3ce929d0e0e4736"
```

## Metric queries (turn logs into numbers)

```logql
# log lines per second per level
sum by (level) (rate({service_name="sample-app"}[1m]))

# errors in the last 5 minutes
sum(count_over_time({service_name="sample-app", level="error"}[5m]))

# payment failures per method
sum by (payment_method) (count_over_time({service_name="sample-app"} | json | msg="payment failed" [5m]))

# p95 of a numeric field from logs
quantile_over_time(0.95, {job="shop"} | json | unwrap duration_ms [5m]) by (route)
```

## Label rules (important!)

| Good labels (low cardinality) | Bad labels (high cardinality) |
|------|------|
| `service_name`, `env`, `cluster`, `namespace`, `level` | `trace_id`, `user_id`, `request_id`, `ip`, `order_id` |

High-cardinality values go in the log line (or structured metadata) and are searched with filters, not labels.
