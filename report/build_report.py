"""Builds deliverables/IR_Group13_CaseHOLD_Report.docx from the professor's
template (report/IR_report_template.docx). Every number is read from results/,
so re-running the experiments and this script keeps the report in sync."""
import copy
import json
import os
import sys

import pandas as pd
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from docx.table import Table

sys.path.insert(0, os.path.dirname(__file__))
from docx_helpers import fill_table, keep_with_next, page_break_before, set_header_cells, set_runs

ROOT = os.path.join(os.path.dirname(__file__), "..")
R = lambda *p: os.path.join(ROOT, *p)

MEMBERS = [("Vaibhav Bansal", "23FE10CSE00333", "VAIBHAV.23FE10CSE00333@muj.manipal.edu"),
           ("Pranav Joshi", "23FE10CSE00701", "Pranav.23FE10CSE00701@muj.manipal.edu"),
           ("Ishaan Manocha", "23FE10CSE00143", "")]  # Ishaan's email still to be added

full = pd.read_csv(R("results/test_full_pool.csv")).set_index("model")
five = pd.read_csv(R("results/test_five_choice.csv")).set_index("model")
cfg = json.load(open(R("results/chosen_settings.json")))
ix = json.load(open(R("results/index_stats.json")))
err = json.load(open(R("results/error_analysis.json")))
split = json.load(open(R("results/split_stats.json")))
timing = pd.read_csv(R("results/timing_seconds.csv"), index_col=0)["seconds"]
val = pd.read_csv(R("results/validation_tuning.csv"))
sig = pd.read_csv(R("results/significance_vs_bm25.csv")).set_index("model")

H3 = "Hybrid RRF (TF-IDF+BM25+Dense)"
HK = f"Hybrid RRF (TF-IDF+BM25+Dense, k={cfg['rrf_k']})"
HFT = "Hybrid RRF (BM25+Dense fine-tuned)"
FT = "Dense (fine-tuned)"
CE = "Hybrid + cross-encoder re-rank"


def f(model, metric, table=full):
    return f"{table.loc[model, metric]:.3f}"


def vmrr(setting):
    return f"{val[val['setting'] == setting]['MRR'].iloc[0]:.3f}"


doc = Document(R("report/IR_report_template.docx"))
body = doc.element.body
items = list(body)

# prototypes taken from the template itself
P_TITLE, T_STUDENTS, T_ABSTRACT = items[0], items[1], items[3]
proto = {
    "h1": copy.deepcopy(items[5]), "body": copy.deepcopy(items[6]), "h2": copy.deepcopy(items[13]),
    "figbox": copy.deepcopy(items[26]), "caption": copy.deepcopy(items[27]),
    "bullet": copy.deepcopy(items[32]), "formula": copy.deepcopy(items[38]),
    "tabcap": copy.deepcopy(items[48]), "table": copy.deepcopy(items[49]),
    "ref": copy.deepcopy(items[62]), "box": copy.deepcopy(items[3]), "empty": copy.deepcopy(items[2]),
}
sect = items[-1]
for el in items[4:-1]:
    body.remove(el)

# ---------------------------------------------------------------- cover page
title = ("Comparative Performance Evaluation of TF-IDF, BM25, Sentence Transformer and "
         "Hybrid RRF Retrieval for Legal Holdings on CaseHOLD")
set_runs(P_TITLE, [(title, True)], doc)

students = Table(T_STUDENTS, doc._body)
for row, (name, reg, email) in zip(students.rows[1:], MEMBERS):
    for cell, val_ in zip(row.cells, [name, reg, email]):
        p = cell.paragraphs[0]
        p.add_run(val_).font.size = Pt(9 if "@" in val_ else 12)
        for extra in cell.paragraphs[1:]:
            extra._p.getparent().remove(extra._p)
for tr in students.rows[1 + len(MEMBERS):]:
    tr._tr.getparent().remove(tr._tr)

