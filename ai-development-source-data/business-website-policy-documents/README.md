# Company Policy Documents
> (c) Venkata Bhattaram

A synthetic corpus of **company policy documents, PDFs and websites for three fictional companies**, built as source data for AI training (RAG, document Q&A, classification, extraction and agent evaluation).

> **All companies, people, addresses, phone numbers, registration numbers and figures are fictional.** Phone numbers use reserved `555` ranges, domains use the reserved `.example` TLD, and regulatory references (IMDG, MLC, Reg E, HIPAA, etc.) are cited for realism only. Nothing here is legal, financial or medical advice.

## The companies

| | Company | Industry | Region | Explainer |
|---|---|---|---|---|
| <img src="oceanx-logistics/brand/icon.svg" width="40" alt="OceanX icon"> | **OceanX Logistics** | Ocean container shipping & logistics | Global - HQ Singapore; China, USA, EU, India | [oceanx-logistics.md](oceanx-logistics.md) |
| <img src="atlas-retail-bank/brand/icon.svg" width="40" alt="Atlas icon"> | **Atlas Retail Bank** | Retail & small-business banking | US East Coast - HQ Baltimore, MD | [atlas-retail-bank.md](atlas-retail-bank.md) |
| <img src="amerimed-wellness-institute/brand/icon.svg" width="40" alt="Amerimed icon"> | **Amerimed Wellness Institute** | Hospitals, clinics, urgent care & telehealth | US West Coast - HQ San Jose, CA | [amerimed-wellness-institute.md](amerimed-wellness-institute.md) |

## What's in each company folder

```
<company>/
├── company.yaml          # structured profile: legal entity, HQ, offices, leadership, key figures, brand colours
├── brand/
│   ├── logo.svg / .png   # full logo (wordmark)
│   └── icon.svg / .png   # square app / favicon icon
├── documents/
│   ├── *.pdf             # branded policy PDFs (generated)
│   └── source/*.md       # Markdown source of each PDF, with YAML front matter (doc_id, owner, version...)
└── website/
    ├── content.yaml      # website copy
    ├── *.html            # Home, About, Services, Policies & Documents, FAQ, Careers, Contact
    └── assets/           # style.css, logo.svg, icon.svg
```

## Corpus summary

| Company | PDFs | Website pages | Document categories |
|---|---|---|---|
| OceanX Logistics | 10 | 7 | HR, Customer (onboarding, payments, refunds, customs, tariffs, dangerous goods, claims), Fleet, Crew |
| Atlas Retail Bank | 9 | 7 | HR, Customer agreements & disclosures (CIP, Truth in Savings, fees, Reg CC, Reg E, GLBA privacy), BSA/AML, Fair Lending |
| Amerimed Wellness Institute | 8 | 7 | HR, Patient (rights, HIPAA privacy, financial assistance, billing, registration & telehealth), Infection Control, Compliance |

## Rebuilding

Edit the Markdown sources, `company.yaml` or `website/content.yaml`, then run:

```bash
pip install markdown pyyaml
python _tools/build.py          # PDFs (via headless Chrome/Edge) + PNG logos
python _tools/build_sites.py    # static websites
```

`build.py` accepts a company folder name to rebuild just one company, e.g. `python _tools/build.py atlas-retail-bank`.

## Ideas for AI training use

- **RAG / document Q&A:** "What is OceanX's free time for reefers in Rotterdam?", "How long does Atlas take to resolve a Reg E dispute for a new account?"
- **Cross-format consistency:** the same facts appear in YAML, Markdown, PDF and HTML, so you can test extraction from each format.
- **Classification:** route documents by `category` / `classification` in the front matter.
- **Policy-compliance agents:** customer-service and HR assistants grounded on one company's policy set.
- **Negative tests:** questions about topics in each company's checklist that have no document yet should be answered "not covered".
