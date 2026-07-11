```
docker run -d \
  --name lighter-collector \
  -v ~/data:/data \
  -e DATA_ROOT=/data \
  lighter-collector
```