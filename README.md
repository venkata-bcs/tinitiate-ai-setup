# AI Setup

Local development stack for AI work: relational, document, cache, search, object storage,
streaming and vector databases — all started from one Docker Compose file,
`tinitiate-ai-onboarding.yml`.

> **Local development only.** Every service uses the shared default credentials below.
> Change them before exposing any port outside your machine.

## Docker

### Quick start
```bash
# Start all services in the background
docker compose -f tinitiate-ai-onboarding.yml up -d

# Check status / health
docker compose -f tinitiate-ai-onboarding.yml ps

# Follow logs of one service (e.g. kafka)
docker compose -f tinitiate-ai-onboarding.yml logs -f kafka

# Start only selected services
docker compose -f tinitiate-ai-onboarding.yml up -d postgres redis vectordb

# Stop all services (data is kept)
docker compose -f tinitiate-ai-onboarding.yml down

# Stop and DELETE all data volumes
docker compose -f tinitiate-ai-onboarding.yml down -v
```

Host ports can be overridden with environment variables or a `.env` file next to the
compose file (already git-ignored), e.g.:
```bash
POSTGRES_PORT=15432
REDIS_PORT=16379
```

### Credentials summary

| Service | Container | Host port(s) | Username | Password |
|---|---|---|---|---|
| PostgreSQL 16 | `tinitiate-ai-postgres` | 5432 | `ai_admin` | `ai_admin_pw` |
| MongoDB 7 | `tinitiate-ai-mongodb` | 27017 | `ai_admin` | `ai_admin_pw` |
| Redis 7 | `tinitiate-ai-redis` | 6379 | *(none / `default`)* | `ai_admin_pw` |
| Elasticsearch 8.15 | `tinitiate-ai-elasticsearch` | 9200 | `elastic` | `ai_admin_pw` |
| MinIO | `tinitiate-ai-minio` | 9002 (API), 9003 (console) | `ai_admin` | `ai_admin_pw` |
| Kafka 3.8 (KRaft) | `tinitiate-ai-kafka` | 9092 | `ai_admin` | `ai_admin_pw` |
| Qdrant | `tinitiate-ai-vectordb` | 6333 (HTTP), 6334 (gRPC) | — | API key `ai_admin_pw` |
| Milvus 2.4 | `tinitiate-ai-milvus` | 19530 (gRPC), 9091 (metrics) | `root` | `Milvus` *(Milvus default — see below)* |
| Milvus MinIO | `tinitiate-ai-milvus-minio` | 9000 (API), 9001 (console) | `ai_admin` | `ai_admin_pw` |
| Milvus etcd | `tinitiate-ai-milvus-etcd` | *(internal only)* | — | *(no auth, not exposed)* |

### Service details

#### PostgreSQL
* Image `postgres:16`, database `ai_setup`, volume `postgres_data`
* Port env var: `POSTGRES_PORT` (default `5432`)
```bash
psql "postgresql://ai_admin:ai_admin_pw@localhost:5432/ai_setup"
docker exec -it tinitiate-ai-postgres psql -U ai_admin -d ai_setup
```
Python: `psycopg2.connect("postgresql://ai_admin:ai_admin_pw@localhost:5432/ai_setup")`

#### MongoDB
* Image `mongo:7`, root user created in the `admin` database, initial database `ai_setup`, volume `mongo_data`
* Port env var: `MONGO_PORT` (default `27017`)
```bash
mongosh "mongodb://ai_admin:ai_admin_pw@localhost:27017/ai_setup?authSource=admin"
```
Python: `pymongo.MongoClient("mongodb://ai_admin:ai_admin_pw@localhost:27017/?authSource=admin")`

#### Redis
* Image `redis:7`, password set with `--requirepass`, AOF persistence on, volume `redis_data`
* Port env var: `REDIS_PORT` (default `6379`)
```bash
docker exec -it tinitiate-ai-redis redis-cli -a ai_admin_pw
```
URL: `redis://:ai_admin_pw@localhost:6379/0`

#### Elasticsearch
* Image `docker.elastic.co/elasticsearch/elasticsearch:8.15.0`, single node, security on, **HTTP (no TLS)**, 1 GB heap, volume `elasticsearch_data`
* Port env var: `ELASTIC_PORT` (default `9200`)
* Takes ~60 s to become healthy on first start
```bash
curl -u elastic:ai_admin_pw http://localhost:9200/_cluster/health?pretty
```
Python: `Elasticsearch("http://localhost:9200", basic_auth=("elastic", "ai_admin_pw"))`

