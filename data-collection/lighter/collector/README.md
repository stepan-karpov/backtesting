```
docker run -d \
  --name lighter-collector \
  -v ~/backesting/data/lighter:/data \
  -e DATA_ROOT=/data \
  lighter-collector
```