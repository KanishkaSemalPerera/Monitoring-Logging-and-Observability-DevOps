# Kubernetes Reference Manifests

These files show how the same ideas look in Kubernetes. They are **reference examples** for reading and adapting. In real clusters most teams install these with Helm charts:

| What | Helm chart |
|------|-----------|
| Prometheus + Alertmanager + Grafana + node-exporter + kube-state-metrics | `prometheus-community/kube-prometheus-stack` |
| Loki | `grafana/loki` |
| Grafana Alloy | `grafana/alloy` |
| Fluent Bit | `fluent/fluent-bit` |
| OpenTelemetry Collector | `open-telemetry/opentelemetry-collector` |
| Jaeger | `jaegertracing/jaeger` |

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80
```

| File | Shows |
|------|-------|
| `servicemonitor.yaml` | How the Prometheus Operator discovers your app's `/metrics` |
| `prometheusrule.yaml` | Alert rules as a Kubernetes object |
| `fluent-bit-daemonset.yaml` | Fluent Bit running on every node (the "F" in EFK) |
