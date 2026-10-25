"""Draws every chart used in the report and the slides into figures/."""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

os.environ.setdefault("HF_HOME", "data/hf_cache")
sys.path.insert(0, os.path.dirname(__file__))

from data import load_split
from metrics import pr_points

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.3,
    "savefig.dpi": 200, "savefig.bbox": "tight",
})
NAVY, TEAL, GREY, RED, GOLD = "#1F3864", "#2E7D7A", "#8C8C8C", "#B03A2E", "#C58B00"
COLORS = {"TF-IDF": GREY, "BM25": NAVY, "Dense": TEAL, "Dense (fine-tuned)": "#5B8E3E",
          "Hybrid RRF (TF-IDF+BM25+Dense)": RED, "Hybrid RRF (BM25+Dense)": GOLD,
          "Hybrid RRF (BM25+Dense fine-tuned)": "#6A4C93", "Hybrid + cross-encoder re-rank": "#444444",
          "Hybrid RRF (TF-IDF+BM25+Dense, k=1)": "#D98880", "Cross-encoder (ms-marco)": "#444444"}
SHORT = {"Hybrid RRF (TF-IDF+BM25+Dense)": "RRF (3-way)", "Hybrid RRF (TF-IDF+BM25+Dense, k=1)": "RRF (3-way, k=1)", "Hybrid RRF (BM25+Dense)": "RRF (BM25+Dense)",
         "Hybrid RRF (BM25+Dense fine-tuned)": "RRF (BM25+FT dense)",
         "Hybrid + cross-encoder re-rank": "RRF + cross-enc.", "Dense (fine-tuned)": "Dense (FT)",
         "Cross-encoder (ms-marco)": "Cross-enc."}
OUT = "figures"
# the runs shown in the crowded charts; every run is still in the tables
MAIN = ["TF-IDF", "BM25", "Dense", "Hybrid RRF (TF-IDF+BM25+Dense)", "Dense (fine-tuned)",
        "Hybrid RRF (BM25+Dense fine-tuned)"]


def short(n):
    return SHORT.get(n, n)


def dataset_figures():
    test = load_split("test")
    ctx = [len(q.replace("<HOLDING>", "").split()) for q in test.queries]
    hold = [len(h.split()) for h in test.corpus]
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
    ax[0].hist(ctx, bins=30, color=NAVY)
    ax[0].set(title="Citing context (query) length", xlabel="words", ylabel="queries")
    ax[1].hist(hold, bins=40, range=(0, 100), color=TEAL)
    ax[1].set(title="Holding (document) length", xlabel="words", ylabel="holdings")
    fig.savefig(f"{OUT}/dataset_lengths.png"); plt.close(fig)

    labels = pd.Series(test.labels).value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(4.2, 3))
    ax.bar([f"choice {i}" for i in labels.index], labels.values, color=NAVY)
    ax.set(title="Position of the correct holding (test)", ylabel="queries")
    fig.savefig(f"{OUT}/label_distribution.png"); plt.close(fig)


def bar_full_pool(df):
    df = df[df["model"].isin(MAIN)].set_index("model").loc[MAIN].reset_index()
    metrics = ["MRR", "nDCG@10", "R@10", "R@100"]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    x = np.arange(len(metrics))
    w = 0.8 / len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        ax.bar(x + i * w - 0.4 + w / 2, row[metrics], w, label=short(row["model"]),
               color=COLORS.get(row["model"], GREY))
    ax.set_xticks(x, metrics)
    ax.set(ylim=(0, 1), title="Full-pool retrieval on the CaseHOLD test split")
    ax.legend(ncol=6, fontsize=8, loc="upper center", frameon=False, bbox_to_anchor=(0.5, -0.1))
    fig.savefig(f"{OUT}/full_pool_metrics.png"); plt.close(fig)


def pr_curves(ranks, names, fname, title):
    fig, ax = plt.subplots(figsize=(5.6, 4))
    for n in names:
        _, p, r = pr_points(ranks[f"full|{n}"], 100)
        ax.plot(r, p, label=short(n), color=COLORS.get(n, GREY), lw=1.8)
    ax.set(xlabel="Recall@k", ylabel="Precision@k", title=title, yscale="log")
    ax.legend(fontsize=8, frameon=False)
    fig.savefig(f"{OUT}/{fname}"); plt.close(fig)


def recall_at_k(ranks, names):
    fig, ax = plt.subplots(figsize=(5.6, 4))
    ks = np.arange(1, 101)
    for n in names:
        r = ranks[f"full|{n}"]
        ax.plot(ks, [np.mean(r <= k) for k in ks], label=short(n), color=COLORS.get(n, GREY), lw=1.8)
    ax.set(xscale="log", xlabel="k (cut-off)", ylabel="Recall@k", title="Recall@k, full pool", ylim=(0, 1))
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    fig.savefig(f"{OUT}/recall_at_k.png"); plt.close(fig)


def five_choice_bar(df5):
    df5 = df5.sort_values("accuracy")
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.barh([short(m) for m in df5["model"]], df5["accuracy"],
            color=[COLORS.get(m, "#444444") for m in df5["model"]])
    ax.axvline(0.2, color="black", ls="--", lw=1)
    ax.text(0.21, len(df5) - 0.45, "random guess (0.20)", fontsize=8)
    for i, v in enumerate(df5["accuracy"]):
        ax.text(v + 0.005, i, f"{v:.3f}", va="center", fontsize=8)
    ax.set(xlim=(0, 1), ylim=(-0.6, len(df5) + 0.1), xlabel="accuracy (correct holding ranked first)",
           title="5-choice setting (CaseHOLD multiple choice)")
    ax.grid(axis="y", visible=False)
    fig.savefig(f"{OUT}/five_choice_accuracy.png"); plt.close(fig)


