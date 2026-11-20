#!/bin/sh
# Generates two kinds of logs forever:
#   /logs/app.log     structured JSON (good practice)
#   /logs/access.log  nginx "combined" format (needs grok to parse)

ROUTES="/api/orders /api/users /api/cart /healthz /api/payments"
LEVELS="info info info info warn error"
IPS="10.0.0.12 10.0.0.15 172.16.4.2 192.168.1.20"

pick() { # pick a random word from a list
  set -- $1
  n=$(( RANDOM % $# + 1 ))
  eval echo "\${$n}"
}

echo "log-generator started"
while true; do
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  route=$(pick "$ROUTES")
  level=$(pick "$LEVELS")
  ms=$(( RANDOM % 900 + 20 ))
  user=$(( RANDOM % 500 + 1 ))

  if [ "$level" = "error" ]; then
    status=500; msg="database timeout"
  elif [ "$level" = "warn" ]; then
    status=429; msg="rate limit hit"
  else
    status=200; msg="request completed"
  fi

  echo "{\"@timestamp\":\"$ts\",\"level\":\"$level\",\"service\":\"shop-api\",\"route\":\"$route\",\"status\":$status,\"duration_ms\":$ms,\"user_id\":$user,\"msg\":\"$msg\"}" >> /logs/app.log

  ip=$(pick "$IPS")
  nginx_ts=$(date -u +"%d/%b/%Y:%H:%M:%S +0000")
  echo "$ip - - [$nginx_ts] \"GET $route HTTP/1.1\" $status $(( RANDOM % 5000 + 200 )) \"-\" \"curl/8.4.0\"" >> /logs/access.log

  sleep 1
done