#### MinIO (general object storage)
* Image `quay.io/minio/minio:latest`, volume `minio_data`
* Port env vars: `MINIO_API_PORT` (default `9002`), `MINIO_CONSOLE_PORT` (default `9003`)
* Web console: http://localhost:9003 — log in with `ai_admin` / `ai_admin_pw`
* S3 endpoint: `http://localhost:9002`, access key `ai_admin`, secret key `ai_admin_pw`

#### Kafka
* Image `apache/kafka:3.8.0`, single-node KRaft (no ZooKeeper), volume `kafka_data`
* Port env var: `KAFKA_PORT` (default `9092`)
* Listeners: `EXTERNAL` `localhost:9092` (host clients), `INTERNAL` `kafka:29092` (other containers), `CONTROLLER` `9093` (internal)
* Auth: **SASL_PLAINTEXT** with mechanism **PLAIN**, user `ai_admin` / `ai_admin_pw`

Client settings:
```properties
bootstrap.servers=localhost:9092
security.protocol=SASL_PLAINTEXT
sasl.mechanism=PLAIN
sasl.jaas.config=org.apache.kafka.common.security.plain.PlainLoginModule required username="ai_admin" password="ai_admin_pw";
```
Python (`kafka-python` / `confluent-kafka`): `security_protocol="SASL_PLAINTEXT", sasl_mechanism="PLAIN", sasl_plain_username="ai_admin", sasl_plain_password="ai_admin_pw"`

#### Qdrant (VectorDB)
* Image `qdrant/qdrant:latest`, volume `vectordb_data`
* Port env vars: `QDRANT_HTTP_PORT` (default `6333`), `QDRANT_GRPC_PORT` (default `6334`)
* API key `ai_admin_pw` (sent as the `api-key` header)
* Dashboard: http://localhost:6333/dashboard (enter the API key when prompted)
```bash
curl -H "api-key: ai_admin_pw" http://localhost:6333/collections
```
Python: `QdrantClient(url="http://localhost:6333", api_key="ai_admin_pw")`

#### Milvus (VectorDB)
* Image `milvusdb/milvus:v2.4.5`, standalone mode, volume `milvus_data`
* Port env vars: `MILVUS_PORT` (default `19530`), `MILVUS_METRICS_PORT` (default `9091`)
* Depends on `milvus-etcd` (metadata) and `milvus-minio` (object storage), started automatically
* Authentication is **enabled**. Milvus creates the built-in user `root` with password `Milvus`; it cannot be set from the compose file. Change it after first start:
```python
from pymilvus import MilvusClient
client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
client.update_password("root", "Milvus", "ai_admin_pw")
# from then on: token="root:ai_admin_pw"
```
* Health: http://localhost:9091/healthz (may take up to ~90 s on first start)

#### Milvus MinIO / etcd
* `milvus-minio` (`RELEASE.2023-03-20`): storage for Milvus only, volume `milvus_minio_data`. Console http://localhost:9001 with `ai_admin` / `ai_admin_pw`. Port env vars: `MILVUS_MINIO_API_PORT` (9000), `MILVUS_MINIO_CONSOLE_PORT` (9001)
* `milvus-etcd` (`v3.5.5`): Milvus metadata, volume `milvus_etcd_data`, reachable only inside the Docker network

### Volumes
`postgres_data`, `mongo_data`, `redis_data`, `elasticsearch_data`, `minio_data`, `kafka_data`,
`vectordb_data`, `milvus_etcd_data`, `milvus_minio_data`, `milvus_data`

### Troubleshooting
* **Changed a password but login still fails** — Postgres, MongoDB, Elasticsearch and MinIO only apply credentials when their volume is first created. Run `docker compose -f tinitiate-ai-onboarding.yml down -v` (deletes data) and start again.
* **Elasticsearch exits on Linux/WSL** — raise the mmap limit: `sudo sysctl -w vm.max_map_count=262144`.
* **Port already in use** — override the port with the env vars listed above.
* **Containers from an older version (`venkatab-ai-*`)** — remove them with `docker rm -f $(docker ps -aq --filter name=venkatab-ai-)` before starting.

## Python Libraries
Defined in `requirements.txt`:
```bash
pip install -r requirements.txt
```
* python-dotenv
* psycopg2-binary (PostgreSQL)
* pymongo (MongoDB)
* qdrant-client (VectorDB)
* pymilvus (VectorDB)
* anthropic
* openai
* langchain
* langgraph
* langsmith
* crewai
* numpy
* pandas
* mlflow

## NodeJS Libraries
```bash
npm install dotenv pg mongodb @qdrant/js-client-rest @zilliz/milvus2-sdk-node @anthropic-ai/sdk openai
```
* dotenv
* pg (PostgreSQL)
* mongodb (MongoDB)
* @qdrant/js-client-rest (VectorDB)
* @zilliz/milvus2-sdk-node (VectorDB)
* @anthropic-ai/sdk
* openai
