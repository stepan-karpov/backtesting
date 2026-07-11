```
cd data-collection/lighter/collector/

sudo docker build -t lighter-collector .

sudo docker run -d \
  --name lighter-collector \
  -v ~/backtesting/data/lighter:/data \
  -e DATA_ROOT=/data \
  lighter-collector
```