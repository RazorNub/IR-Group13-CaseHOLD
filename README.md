# Legal Retrieval using CaseHOLD (IR Project 13, Group 13)

Vaibhav Bansal (23FE10CSE00333), Pranav Joshi (23FE10CSE00701), Ishaan Manocha (23FE10CSE00143)
CSE4144 Information Retrieval, Manipal University Jaipur, 2026-27.

We turn the CaseHOLD multiple-choice dataset into a retrieval task. The query is the passage that cites a
case; the documents are all unique holding statements of the split (13,297 in test); each query has exactly
one relevant holding. We compare TF-IDF, BM25 (our own implementation on an inverted index), a Sentence
Transformer (all-MiniLM-L6-v2) and Reciprocal Rank Fusion, plus two extensions: fine-tuning MiniLM on the
CaseHOLD train split and re-ranking with a cross-encoder.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
bash run_all.sh                     # every number, table and chart
streamlit run app/search_app.py     # search interface for the demo
```

Data comes from Hugging Face (`coastalcph/lex_glue`, config `case_hold`) and is cached in `data/`.
Tested on Python 3.13, Apple M4 Pro laptop (neural models on the MPS GPU; CPU also works, just slower).

## Layout

| Path | What it does |
|---|---|
| `src/data.py` | loads CaseHOLD and builds queries, the holdings pool and relevance labels |
| `src/preprocess.py` | cleaning, tokenisation, stop words, Porter stemming |
| `src/index.py` | inverted index, BM25, TF-IDF |
| `src/dense.py` | sentence-transformer encoding (cached) and cross-encoder scoring |
| `src/fusion.py` | Reciprocal Rank Fusion |
| `src/metrics.py` | P@k, Recall@k, MAP/MRR, nDCG@10, PR points |
| `src/tune.py` | picks every setting on the validation split |
| `src/finetune_dense.py` | optional: fine-tunes MiniLM on the train split |
| `src/run_experiments.py` | runs everything on the test split, writes `results/` |
| `src/error_analysis.py`, `src/make_figures.py` | error analysis and charts |
| `app/search_app.py` | Streamlit search interface |
| `report/` | scripts that build the report, slides and viva sheet from `results/` |
| `deliverables/` | report, slides and viva sheet (.docx/.pptx and .pdf) |

## Test results (full pool: 3,600 queries, 13,297 holdings)

| Model | P@10 | R@10 | R@100 | MAP (=MRR) | nDCG@10 | 5-choice acc. |
|---|---|---|---|---|---|---|
| TF-IDF | 0.049 | 0.488 | 0.729 | 0.317 | 0.349 | 0.565 |
| BM25 | 0.049 | 0.493 | 0.710 | 0.323 | 0.356 | 0.590 |
| Dense | 0.037 | 0.373 | 0.605 | 0.234 | 0.260 | 0.526 |
| Dense (fine-tuned) | 0.058 | 0.575 | 0.797 | 0.389 | 0.426 | 0.634 |
| Hybrid RRF (TF-IDF+BM25+Dense) | 0.052 | 0.521 | 0.761 | 0.328 | 0.365 | 0.583 |
| Hybrid RRF (TF-IDF+BM25+Dense, k=1) | 0.053 | 0.530 | 0.759 | 0.342 | 0.379 | 0.582 |
| Hybrid RRF (BM25+Dense) | 0.049 | 0.491 | 0.747 | 0.314 | 0.348 | 0.576 |
| Hybrid RRF (BM25+Dense fine-tuned) | 0.060 | 0.597 | 0.817 | 0.400 | 0.440 | 0.610 |
| Hybrid + cross-encoder re-rank | 0.041 | 0.407 | 0.761 | 0.196 | 0.231 | - |

Chosen on validation: whole passage as query, BM25 k1=0.6, b=0.9, MiniLM as dense model, RRF k=60 (standard) and k=1 (tuned).
P@10 is capped at 0.1 because each query has one relevant holding. The 5-choice column is the original
CaseHOLD multiple-choice accuracy (random = 0.20).