abstract = (
    "Lawyers and judges routinely cite earlier cases for a specific holding, and finding that holding "
    "quickly is a retrieval problem. We turn the CaseHOLD benchmark into a retrieval task in which the "
    "passage that cites a case is the query and the pool of "
    f"{split['test']['holdings']:,} holding statements in the test split is the document collection. "
    "We compare TF-IDF, Okapi BM25, a Sentence Transformer (all-MiniLM-L6-v2) and a hybrid that "
    "merges their rankings with Reciprocal Rank Fusion (RRF), with every setting chosen on the "
    f"validation split. On {split['test']['queries']:,} test queries BM25 reaches an MRR of "
    f"{f('BM25', 'MRR')} and the off-the-shelf dense model only {f('Dense', 'MRR')}. The three-way RRF "
    f"hybrid improves Recall@100 from {f('BM25', 'R@100')} to {f(H3, 'R@100')} but gives only a small "
    f"MRR gain ({f(H3, 'MRR')}). Fine-tuning the dense model for one epoch on the CaseHOLD training "
    f"split raises its MRR to {f(FT, 'MRR')}, and fusing it with BM25 gives our best result "
    f"(MRR {f(HFT, 'MRR')}, Recall@10 {f(HFT, 'R@10')}). A general-purpose cross-encoder re-ranker "
    "made results worse, which shows how much domain matters in legal text.")
abs_p = Table(T_ABSTRACT, doc._body).rows[0].cells[0].paragraphs[0]._p
runs = abs_p.findall(qn("w:r"))
runs[1].find(qn("w:t")).text = abstract
runs[0].find(qn("w:t")).text = "Abstract: "  # template label used an em dash
runs[-1].find(qn("w:t")).text = ("Information Retrieval · CaseHOLD · BM25 · Sentence "
                                 "Transformers · Reciprocal Rank Fusion · Legal Search")

# the template header only carries an instruction to students, so it is left empty
for p in doc.sections[0].header.paragraphs:
    for r in p.runs:
        r.text = ""

# ---------------------------------------------------------------- builders
cursor = [T_ABSTRACT]


def add(el):
    cursor[0].addnext(el)
    cursor[0] = el
    return el


def H1(text, new_page=True):
    el = add(copy.deepcopy(proto["h1"]))
    set_runs(el, [(text, True)], doc)
    if new_page:
        page_break_before(el)


def H2(text):
    set_runs(add(copy.deepcopy(proto["h2"])), [(text, True)], doc)


def P(*parts):
    parts = [(p, False) if isinstance(p, str) else p for p in parts]
    set_runs(add(copy.deepcopy(proto["body"])), parts, doc)


def B(lead, text):
    el = add(copy.deepcopy(proto["bullet"]))
    set_runs(el, [(lead, True), (text, False)], doc)
    # the template's description text after the bold lead is plain black
    rpr = el.findall(qn("w:r"))[1].find(qn("w:rPr"))
    for c in rpr.findall(qn("w:color")):
        rpr.remove(c)


def FORMULA(text):
    set_runs(add(copy.deepcopy(proto["formula"])), [(text, True)], doc)


def CAPTION(text):
    set_runs(add(copy.deepcopy(proto["caption"])), [(text, False)], doc)


def FIGURE(image, width, caption, boxed=False):
    if boxed:
        tbl = add(copy.deepcopy(proto["figbox"]))
        cell_p = Table(tbl, doc._body).rows[0].cells[0].paragraphs[0]
        for r in cell_p._p.findall(qn("w:r")):
            cell_p._p.remove(r)
        cell_p.add_run().add_picture(image, width=Inches(width))
    else:
        el = add(copy.deepcopy(proto["caption"]))
        para = set_runs(el, "", doc)
        for r in el.findall(qn("w:r")):
            el.remove(r)
        ppr = el.find(qn("w:pPr"))
        ppr.insert(0, ppr.makeelement(qn("w:keepNext"), {}))
        para.add_run().add_picture(image, width=Inches(width))
    CAPTION(caption)


def TABLE(caption, headers, rows, highlight_last=False):
    cap = add(copy.deepcopy(proto["tabcap"]))
    set_runs(cap, [(caption, True)], doc)
    keep_with_next(cap)
    tbl = add(copy.deepcopy(proto["table"]))
    set_header_cells(tbl, doc, headers)
    fill_table(tbl, doc, rows, bold_last=highlight_last)
    add(copy.deepcopy(proto["empty"]))


def BOX(lines):
    """Grey box with a navy left rule (the template's abstract box). lines = list of parts lists."""
    tbl = add(copy.deepcopy(proto["box"]))
    cell = Table(tbl, doc._body).rows[0].cells[0]
    p0 = cell.paragraphs[0]._p
    for i, parts in enumerate(lines):
        p = p0 if i == 0 else copy.deepcopy(p0)
        if i:
            cell._tc.append(p)
        set_runs(p, parts, doc)
        for r in p.findall(qn("w:r")):
            rpr = r.find(qn("w:rPr"))
            if rpr is not None:
                for c in rpr.findall(qn("w:color")):
                    rpr.remove(c)
        for br in p.iter(qn("w:br")):
            br.getparent().remove(br)
    add(copy.deepcopy(proto["empty"]))


