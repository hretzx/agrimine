"""
algorithms/apriori.py
---------------------
Apriori association-rule mining written from scratch (no scikit-learn, no mlxtend).

Vocabulary
    item        one fact about a row, e.g. "rainfall=high", "ph=acidic", "crop=rice"
    transaction one row of the dataset = the set of items that are true for it
    itemset     a group of items, e.g. {rainfall=high, humidity=high}
    support     fraction of rows that contain the whole itemset
    confidence  of the rows with the antecedent, the fraction that also have the
                consequent:   support(A and C) / support(A)
    lift        confidence divided by how common the consequent is overall:
                lift > 1 means A and C appear together MORE than chance

How the algorithm works (the "Apriori property")
    If an itemset is frequent, every subset of it must be frequent too. So we
        1. find frequent single items,
        2. combine them into candidate pairs, count them, keep the frequent ones,
        3. combine those into candidate triples ... and so on,
    and we can discard (prune) any candidate that has an infrequent subset
    without even counting it.

Speed trick: every item is stored as one big integer whose bit r is 1 when row r
contains the item ("bitset"). The rows containing BOTH items are then just
(mask_a & mask_b) and the number of such rows is the number of 1-bits.
"""
from itertools import combinations

import numpy as np
import pandas as pd


def _popcount(x: int) -> int:
    """Count the 1-bits of an integer (= how many rows contain the itemset)."""
    return x.bit_count() if hasattr(x, "bit_count") else bin(x).count("1")


def make_item_masks(labels: pd.DataFrame) -> tuple[list[str], list[int]]:
    """
    Turn a table of category labels into items.
    Each column/value pair becomes an item named "column=value" and gets a bitset
    saying which rows contain it.
    Returns (item_names, item_masks) in the same order.
    """
    names, masks = [], []
    for col in labels.columns:
        for value in sorted(labels[col].unique()):
            present = (labels[col].to_numpy() == value)
            # pack the True/False column into bytes, then into one Python integer
            masks.append(int.from_bytes(np.packbits(present).tobytes(), "big"))
            names.append(f"{col}={value}")
    return names, masks


def _join_and_prune(prev_level: list[tuple], prev_set: set):
    """
    Build candidate itemsets of size k+1 from the frequent itemsets of size k.
    JOIN : two itemsets that agree on all but their last item are merged.
    PRUNE: keep the candidate only if ALL of its size-k subsets were frequent.
    (Itemsets are sorted tuples of item numbers, so equal prefixes sit together.)
    """
    prev_level = sorted(prev_level)
    for i, a in enumerate(prev_level):
        for b in prev_level[i + 1:]:
            if a[:-1] != b[:-1]:
                break  # sorted order: no later itemset can share this prefix
            cand = a + (b[-1],)
            if all(sub in prev_set for sub in combinations(cand, len(cand) - 1)):
                yield cand


def apriori(item_masks: list[int], n_rows: int, min_support: float,
            max_len: int = 4) -> dict[tuple, int]:
    """
    Find all frequent itemsets.
    Returns {itemset (sorted tuple of item numbers): number of rows containing it}.
    Support of an itemset = that count / n_rows.
    """
    min_count = int(np.ceil(min_support * n_rows - 1e-9))   # rows needed to be "frequent"
    frequent: dict[tuple, int] = {}

    # Level 1: single items
    level_masks: dict[tuple, int] = {}
    for i, m in enumerate(item_masks):
        count = _popcount(m)
        if count >= min_count:
            frequent[(i,)] = count
            level_masks[(i,)] = m

    # Level k+1: join, prune, count
    size = 1
    while level_masks and size < max_len:
        next_masks: dict[tuple, int] = {}
        for cand in _join_and_prune(list(level_masks), set(level_masks)):
            mask = level_masks[cand[:-1]] & item_masks[cand[-1]]   # rows with ALL items
            count = _popcount(mask)
            if count >= min_count:
                frequent[cand] = count
                next_masks[cand] = mask
        level_masks = next_masks
        size += 1
    return frequent


def association_rules(frequent: dict[tuple, int], item_names: list[str], n_rows: int,
                      min_confidence: float, consequent_prefix: str | None = None) -> pd.DataFrame:
    """
    Build rules "antecedent -> consequent" from the frequent itemsets.
    Each rule has a single-item consequent. If consequent_prefix is given (for
    example "crop="), only rules whose consequent starts with it are kept.
    Columns: Antecedent, Consequent, Support, Confidence, Lift.
    """
    rows = []
    for itemset, count in frequent.items():
        if len(itemset) < 2:
            continue
        for c in itemset:
            consequent = item_names[c]
            if consequent_prefix and not consequent.startswith(consequent_prefix):
                continue
            antecedent = tuple(i for i in itemset if i != c)
            confidence = count / frequent[antecedent]   # antecedent is frequent too (Apriori property)
            if confidence < min_confidence:
                continue
            lift = confidence / (frequent[(c,)] / n_rows)
            rows.append({
                "Antecedent": " AND ".join(item_names[i] for i in antecedent),
                "Consequent": consequent,
                "Support": count / n_rows,
                "Confidence": confidence,
                "Lift": lift,
            })
    columns = ["Antecedent", "Consequent", "Support", "Confidence", "Lift"]
    rules = pd.DataFrame(rows, columns=columns)
    return rules.sort_values(["Lift", "Confidence", "Support"], ascending=False).reset_index(drop=True)
