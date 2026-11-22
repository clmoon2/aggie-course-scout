"""Tokenizer, stopword list, and a deliberately conservative Porter stemmer.

The browser gets a line-for-line JavaScript copy in web/js/stemmer.js. Both
implement the same reduced suffix table, and tests/test_tokenizer.py checks
parity on a fixed word list so the two indexes cannot drift.
"""
from __future__ import annotations

import re

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset("""
a about above after again against all also am an and any are as at be because been
before being below between both but by can could did do does doing down during each
few for from further had has have having he her here hers herself him himself his how
i if in into is it its itself just me more most my myself no nor not now of off on once
only or other our ours ourselves out over own same she should so some such than that the
their theirs them themselves then there these they this those through to too under until
up very was we were what when where which while who whom why will with would you your
yours yourself yourselves
""".split())

VOWELS = set("aeiou")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _cons(w: str, i: int) -> bool:
    ch = w[i]
    if ch in VOWELS:
        return False
    if ch == "y":
        return i == 0 or not _cons(w, i - 1)
    return True


def _measure(stem: str) -> int:
    m = 0
    prev_v = False
    for i in range(len(stem)):
        c = _cons(stem, i)
        if c and prev_v:
            m += 1
        prev_v = not c
    return m


def _has_vowel(stem: str) -> bool:
    return any(not _cons(stem, i) for i in range(len(stem)))


def _cvc(w: str) -> bool:
    if len(w) < 3:
        return False
    return (not _cons(w, len(w) - 1) and _cons(w, len(w) - 2)
            and not _cons(w, len(w) - 3)
            and w[-1] not in "wxy")


STEP2 = [
    ("ational", "ate"), ("tional", "tion"), ("enci", "ence"), ("anci", "ance"),
    ("izer", "ize"), ("bli", "ble"), ("alli", "al"), ("entli", "ent"),
    ("eli", "e"), ("ousli", "ous"), ("ization", "ize"), ("ation", "ate"),
    ("ator", "ate"), ("alism", "al"), ("iveness", "ive"), ("fulness", "ful"),
    ("ousness", "ous"), ("aliti", "al"), ("iviti", "ive"), ("biliti", "ble"),
    ("logi", "log"),
]
STEP3 = [("icate", "ic"), ("ative", ""), ("alize", "al"), ("iciti", "ic"),
         ("ical", "ic"), ("ful", ""), ("ness", "")]
STEP4 = ["al", "ance", "ence", "er", "ic", "able", "ible", "ant", "ement",
         "ment", "ent", "ion", "ou", "ism", "ate", "iti", "ous", "ive", "ize"]


def stem(word: str) -> str:
    if len(word) <= 3 or not word.isalpha():
        return word
    w = word
    # Step 1a
    if w.endswith("sses"):
        w = w[:-2]
    elif w.endswith("ies"):
        w = w[:-2]
    elif w.endswith("ss"):
        pass
    elif w.endswith("s") and len(w) > 3:
        w = w[:-1]
    # Step 1b
    if w.endswith("eed"):
        if _measure(w[:-3]) > 0:
            w = w[:-1]
    elif w.endswith("ed") and _has_vowel(w[:-2]):
        w = w[:-2]
        if w.endswith(("at", "bl", "iz")):
            w += "e"
        elif len(w) > 1 and w[-1] == w[-2] and w[-1] not in "lsz":
            w = w[:-1]
        elif _measure(w) == 1 and _cvc(w):
            w += "e"
    elif w.endswith("ing") and _has_vowel(w[:-3]):
        w = w[:-3]
        if w.endswith(("at", "bl", "iz")):
            w += "e"
        elif len(w) > 1 and w[-1] == w[-2] and w[-1] not in "lsz":
            w = w[:-1]
        elif _measure(w) == 1 and _cvc(w):
            w += "e"
    # Step 1c
    if w.endswith("y") and _has_vowel(w[:-1]):
        w = w[:-1] + "i"
    # Step 2
    if len(w) > 4:
        for suf, rep in STEP2:
            if w.endswith(suf) and _measure(w[:-len(suf)]) > 0:
                w = w[:-len(suf)] + rep
                break
    # Step 3
    if len(w) > 4:
        for suf, rep in STEP3:
            if w.endswith(suf) and _measure(w[:-len(suf)]) > 0:
                w = w[:-len(suf)] + rep
                break
    # Step 4
    if len(w) > 5:
        for suf in STEP4:
            if w.endswith(suf):
                base = w[:-len(suf)]
                if _measure(base) > 1 and (suf != "ion" or base.endswith(("s", "t"))):
                    w = base
                break
    # Step 5
    if w.endswith("e"):
        base = w[:-1]
        m = _measure(base)
        if m > 1 or (m == 1 and not _cvc(base)):
            w = base
    if w.endswith("ll") and _measure(w) > 1:
        w = w[:-1]
    return w


def normalize_tokens(text: str) -> list[str]:
    out = []
    for token in tokenize(text):
        if token in STOPWORDS:
            continue
        s = stem(token)
        if s and s not in STOPWORDS:
            out.append(s)
    return out


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        print(arg, "->", " ".join(normalize_tokens(arg)))