def rank_buckets(ranks, names):
    buckets = [(1, 1, "rank 1"), (2, 10, "2-10"), (11, 100, "11-100"), (101, np.inf, ">100")]
    fig, ax = plt.subplots(figsize=(7, 3.4))
    left = np.zeros(len(names))
    shades = [NAVY, TEAL, GOLD, GREY]
    for (lo, hi, lab), c in zip(buckets, shades):
        vals = np.array([np.mean((ranks[f"full|{n}"] >= lo) & (ranks[f"full|{n}"] <= hi)) for n in names])
        ax.barh([short(n) for n in names], vals, left=left, color=c, label=lab)
        left += vals
    ax.set(xlim=(0, 1), xlabel="share of test queries", title="Where the correct holding ends up")
    ax.legend(ncol=4, fontsize=8, frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.38))
    ax.grid(axis="y", visible=False)
    fig.savefig(f"{OUT}/rank_buckets.png"); plt.close(fig)


def bm25_heatmap():
    v = pd.read_csv("results/validation_tuning.csv")
    v = v[v["group"] == "bm25"].copy()
    v["k1"] = v["setting"].str.extract(r"k1=([\d.]+)").astype(float)
    v["b"] = v["setting"].str.extract(r"b=([\d.]+)").astype(float)
    grid = v.pivot(index="k1", columns="b", values="MRR")
    fig, ax = plt.subplots(figsize=(4.6, 3.4))
    im = ax.imshow(grid.values, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(grid.columns)), grid.columns)
    ax.set_yticks(range(len(grid.index)), grid.index)
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            val = grid.values[i, j]
            ax.text(j, i, f"{val:.3f}", ha="center", va="center", fontsize=8,
                    color="white" if val > grid.values.mean() else "black")
    ax.set(xlabel="b", ylabel="k1", title="BM25 MRR on validation")
    ax.grid(False)
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.savefig(f"{OUT}/bm25_tuning.png"); plt.close(fig)


def pipeline_diagram():
    fig, ax = plt.subplots(figsize=(10, 3.9))
    ax.set_xlim(0, 100); ax.set_ylim(0, 40); ax.axis("off")

    def box(x, y, w, h, text, fc="white"):
        ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec=NAVY, lw=1.2))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.5)

    def arrow(x1, y1, x2, y2):
        ax.annotate("", (x2, y2), (x1, y1), arrowprops=dict(arrowstyle="->", color=NAVY, lw=1.1))

    # inputs
    box(0.5, 14, 13, 12, "Query\n(citing context)\n+\n13,297\nholdings", "#E8EEF6")
    # sparse lane (top)
    ax.text(16, 38.2, "sparse path", fontsize=8, color=GREY)
    box(16, 27, 16, 10, "Clean, tokenise,\nstop words,\nPorter stem")
    box(35, 27, 15, 10, "Inverted index\nterm \u2192 postings")
    box(53, 32, 14, 6, "TF-IDF cosine")
    box(53, 25, 14, 6, "BM25")
    # dense lane (bottom)
    ax.text(16, 0.3, "dense path", fontsize=8, color=GREY)
    box(16, 3, 16, 10, "Raw text\n(no stemming)")
    box(35, 3, 15, 10, "MiniLM encoder\n384-d vectors")
    box(53, 5, 14, 6, "Cosine similarity")
    # fusion and output
    box(71, 15, 12, 10, "RRF fusion\nk = 60", "#F6E8E6")
    box(86, 26, 13.5, 10, "Cross-encoder\nre-rank top 20\n(extra)")
    box(86, 4, 13.5, 10, "Ranked holdings\n+ evaluation", "#E8EEF6")

    arrow(13.5, 23, 16, 30); arrow(13.5, 17, 16, 9)
    arrow(32, 32, 35, 32); arrow(32, 8, 35, 8)
    arrow(50, 33, 53, 35); arrow(50, 31, 53, 28); arrow(50, 8, 53, 8)
    arrow(67, 35, 71, 23); arrow(67, 28, 71, 21); arrow(67, 8, 71, 17)
    arrow(83, 22, 86, 29); arrow(83, 18, 86, 10)
    arrow(92.75, 26, 92.75, 14)
    fig.savefig(f"{OUT}/pipeline.png"); plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    full = pd.read_csv("results/test_full_pool.csv")
    five = pd.read_csv("results/test_five_choice.csv")
    ranks = dict(np.load("results/ranks.npz"))
    dataset_figures()
    pipeline_diagram()
    bar_full_pool(full)
    core = ["TF-IDF", "BM25", "Dense", "Hybrid RRF (TF-IDF+BM25+Dense)"]
    pr_curves(ranks, core, "pr_curve.png", "Precision-Recall (k = 1..100), test")
    pr_curves(ranks, list(full["model"]), "pr_curve_all.png", "Precision-Recall, all runs")
    recall_at_k(ranks, MAIN)
    five_choice_bar(five)
    rank_buckets(ranks, MAIN + ["Hybrid + cross-encoder re-rank"])
    bm25_heatmap()
    print(sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