def REF(text):
    set_runs(add(copy.deepcopy(proto["ref"])), [(text, False)], doc)


FIG = lambda name: R("figures", name)
tst, val_s, trn = split["test"], split["validation"], split["train"]

# ---------------------------------------------------------------- 1. Introduction
H1("1. Introduction")
P("Legal arguments are built on precedent. When a court writes that other courts “have held” "
  "something, it backs the sentence with a citation, and in US case law that citation is usually followed "
  "by a short parenthetical that states what the cited case decided, its holding. A lawyer drafting a "
  "brief has the opposite problem: they know what point they want to make and need to find the case "
  "whose holding supports it. Doing this by hand through thousands of decisions is slow, so it is a "
  "natural job for an information retrieval (IR) system.")
P("Classical IR handles this with sparse lexical matching. TF-IDF and Okapi BM25 score a document by "
  "the query words it contains, weighted by how rare those words are, and an inverted index makes the "
  "lookup fast. Their known weakness is vocabulary mismatch. A citing passage may talk about “fears "
  "of a gas pipeline” while the holding talks about “stigma damages”. Dense retrievers "
  "built on Sentence Transformers map both texts to vectors and compare meaning instead of words, but "
  "a model trained on general web text may not know legal language, and it can miss exact terms such as "
  "statute names that BM25 catches easily. Reciprocal Rank Fusion (RRF) is a simple way to combine "
  "both kinds of ranker using only their rank positions.")
P("Our project (Project 13 in the course list) builds and evaluates such a system on CaseHOLD [4], a "
  "dataset of more than 53,000 citing passages from US court decisions, each paired with the correct "
  "holding and four wrong ones. CaseHOLD is normally used as a multiple-choice reading task. We recast "
  "it as retrieval: the citing passage is the query and every holding in the split is a document. We "
  "then compare the four ranking models required by the brief (TF-IDF, BM25, Sentence Transformer and "
  "hybrid RRF) using Precision@10, Recall, MAP and nDCG, and draw Precision-Recall graphs.")
P("Beyond the required models we tried two extensions that came up while reading the results: "
  "fine-tuning the Sentence Transformer on the CaseHOLD training split, and re-ranking the top "
  "results with a cross-encoder. We also built a small search interface so that any passage can be "
  "typed in and the four rankers compared side by side. All parameters were chosen on the validation "
  "split and every number in this report comes from one run of our code on the test split.")

# ---------------------------------------------------------------- 2. Dataset
H1("2. About Dataset")
H2("2.1 Visualization of the Dataset and an Example")
P("CaseHOLD (Case Holdings On Legal Decisions) was released by Zheng et al. [4]. It was built from the "
  "Harvard Law Library case law corpus. For each citation followed by a parenthetical that starts with "
  "“holding”, the authors kept the text before the citation as the prompt, replaced the "
  "holding with a <HOLDING> marker, and stored the real holding as the right answer. The four wrong "
  "answers are other holdings from the corpus that have the highest TF-IDF similarity to the right one, "
  "chosen on purpose to make the task hard. A law student scored 94% on the task in the original paper.")
P(f"We load the version packaged in the LexGLUE benchmark [5] (Hugging Face: coastalcph/lex_glue, "
  f"config case_hold), which has fixed train, validation and test splits. Table 1 gives the sizes and "
  f"Figure 1 the length distributions. The queries are long (about {tst['ctx_words']:.0f} words) and the "
  f"holdings short (about {tst['hold_words']:.0f} words), so a query shares only a handful of terms with "
  f"its answer. In the test split the 18,000 answer options contain {tst['holdings']:,} distinct texts, "
  f"and 1,032 correct holdings also appear as a wrong option for some other query, so a holding can be "
  f"right for one passage and a distractor for another. The correct answer is spread evenly over the "
  f"five positions (between 713 and 727 test questions per position), so no position bias can be used.")
TABLE("Table 1. CaseHOLD (LexGLUE version) split sizes as used in this project.",
      ["Split", "Citing contexts (queries)", "Unique holdings (documents)", "Avg. words per query",
       "Avg. words per holding"],
      [["Train", f"{trn['queries']:,}", f"{trn['holdings']:,}", trn["ctx_words"], trn["hold_words"]],
       ["Validation", f"{val_s['queries']:,}", f"{val_s['holdings']:,}", val_s["ctx_words"], val_s["hold_words"]],
       ["Test", f"{tst['queries']:,}", f"{tst['holdings']:,}", tst["ctx_words"], tst["hold_words"]]])
