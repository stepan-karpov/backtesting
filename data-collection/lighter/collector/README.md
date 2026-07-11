```
cd data-collection/lighter/collector/

docker build -t lighter-collector .

docker run -d \
  --name lighter-collector \
  -v ~/backtesting/data/lighter:/data \
  -e DATA_ROOT=/data \
  lighter-collector
```