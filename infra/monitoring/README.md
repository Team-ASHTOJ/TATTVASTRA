# Monitoring foundation

Enable `app` and `monitoring` Compose profiles together. Prometheus scrapes the actual HTTP counter. Grafana has a provisioned Prometheus source; no fabricated dashboards or performance samples are seeded. OpenTelemetry Collector configuration is supplied, but application OTLP exporters and forensic spans are not wired yet. Trace debug output must remain free of evidence/secrets before enabling exporters. Operational compiler/agent/distributed charts remain P9 work.