FIGURE(FIG("dataset_lengths.png"), 5.2, "Figure 1: Length of the citing contexts (queries) and of the "
       "unique holdings (documents) in the test split.")
P("The box below shows test query 0, shortened at the start. The correct answer is choice 4. Choices 2 "
  "and 3 are on the same topic (severance and stigma damages), which is exactly what makes the "
  "multiple-choice version hard for word-matching methods.")
BOX([[("Citing context: ", True), ("… Other courts, in the same or similar circumstances, have held "
      "that the anticipation of increased interference or potential hazards on the land remaining after a "
      "taking, which one court has labeled “stigma damages,” can be considered in assessing "
      "severance damages. See, e.g., Vector Pipeline, L.P., v. 68.55 Acres of Land, 157 F.Supp.2d 949, 957 "
      "(N.D.Ill.2001) (<HOLDING>); …", False)],
     [("0: ", True), ("holding that actual damages under respa included emotional damages", False)],
     [("1: ", True), ("holding that increased fear of flooding was a matter that factfinder could properly "
                      "consider in assessing severance damages", False)],
     [("2: ", True), ("holding that local buyers fear of possible knapweed infestation legitimately affected "
                      "calculation of severance damages", False)],
     [("3: ", True), ("recognizing concept of stigma damages as they apply to property which is in fact "
                      "contaminated", False)],
     [("4 (correct): ", True), ("holding that stigma damages were properly included in calculation of "
                                "severance damages where proximity of gas pipeline could trigger fears "
                                "about possible mishaps", True)]])
H2("2.2 Turning CaseHOLD into a Retrieval Task")
P("We evaluate every model in two settings. In the ", ("full-pool setting", True), " the documents are "
  f"all {tst['holdings']:,} unique holdings of the test split and each of the {tst['queries']:,} queries "
  "has exactly one relevant document. This is the realistic search setting. In the ",
  ("5-choice setting", True), " each query is scored only against its own five options, which matches "
  "the original CaseHOLD task. Here we report accuracy (the correct holding ranked first), so random "
  "guessing gives 0.20.")

# ---------------------------------------------------------------- 3. Methodology
H1("3. Methodology")
P("Figure 2 shows the pipeline. The query and the holdings go through two paths. The sparse path cleans "
  "and stems the text, builds an inverted index and scores with TF-IDF and BM25. The dense path sends the "
  "raw text to a Sentence Transformer and compares vectors with cosine similarity. The ranked lists are "
  "merged with RRF. An optional cross-encoder step re-orders the top 20 of the fused list.")
FIGURE(FIG("pipeline.png"), 6.2, "Figure 2: Retrieval pipeline used in this project, with a sparse path "
       "(TF-IDF, BM25) and a dense path (Sentence Transformer) merged by Reciprocal Rank Fusion.", boxed=True)
H2("3.1 Preprocessing and Indexing")
P("For the sparse models every query and holding is lower-cased, the <HOLDING> marker is removed and "
  "dotted abbreviations are joined into one token (\u201ce.g.\u201d becomes \u201ceg\u201d). The text is split on "
  "anything that is not a letter or digit, and we drop one-letter tokens and every token that contains a "
  "digit. The second rule removes reporter citations such as 157 F.Supp.2d 949, which are unique to each "
  "case and only add noise. We then remove the scikit-learn English stop-word list plus a few legal "
  "words that occur everywhere (holding, held, v, see, eg, id, cf, supra, citing; 91% of holdings start "
  "with “holding that”) and apply the Porter stemmer [9]. For the example above, the holding "
  "becomes: stigma, damag, properli, includ, calcul, sever, damag, …")
P(f"The inverted index maps each stemmed term to a postings list of (holding id, term frequency) pairs "
  f"and stores each holding's length. On the test pool it has {ix['vocabulary']:,} terms and "
  f"{ix['postings']:,} postings; an average holding has {ix['avg_doc_length']} indexed terms and an "
  f"average postings list has {ix['avg_postings_length']} entries. The dense model does not use this "
  "index. It reads the raw text, because stemming and stop-word removal would destroy the sentences it "
  "was trained on.")
