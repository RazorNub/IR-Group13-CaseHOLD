#!/bin/bash
# Reproduces every number, table and chart in the report.
# Run from the project folder after: pip install -r requirements.txt
set -e
export HF_HOME="$PWD/data/hf_cache"
export TOKENIZERS_PARALLELISM=false

python src/tune.py            # 1. pick settings on the validation split
python src/finetune_dense.py  # 2. optional: fine-tune MiniLM on the train split (~10 min on a laptop GPU/MPS)
python src/run_experiments.py # 3. evaluate everything on the test split
python src/error_analysis.py  # 4. failure counts and examples
python src/make_figures.py    # 5. charts into figures/

# 6. rebuild the report, slides and viva sheet from results/ (PDFs need LibreOffice)
python report/build_report.py
python report/build_slides.py
python report/build_qa.py
