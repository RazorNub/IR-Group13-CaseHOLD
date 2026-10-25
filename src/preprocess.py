"""Text cleaning, tokenisation, stop-word removal and stemming."""
import re

from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# 91% of holdings start with "holding that", so these words carry no signal.
# The rest are citation words (v., see, e.g., id.) that appear in every context.
LEGAL_STOPWORDS = {"holding", "held", "v", "see", "eg", "id", "cf", "supra", "citing"}
STOPWORDS = set(ENGLISH_STOP_WORDS) | LEGAL_STOPWORDS

_stemmer = PorterStemmer()
_stem_cache = {}


def stem(word):
    if word not in _stem_cache:
        _stem_cache[word] = _stemmer.stem(word)
    return _stem_cache[word]


def tokenize(text, remove_stopwords=True, use_stemming=True):
    text = text.lower().replace("<holding>", " ")
    # e.g. -> eg, u.s.c. -> usc, so abbreviations stay one token
    text = re.sub(r"(?<=\w)\.(?=\w)", "", text)
    tokens = re.findall(r"[a-z0-9]+", text)
    # drop single letters and anything with a digit (reporter cites like 81, 2d, 1196)
    tokens = [t for t in tokens if len(t) > 1 and not any(c.isdigit() for c in t)]
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    if use_stemming:
        tokens = [stem(t) for t in tokens]
    return tokens


if __name__ == "__main__":
    print(tokenize("See, e.g., Vector Pipeline, L.P., v. 68.55 Acres of Land, 157 F.Supp.2d 949 (<HOLDING>)"))
    print(tokenize("holding that stigma damages were properly included in calculation of severance damages"))