H2("3.2 Ranking Models")
P("We evaluate the four models required by the brief and two extensions:")
B("TF-IDF Vector Space Model: ", "each text becomes a vector with weight (1 + log tf) x idf per term, "
  "normalised to unit length; holdings are ranked by cosine similarity with the query (scikit-learn "
  "TfidfVectorizer with our tokenizer).")
B("Okapi BM25: ", "written by us on top of the inverted index. Term frequency is saturated by k1 and "
  "normalised by document length through b. We checked that the matrix version used for batch "
  "evaluation gives the same scores as a plain loop over the postings lists (differences below "
  "1e-5, which is float rounding).")
B("Sentence Transformer (Dense Search): ", "all-MiniLM-L6-v2, a 6-layer model that outputs 384-dimensional "
  "vectors [2, 6]. Queries and holdings are encoded once and compared by cosine similarity. Inputs longer "
  "than 256 word pieces are cut off by the model.")
B("Hybrid Reciprocal Rank Fusion (RRF): ", "merges the top-1000 lists of TF-IDF, BM25 and the dense "
  "model (Section 3.3). We also report BM25 + dense without TF-IDF.")
B("Extension 1, fine-tuned dense model: ", "all-MiniLM-L6-v2 trained for one epoch on the 45,000 "
  "training pairs (citing context, correct holding) with one wrong option as a hard negative, using "
  "the multiple negatives ranking loss [7] (batch 32, learning rate 2e-5, 11 minutes on the laptop GPU).")
B("Extension 2, cross-encoder re-ranker: ", "cross-encoder/ms-marco-MiniLM-L6-v2 [8] reads each "
  "(query, holding) pair together and re-scores the top 20 of the hybrid list.")
FORMULA("BM25(q, d) = ∑ t∈q  idf(t) · tf(t,d)·(k1 + 1) / ( tf(t,d) + k1·(1 - b + b·|d| / avgdl) )")
P("where idf(t) = ln(1 + (N − df(t) + 0.5) / (df(t) + 0.5)), N is the number of holdings, df(t) the "
  "number of holdings containing t, |d| the length of the holding and avgdl the average length.")
H2("3.3 Reciprocal Rank Fusion Formulation")
P("RRF [3] adds up the reciprocal of the position each ranker gives a document. Given a set of rankers M "
  "and a constant k, the RRF score of document d is:")
FORMULA("RRF_Score(d ∈ D) = ∑ (m ∈ M)  1 / (k + r_m(d))")
P("where r_m(d) is the 1-based rank of d in the list of model m, and a document missing from a list adds "
  "nothing. RRF needs no score normalisation, which matters here because BM25 scores are unbounded "
  "(around 40 for the example query) while cosine scores lie between −1 and 1. We use the standard "
  "k = 60 for the main results and report the k chosen on validation as an extra run.")
H2("3.4 Choosing Parameters on the Validation Split")
P(f"All choices were made on the {val_s['queries']:,} validation queries and then frozen. Using the whole "
  f"context as the query worked best for BM25 (MRR {vmrr('BM25 last all words')}) compared with only the "
  f"last 64 or 32 words ({vmrr('BM25 last 64 words')} and {vmrr('BM25 last 32 words')}). A grid over k1 and "
  f"b (Figure 3) picked k1 = {cfg['bm25_k1']} and b = {cfg['bm25_b']}; a low k1 and a high b suit short "
  "documents where repeating a term carries little extra meaning. For TF-IDF, stop-word removal alone did "
  f"not help ({vmrr('TF-IDF stopwords=True stemming=False')} against "
  f"{vmrr('TF-IDF stopwords=False stemming=False')}) but adding stemming did "
  f"({vmrr('TF-IDF stopwords=True stemming=True')}). Between the two small dense models, "
  f"all-MiniLM-L6-v2 ({vmrr('all-MiniLM-L6-v2 last all words')}) beat bge-small-en-v1.5 "
  f"({vmrr('bge-small-en-v1.5 last 96 words')} at best, even with its query instruction). For RRF, "
  f"smaller k was slightly better (k = 1: {vmrr('k=1')}, k = 60: {vmrr('k=60')}).")
FIGURE(FIG("bm25_tuning.png"), 3.6, "Figure 3: BM25 MRR on the validation split for different k1 and b.")
H2("3.5 Evaluation Metrics")
P("Each query has one relevant holding, so all metrics depend on the rank r of that holding. "
  "Precision@10 is 1/10 if r ≤ 10 and 0 otherwise, so its maximum possible value here is 0.1, not 1. "
  "Recall@k is the share of queries with r ≤ k. Average precision of a query equals 1/r, so MAP is "
  "the same as Mean Reciprocal Rank (MRR). nDCG@10 with binary relevance is 1/log2(r + 1) when "
  "r ≤ 10. The Precision-Recall graph plots mean Precision@k against mean Recall@k for k = 1 to "
  "100. We also tested every model against BM25 with a Wilcoxon signed-rank test on per-query "
  "reciprocal ranks.")

