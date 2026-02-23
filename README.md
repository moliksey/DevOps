# Лабораторная работа по DevOps

## Лабораторная раота №1

Билдим образ контейнера 
``` bash
    docker build -t random-cat-app .
```
Запускаем сбилженый образ
``` bash
    docker run -d -p 8000:8000 random-cat-app 
```
По адресу http://localhost:8000/ открывается приложение.

## Лабораторная работа №2

Пушим образ в docker hub.

``` bash 
    sudo docker login -u moliksey1
    docker tag random-cat-app moliksey1/devops-lab:v-0-0-1
    docker push moliksey1/devops-lab:v-0-0-1
```
Переходим на wsl и ставим kind

``` bash
    wsl
    cd ~
    curl -Lo kind https://kind.sigs.k8s.io/dl/v0.26.0/kind-linux-amd64
    chmod +x kind
    sudo mv kind /usr/local/bin/
    kind version
```

Создаем локальный кластер

``` bash 
    kind create cluster --name hw-cluster1
```

Смотрим информацию о всех компьютерах в кластере

|NAME|STATUS|ROLES|AGE|VERSION|
|----|------|-----|---|-------|
|hw-cluster1-control-plane|Ready|control-plane|27s|v1.32.0|

Добавляем конфигурационный файл 
``` yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: web
          image: moliksey1/devops-lab:v-0-0-1
          ports:
            - containerPort: 8000
          livenessProbe:
            httpGet:
              path: /
              port: 8000
```
И отправляем эту конфигурацию в главную ноду кластера.
``` bash 
    kubectl apply -f deployment-web.yaml
```
Смотрим созданные контейнеры

|NAME|READY|STATUS|RESTARTS|AGE|
|----|-----|------|--------|---|
|web-6b66d587bd-47lmh|1/1|Running|0|5m14s|
|web-6b66d587bd-z5mvs|1/1|Running|0|5m14s|

Пробросим порты, создадим тунель:

``` bash 
    kubectl port-forward deployment/web 8080:8000
```
Заработало!!!

##  Лабораторная раота №3

Скачиваем и билдим приложение, и сразу запускаем его. (Сеть сама не создавалась, по этому пришлось создать ее вручную)
``` bash
    git clone https://github.com/Lanjetto/demo-prometeus-app
    cd demo-prometeus-app/
    docker network create demo-network
    docker compose up --build -d
```

Добавим конфигурационный файл прометеуса
``` yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
```

И запускаем его с примонтированным файлом конфигурации
``` bash
    docker run -d -p 9090:9090 -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml --name prometheus prom/prometheus
```
Скачаем и установим node_exporter как сервис, потому что так рекомендовано.
``` bash
сd /tmp
wget $(curl -s https://api.github.com/repos/prometheus/node_exporter/releases/latest | grep browser_download_url | grep linux-amd64 | cut -d '"' -f 4)
tar -xvf node_exporter-*.tar.gz
cd node_exporter-1.10.2.linux-amd64
sudo useradd --no-create-home --shell /bin/false node_exporter
sudo cp node_exporter /usr/local/bin/
sudo chown node_exporter:node_exporter /usr/local/bin/node_exporter
sudo nano /etc/systemd/system/node_exporter.service
```

Загружаем службу и запускаем ее:

``` bash 
    sudo systemctl daemon-reload
    sudo systemctl enable node_exporter
    sudo systemctl start node_exporter
```
Прописываем конфиги 
``` yaml
  - job_name: 'node'
    scrape_interval: 5s
    static_configs:
      - targets: ['192.168.210.65:9100']

  - job_name: 'app'
    scrape_interval: 5s
    metrics_path: '/actuator/prometheus'
    static_configs:
      - targets: ['app:8080']
```

Скачаем плагин Loki для сбора логов
``` bash
docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions
```

Добавим конфигурации Grafana, Loki и добавим плагин loki для сбора логов приложения. А так же перенесем конфиг прометеуса в docker compose.

``` yaml
services:
  app:
    build: .
    ports:
      - "8080:8080"
    restart: unless-stopped
    logging:
      driver: loki
      options:
        loki-url: "http://localhost:3100/loki/api/v1/push"
    networks:
      - demo-network
  
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped
    networks:
      - demo-network
    volumes:
      - ../../prometheus.yml:/etc/prometheus/prometheus.yml:ro
  
  loki:
    image: grafana/loki:2.9.8
    container_name: loki
    ports:
      - "3100:3100"
    restart: unless-stopped
    networks:
      - demo-network
    command: -config.file=/etc/loki/local-config.yaml

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    restart: unless-stopped
    networks:
      - demo-network
    depends_on:
      - prometheus
      - loki
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
```