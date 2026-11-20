# Kibana KQL • Elasticsearch API • Splunk SPL • TraceQL

## Kibana KQL (Discover search bar)

Run the EFK lab, then in Kibana create data views `fluentbit-app-*` and `logstash-access-*`.

```text
level : "error"
level : "error" and route : "/api/orders"
status >= 500
duration_ms > 500 and not route : "/healthz"
route : /api/*
msg : "database timeout"
tags : "server_error"
http.response.status_code >= 500
not level : "info"
```

## Elasticsearch REST API (curl)

```bash
curl -s localhost:9200/_cluster/health?pretty           # green / yellow / red
curl -s localhost:9200/_cat/nodes?v                      # nodes
curl -s localhost:9200/_cat/indices?v                    # indices, doc counts, size
curl -s localhost:9200/_cat/shards?v                     # where each shard lives

# Search: last 5 errors
curl -s -H 'Content-Type: application/json' localhost:9200/fluentbit-app-*/_search?pretty -d '{
  "size": 5,
  "sort": [{"@timestamp": "desc"}],
  "query": {"term": {"level": "error"}}
}'

# Aggregation: count by route
curl -s -H 'Content-Type: application/json' localhost:9200/fluentbit-app-*/_search?pretty -d '{
  "size": 0,
  "aggs": {"by_route": {"terms": {"field": "route.keyword"}}}
}'

# Delete old indices (careful!)
curl -X DELETE localhost:9200/fluentbit-app-2026.01.01
```

## Splunk SPL

```text
index=web sourcetype=access_combined status>=500
index=web status>=500 | stats count by host, uri_path | sort -count
index=app level=error | timechart span=5m count by service
index=app "payment failed" | rex "user_id=(?<user>\d+)" | stats dc(user) as affected_users
index=web | stats avg(response_time) p95(response_time) by uri_path
index=app earliest=-1h level=error | top limit=10 msg
index=security action=failure | stats count by src_ip | where count > 20
```

| SPL command | Does |
|-------------|------|
| `search` / implicit | filter events |
| `stats` | aggregate (count, avg, p95, dc) |
| `timechart` | aggregate over time for charts |
| `rex` | extract fields with regex |
| `eval` | compute new fields |
| `where` | filter on computed values |
| `top` / `rare` | most / least common values |
| `table` / `fields` | choose columns |

## TraceQL (Grafana Tempo)

```text
{ resource.service.name = "sample-app" }
{ status = error }
{ duration > 1s }
{ span.http.route = "/api/orders" && status = error }
{ resource.service.name = "frontend" } >> { resource.service.name = "payment" && duration > 500ms }
```

## Jaeger UI search tips

- Service: `sample-app`, Operation: `GET /api/orders`
- Tags: `error=true`  or  `payment.method=paypal`
- Min Duration: `1s` to find slow traces
- Use **Compare** to diff a fast and a slow trace of the same operation