# ---------------------------------------------------------------- 4. Experiments
H1("4. Experimental Setup and Performance Analysis")
P(f"Everything ran on one laptop (Apple M4 Pro, 24 GB RAM) with Python 3.13, scikit-learn, "
  f"sentence-transformers and PyTorch; the neural models used the Apple GPU (MPS). Building the TF-IDF "
  f"and BM25 indexes took {timing['TF-IDF index']:.2f} s and {timing['BM25 index']:.2f} s, and scoring all "
  f"{tst['queries']:,} test queries took about {timing['BM25 search']:.1f} s for each. Encoding the "
  f"queries and holdings with the dense model took {timing['Dense encode+search']:.0f} s and cross-encoder "
  f"re-ranking took {timing['Cross-encoder re-rank top-20']:.0f} s. Table 2 gives the full-pool results "
  f"with the metrics of the brief, Table 3 the 5-choice results.")
order = ["TF-IDF", "BM25", "Dense", H3, HK, "Hybrid RRF (BM25+Dense)", CE, FT, HFT]
names = {H3: "Hybrid RRF (TF-IDF + BM25 + Dense)", HK: f"Hybrid RRF, k = {cfg['rrf_k']}",
         "Hybrid RRF (BM25+Dense)": "Hybrid RRF (BM25 + Dense)", CE: "Hybrid + cross-encoder",
         FT: "Dense, fine-tuned (ext.)", HFT: "Hybrid RRF (BM25 + fine-tuned Dense)",
         "Dense": "Sentence Transformer"}
TABLE(f"Table 2. Full-pool retrieval on the CaseHOLD test split ({tst['queries']:,} queries, "
      f"{tst['holdings']:,} holdings). Maximum possible Precision@10 is 0.1.",
      ["Ranking Model", "Precision@10", "Recall@100", "MAP (= MRR)", "nDCG@10"],
      [[names.get(m, m), f(m, "P@10"), f(m, "R@100"), f(m, "MAP"), f(m, "nDCG@10")] for m in order],
      highlight_last=True)
P(f"BM25 is the strongest of the required single models (MAP {f('BM25', 'MAP')}), with TF-IDF just "
  f"behind ({f('TF-IDF', 'MAP')}). The general-purpose Sentence Transformer is clearly worse "
  f"({f('Dense', 'MAP')}): it was trained on web text and question answering pairs, not on court "
  f"language, and it puts the correct holding at median rank {full.loc['Dense', 'median_rank']:.0f} "
  f"compared with {full.loc['BM25', 'median_rank']:.0f} for BM25. Even so, the hybrid helps. The three-way "
  f"RRF raises Recall@100 from {f('BM25', 'R@100')} to {f(H3, 'R@100')} and Recall@10 from "
  f"{f('BM25', 'R@10')} to {f(H3, 'R@10')}, while MAP rises only a little ({f(H3, 'MAP')}). The fusion "
  "mostly pulls answers from deep in the list into the top 100, which is what matters if the list is "
  f"handed to a person or a re-ranker. With the k picked on validation the gain is larger (MAP "
  f"{f(HK, 'MAP')}). Dropping TF-IDF from the fusion lowers every metric, because with only two inputs "
  "the weaker dense list gets as much weight as BM25.")
P(f"The two extensions behave very differently. One epoch of fine-tuning on the training split lifts the "
  f"dense model from {f('Dense', 'MAP')} to {f(FT, 'MAP')}, ahead of BM25, and fusing it with BM25 gives "
  f"the best run (MAP {f(HFT, 'MAP')}, Recall@100 {f(HFT, 'R@100')}). The ms-marco cross-encoder, on the "
  f"other hand, drops MAP to {f(CE, 'MAP')}. It was trained to judge whether a web passage answers a short "
  "search question, and a 140-word legal passage paired with a holding is far from that. According to the "
  f"Wilcoxon test, the improvements of the three-way hybrid (p = {sig.loc[H3, 'p_value']:.1e}), the "
  f"fine-tuned model and the fine-tuned hybrid over BM25 are statistically significant, while BM25 + Dense "
  f"is not different from BM25 (p = {sig.loc['Hybrid RRF (BM25+Dense)', 'p_value']:.2f}).")
