#!/bin/bash
set -e

echo "[$(date)] Starting main.py in background..."
python main.py &

echo "[$(date)] Starting encoder loop (every 25 minutes)..."

while true; do
  sleep 1500   # 25 минут = 1500 секунд
  echo "[$(date)] Running encoder.py..."
  python encoder.py
done
