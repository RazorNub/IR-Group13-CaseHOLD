"""Optional extension: fine-tune the dense model on the CaseHOLD TRAIN split.

Training pairs are (citing context, correct holding). One of the 4 wrong
holdings is added as a hard negative. The loss is MultipleNegativesRankingLoss:
for each context, the correct holding has to score higher than its hard
negative and every other holding in the batch.
Saves the model to models/finetuned-dense.
"""
import json
import os
import random
import sys

os.environ.setdefault("HF_HOME", "data/hf_cache")
sys.path.insert(0, os.path.dirname(__file__))

from datasets import Dataset, load_dataset
from sentence_transformers import (SentenceTransformer, SentenceTransformerTrainer,
                                   SentenceTransformerTrainingArguments)
from sentence_transformers.sentence_transformer import losses
from sentence_transformers.training_args import BatchSamplers

from data import query_window
from dense import device

OUT = "models/finetuned-dense"


def main(n_train=None, epochs=1, batch_size=32):
    cfg = json.load(open("results/chosen_settings.json"))
    random.seed(13)
    raw = load_dataset("coastalcph/lex_glue", "case_hold", split="train")
    if n_train:
        raw = raw.select(range(n_train))

    anchors, positives, negatives = [], [], []
    for ex in raw:
        label = int(ex["label"])
        wrong = [e for i, e in enumerate(ex["endings"]) if i != label]
        anchors.append(query_window(ex["context"], cfg["dense_query_window"]))
        positives.append(ex["endings"][label])
        negatives.append(random.choice(wrong))
    train = Dataset.from_dict({"anchor": anchors, "positive": positives, "negative": negatives})

    model = SentenceTransformer(cfg["dense_model"], device=device())
    model.max_seq_length = 256
    args = SentenceTransformerTrainingArguments(
        output_dir="models/checkpoints",
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        learning_rate=2e-5,
        warmup_ratio=0.1,
        batch_sampler=BatchSamplers.NO_DUPLICATES,  # same holding twice in a batch would be a false negative
        save_strategy="no",
        logging_steps=100,
        seed=13,
        report_to=[],
    )
    trainer = SentenceTransformerTrainer(model=model, args=args, train_dataset=train,
                                         loss=losses.MultipleNegativesRankingLoss(model))
    trainer.train()
    model.save(OUT)
    print("saved to", OUT)


if __name__ == "__main__":
    main(n_train=int(sys.argv[1]) if len(sys.argv) > 1 else None)