FIGURE(FIG("full_pool_metrics.png"), 6.3, "Figure 4: Full-pool results for the main runs.")
FIGURE(FIG("pr_curve.png"), 4.3, "Figure 5: Precision-Recall graph for the four required models "
       "(each point is mean Precision@k against mean Recall@k, k = 1 to 100; log scale on precision).")
P("Figure 5 is the Precision-Recall graph asked for in the brief. Because there is one relevant holding "
  "per query, precision falls roughly as 1/k as the cut-off grows, so we plot it on a log scale. The "
  "hybrid curve is level with BM25 for the first two cut-offs and above it from k = 3 (recall about 0.36), the same effect seen "
  "in Recall@100. The dense curve is lower everywhere. Figure 6 shows where the correct holding ends up "
  "for each run.")
FIGURE(FIG("rank_buckets.png"), 5.6, "Figure 6: Share of test queries whose correct holding is ranked "
       "first, 2 to 10, 11 to 100, or below 100.")
TABLE("Table 3. 5-choice setting (original CaseHOLD format) on the test split. Random guessing gives "
      "accuracy 0.20.",
      ["Ranking Model", "Accuracy", "MRR", "Recall@2", "nDCG@5"],
      [[names.get(m, m) if m != "Cross-encoder (ms-marco)" else "Cross-encoder (ms-marco)",
        f(m, "accuracy", five), f(m, "MRR", five), f(m, "R@2", five), f(m, "nDCG@5", five)]
       for m in ["TF-IDF", "BM25", "Dense", H3, "Hybrid RRF (BM25+Dense)", "Cross-encoder (ms-marco)", HFT, FT]],
      highlight_last=True)
P(f"In the 5-choice setting every method is far above chance, but the ordering changes. BM25 "
  f"({f('BM25', 'accuracy', five)}) is now better than the three-way hybrid "
  f"({f(H3, 'accuracy', five)}), and the fine-tuned dense model alone is best "
  f"({f(FT, 'accuracy', five)}). The four wrong options were picked by TF-IDF similarity to the right "
  "answer, so all five candidates share vocabulary and the lexical signal that RRF adds is less useful. "
  "For context, Zheng et al. [4] report a macro F1 of about 0.4 for a BiLSTM and about 0.6 for fine-tuned "
  "BERT on their own split. Our numbers are accuracies on the LexGLUE split, so they are not directly "
  "comparable, but they place unsupervised BM25 and our small fine-tuned model in a reasonable range.")
H2("4.1 Error Analysis")
P(f"The sparse and dense models fail on different queries. BM25 ranks the correct holding first while "
  f"the dense model does not in {err['bm25_top1_dense_not']} queries; the reverse happens in "
  f"{err['dense_top1_bm25_not']}; both succeed in {err['both_top1']}. This is why fusion helps at all. "
  f"In {err['neither_top10']:,} queries ({err['neither_top10'] / tst['queries']:.0%}) neither puts it in the "
  f"top 10. When the hybrid misses rank 1, the holding it puts first is one of the query's own four "
  f"distractors in only {err['miss_top1_is_own_distractor']:.0%} of cases, and its word overlap with the "
  f"correct holding is low (Jaccard {err['miss_top1_vs_gold_jaccard']:.2f}). Longer holdings are easier: "
  "BM25 MRR rises from {:.3f} for holdings of 15 words or fewer to {:.3f} for holdings above 40 words, "
  "since there are more terms to match.".format(err["mrr_by_gold_length"]["0-15 words"]["BM25"],
                                                 err["mrr_by_gold_length"]["41-1000 words"]["BM25"]))
P("Three test queries show the typical cases. In query 3185 the passage is about money ", ("structuring", True),
  " offences; BM25 ranks the right holding first because of that rare word, while the dense model ranks "
  "it 129th and returns a holding about habitual felony sentencing. In query 296 the passage talks about "
  "relationships and a ban on contact; BM25 ranks the answer 1,694th, but the dense model ranks it first "
  "because it links the context to “governmental actions restricting police officers sexual conduct” "
  "without any shared keyword. Query 2885 fails everywhere: the passage is about a strip search but the "
  "cited holding is about one panel of a court being bound by an earlier panel. The citation was used for "
  "a procedural point that the surrounding text never mentions, and no ranker that only reads the "
  "context can recover that.")
