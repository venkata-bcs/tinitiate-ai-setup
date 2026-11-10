# AI Development Source Data

Sample data for AI development work: RAG, document Q&A, extraction, classification,
ETL/CDC pipelines and agent evaluation. Everything lives in
[ai-development-source-data/](ai-development-source-data/) and is meant to be loaded into the
services started by [README.md](README.md) (PostgreSQL, MongoDB, Elasticsearch, MinIO, Qdrant, Milvus, ...).

> Company names, people, addresses and figures in the generated data are fictional.

## How students get the data

Running `docker compose -f tinitiate-ai-onboarding.yml up -d` makes everything in this folder
available in two places:

| Where | What | How to reach it |
|---|---|---|
| **MinIO** bucket `ai-source-data` | A copy of the whole `ai-development-source-data/` folder, same paths (`business-data-dumps/…`, `file-formats/…`, …) | Console http://localhost:9003 (`ai_admin` / `ai_admin_pw`), S3 API `http://localhost:9002` |
| **Company websites** | Every company folder under `business-website-policy-documents/`, with its PDFs | http://localhost:8080/business-website-policy-documents/ |

The `minio-seed` job does the copy on every `up`, uploading only new or changed files. The website
server reads the folder directly, so new sites show up without a restart.

## Adding data

* **Data files** (CSV, zipped CSV, Parquet, JSON, images, PDF, …): put them anywhere under
  `ai-development-source-data/` — e.g. `business-data-dumps/sales_2026.parquet`. No config change is
  needed; the next `up` (or `docker compose -f tinitiate-ai-onboarding.yml run --rm minio-seed`) uploads them.
  Files are copied as-is — zip files are not unpacked.
* **Company websites**: add a folder `business-website-policy-documents/<company>/` with the same layout
  as the existing ones (`company.yaml`, `brand/`, `documents/source/*.md`, `website/content.yaml`), run the
  build scripts below, and the site appears at `http://localhost:8080/business-website-policy-documents/<company>/`.
  Add a row for it in the [business-website-policy-documents README](ai-development-source-data/business-website-policy-documents/README.md).
* **Large files:** GitHub rejects files over 100 MB and warns above 50 MB. Track big Parquet/zip files with
  Git LFS (`git lfs track "*.parquet" "*.zip"`) or compress/split them.

## Folder layout

```
ai-development-source-data/
├── business-data-dumps/         # large real-world-style CSV dumps
├── business-website-policy-documents/   # policy PDFs, Markdown sources and websites for 3 fictional companies
├── file-formats/                # small sample files by format: CSV, images, PDF
└── rdbms-content/               # retail/e-commerce schema + CDC batch generator and Postgres loader
```

## Datasets

| Folder | What it contains | Typical use | Details |
|---|---|---|---|
| [business-data-dumps](ai-development-source-data/business-data-dumps/) | `indian_tech_jobs_2026.csv` — ~23,000 tech job postings (title, company, city, experience, salary, skills, work mode, ...) | Pandas analysis, text-to-SQL, embeddings / semantic search over job descriptions | — |
| [business-website-policy-documents](ai-development-source-data/business-website-policy-documents/) | Policy documents for **OceanX Logistics**, **Atlas Retail Bank** and **Amerimed Wellness Institute**: `company.yaml`, branded PDFs, Markdown sources with front matter, and static websites | RAG, document Q&A, cross-format extraction, classification, policy-compliance agents | [README](ai-development-source-data/business-website-policy-documents/README.md) |
| [file-formats/csv](ai-development-source-data/file-formats/csv/) | `customers`, `organizations`, `people`, `products` — 100 rows each | Loading/parsing practice, quick DB seeding | — |
| [file-formats/images](ai-development-source-data/file-formats/images/) | `lic_1.jpg` … `lic_10.jpg` — sample licence images | OCR, vision-model extraction | — |
| [file-formats/pdf](ai-development-source-data/file-formats/pdf/) | Sample bank statements and financial documents | PDF table/text extraction, document parsing | — |
| [rdbms-content](ai-development-source-data/rdbms-content/) | PostgreSQL schema (categories, products, customers, orders, order_items, payments, inventory), a generator that writes an initial batch plus delta batches (`I`/`U`/`D` rows), and an idempotent loader | ETL/CDC pipelines, text-to-SQL, SQL agents | [README](ai-development-source-data/rdbms-content/README.md) |

## Quick start

### Load the retail schema into the local PostgreSQL
```bash
docker compose -f tinitiate-ai-onboarding.yml up -d postgres

cd ai-development-source-data/rdbms-content
pip install -r requirements.txt
docker exec -i tinitiate-ai-postgres psql -U ai_admin -d ai_setup < sql/01_schema.sql
docker exec -i tinitiate-ai-postgres psql -U ai_admin -d ai_setup < sql/02_control_table.sql

cd generator && python generate_data.py      # writes data/batch_NNNN_*/
cd ../loader && python load_data.py          # applies all pending batches
```
> The rdbms-content README still refers to the older `venkatab-ai-*` container names and
> `.env` path; use `tinitiate-ai-postgres` and the `.env` next to `tinitiate-ai-onboarding.yml`.

### Rebuild the policy PDFs and websites
```bash
cd ai-development-source-data/business-website-policy-documents
pip install markdown pyyaml
python _tools/build.py          # PDFs (headless Chrome/Edge) + PNG logos
python _tools/build_sites.py    # static websites
```

## Related READMEs
* [ai-development-source-data/README.md](ai-development-source-data/README.md)
* [business-website-policy-documents/README.md](ai-development-source-data/business-website-policy-documents/README.md)
* [rdbms-content/README.md](ai-development-source-data/rdbms-content/README.md)