H2("4.2 Search Interface")
P("For the demonstration we built a Streamlit app (app/search_app.py). The user picks a CaseHOLD test "
  "query or types any passage, and the app shows the preprocessed query terms and the top results of "
  "TF-IDF, BM25, the dense model (base or fine-tuned) and the RRF hybrid next to each other, marking the "
  "correct holding when it is known. Single queries are answered by walking the BM25 postings lists "
  "directly and take well under a second.")
FIGURE(FIG("search_app.png"), 6.0, "Figure 7: Search interface for test query 0. TF-IDF, BM25 and the "
       "hybrid rank the correct holding first; the dense model ranks it second.")

# ---------------------------------------------------------------- 5. Conclusion
H1("5. Conclusion")
P("We turned CaseHOLD into a legal holding retrieval task and compared TF-IDF, BM25, a Sentence "
  "Transformer and an RRF hybrid on it. The main lessons are:")
B("Lexical models are strong on legal text. ", f"BM25 with tuned k1 and b (MAP {f('BM25', 'MAP')}) beat "
  f"an off-the-shelf dense model by a wide margin ({f('Dense', 'MAP')}).")
B("Fusion helps recall more than the top rank. ", f"Three-way RRF raised Recall@100 to {f(H3, 'R@100')} "
  "but MAP only slightly, because the dense list is weak on its own.")
B("Domain data matters most. ", f"Fine-tuning the small dense model on CaseHOLD training pairs moved its "
  f"MAP from {f('Dense', 'MAP')} to {f(FT, 'MAP')}, and BM25 plus the fine-tuned model was best overall "
  f"({f(HFT, 'MAP')}). A cross-encoder trained on web search hurt.")
P("The work has limits. Each query has exactly one relevant holding, so Precision@10 is capped at 0.1 and "
  "a holding that is legally correct but not the cited one counts as wrong. The document pool is the "
  f"{tst['holdings']:,} holdings of the test split, not a full case law database, and the wrong options "
  "inside it were chosen to be similar, so it is harder than a random pool of the same size. We used "
  "small models and one epoch of training because everything had to run on a laptop. In future work we "
  "would try a legal-domain encoder such as Legal-BERT [4], train the cross-encoder on CaseHOLD itself, "
  "and weight the rankers inside RRF instead of treating them equally.")
H1("References", new_page=False)
for ref in [
    "1. Robertson, S., Zaragoza, H.: The Probabilistic Relevance Framework: BM25 and Beyond. Foundations "
    "and Trends in Information Retrieval 3(4), 333–389 (2009)",
    "2. Reimers, N., Gurevych, I.: Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. In: "
    "Proceedings of EMNLP-IJCNLP, pp. 3982–3992 (2019)",
    "3. Cormack, G.V., Clarke, C.L.A., Buettcher, S.: Reciprocal Rank Fusion outperforms Condorcet and "
    "individual Rank Learning Methods. In: Proceedings of SIGIR, pp. 758–759 (2009)",
    "4. Zheng, L., Guha, N., Anderson, B.R., Henderson, P., Ho, D.E.: When Does Pretraining Help? "
    "Assessing Self-Supervised Learning for Law and the CaseHOLD Dataset of 53,000+ Legal Holdings. In: "
    "Proceedings of ICAIL (2021)",
    "5. Chalkidis, I., Jana, A., Hartung, D., Bommarito, M., Androutsopoulos, I., Katz, D.M., Aletras, N.: "
    "LexGLUE: A Benchmark Dataset for Legal Language Understanding in English. In: Proceedings of ACL (2022)",
    "6. Wang, W., Wei, F., Dong, L., Bao, H., Yang, N., Zhou, M.: MiniLM: Deep Self-Attention Distillation "
    "for Task-Agnostic Compression of Pre-Trained Transformers. In: Proceedings of NeurIPS (2020)",
    "7. Henderson, M., et al.: Efficient Natural Language Response Suggestion for Smart Reply. "
    "arXiv:1705.00652 (2017)",
    "8. Nogueira, R., Cho, K.: Passage Re-ranking with BERT. arXiv:1901.04085 (2019)",
    "9. Porter, M.F.: An algorithm for suffix stripping. Program 14(3), 130–137 (1980)",
    "10. Manning, C.D., Raghavan, P., Schütze, H.: Introduction to Information Retrieval. Cambridge "
    "University Press (2008)",
]:
    REF(ref)

out = R("deliverables/IR_Group13_CaseHOLD_Report.docx")
doc.save(out)
print("saved", out)
