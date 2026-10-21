"""
algorithms/fpgrowth.py
----------------------
Two more frequent-itemset miners written from scratch, FP-Growth and Eclat, plus
closed and maximal itemsets. They find EXACTLY the same frequent itemsets as Apriori
(algorithms/apriori.py), with the same item numbers, and return the same
{itemset (sorted tuple of item numbers): number of rows containing it}.

FP-GROWTH ("frequent pattern growth": no candidate generation)
 1. Count every item; drop the infrequent ones.
 2. Sort the items of every transaction from most to least frequent and insert it
    into a prefix tree (the FP-tree). Transactions that share a prefix share nodes,
    so the tree is a compressed copy of the data. A HEADER TABLE keeps, for every
    item, a chain linking all tree nodes of that item.
 3. For each item (least frequent first): follow its chain, collect the path from
    every node up to the root (its CONDITIONAL PATTERN BASE = "the transactions that
    contain this item"), build a small FP-tree from them and repeat (recursion).

ECLAT (vertical format)
    Instead of "row -> items" it stores "item -> rows that contain it" (a tid-set).
    The rows that contain an itemset are the INTERSECTION of the items' tid-sets, so
    it grows itemsets depth-first by intersecting. Here the tid-sets are the same
    bitsets the Apriori code uses, so an intersection is one '&' of two integers.

CLOSED and MAXIMAL itemsets (compact summaries of all frequent itemsets)
    closed   no superset has the SAME support     (keeps every support count)
    maximal  no superset is frequent at all       (smallest summary; loses counts)
    Every maximal itemset is closed, and every closed itemset is frequent.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.algorithms.apriori import _popcount


def make_transactions(labels: pd.DataFrame) -> tuple[list[str], list[tuple[int, ...]]]:
    """
    Turn a table of category labels into transactions (one per row).
    Item numbers follow make_item_masks() in apriori.py exactly (column by column,
    values sorted), so all three miners can be compared item for item.
    Returns (item_names, transactions as sorted tuples of item numbers).
    """
    names, index = [], {}
    for col in labels.columns:
        for value in sorted(labels[col].unique()):
            index[(col, value)] = len(names)
            names.append(f"{col}={value}")
    columns = list(labels.columns)
    transactions = [tuple(sorted(index[(c, v)] for c, v in zip(columns, row)))
                    for row in labels.itertuples(index=False, name=None)]
    return names, transactions


def _min_count(min_support: float, n_rows: int) -> int:
    """Rows an itemset needs to be frequent (identical rounding to apriori.py)."""
    return int(np.ceil(min_support * n_rows - 1e-9))


# =============================================================================
# FP-Growth
# =============================================================================
class _Node:
    """One FP-tree node: an item, how many transactions pass through it, and links."""
    __slots__ = ("item", "count", "parent", "children", "link")

    def __init__(self, item, parent):
        self.item, self.count, self.parent = item, 0, parent
        self.children: dict[int, _Node] = {}
        self.link: _Node | None = None       # next node with the same item (header-table chain)


class _FPTree:
    def __init__(self, weighted_paths: list[tuple[list[int], int]], min_count: int):
        # 1. item counts, keep frequent items only
        counts: dict[int, int] = {}
        for path, w in weighted_paths:
            for item in path:
                counts[item] = counts.get(item, 0) + w
        self.counts = {i: c for i, c in counts.items() if c >= min_count}
        # order: most frequent first (ties by item number, so the tree is repeatable)
        self.rank = {i: r for r, i in enumerate(sorted(self.counts, key=lambda i: (-self.counts[i], i)))}
        self.root = _Node(None, None)
        self.head: dict[int, _Node] = {}     # header table: item -> first node of its chain
        self.tail: dict[int, _Node] = {}     # last node of each chain (fast append)
        # 2. insert every (filtered, re-ordered) transaction
        for path, w in weighted_paths:
            items = sorted((i for i in path if i in self.counts), key=self.rank.__getitem__)
            self._insert(items, w)

    def _insert(self, items: list[int], weight: int) -> None:
        node = self.root
        for item in items:
            child = node.children.get(item)
            if child is None:
                child = _Node(item, node)
                node.children[item] = child
                if item in self.tail:            # append the new node to the item's chain
                    self.tail[item].link = child
                else:
                    self.head[item] = child
                self.tail[item] = child
            child.count += weight
            node = child

    def chain(self, item: int):
        """All nodes of one item, following the header-table links."""
        node = self.head.get(item)
        while node is not None:
            yield node
            node = node.link

    def conditional_pattern_base(self, item: int) -> list[tuple[list[int], int]]:
        """Prefix path (root side first) of every node of `item`, weighted by that node's count."""
        base = []
        for node in self.chain(item):
            path, parent = [], node.parent
            while parent is not None and parent.item is not None:
                path.append(parent.item)
                parent = parent.parent
            if path:
                base.append((path[::-1], node.count))
        return base


def fp_growth(transactions: list[tuple[int, ...]], min_support: float, max_len: int = 4) -> dict[tuple, int]:
    """
    Find all frequent itemsets with FP-Growth.
    Returns {itemset (sorted tuple of item numbers): number of rows containing it}.
    """
    min_count = _min_count(min_support, len(transactions))
    frequent: dict[tuple, int] = {}

    def grow(tree: _FPTree, suffix: tuple) -> None:
        # least frequent item first (bottom of the header table)
        for item in sorted(tree.counts, key=lambda i: (tree.counts[i], -i)):
            itemset = tuple(sorted(suffix + (item,)))
            frequent[itemset] = tree.counts[item]
            if len(itemset) < max_len:
                base = tree.conditional_pattern_base(item)
                if base:
                    sub = _FPTree(base, min_count)
                    if sub.counts:
                        grow(sub, suffix + (item,))

    grow(_FPTree([(list(t), 1) for t in transactions], min_count), ())
    return frequent


# =============================================================================
# Eclat
# =============================================================================
def eclat(item_masks: list[int], n_rows: int, min_support: float, max_len: int = 4) -> dict[tuple, int]:
    """
    Find all frequent itemsets with Eclat (depth-first tid-set intersection).
    Uses the same bitsets as apriori() and returns the same {itemset: count}.
    """
    min_count = _min_count(min_support, n_rows)
    frequent: dict[tuple, int] = {}
    singles = [(i, m, _popcount(m)) for i, m in enumerate(item_masks)]
    singles = [(i, m) for i, m, c in singles if c >= min_count]

    def extend(prefix: tuple, prefix_mask: int, candidates: list[tuple[int, int]]) -> None:
        for pos, (item, mask) in enumerate(candidates):
            both = prefix_mask & mask if prefix else mask      # rows with the prefix AND this item
            count = _popcount(both)
            if count < min_count:
                continue
            itemset = prefix + (item,)
            frequent[itemset] = count
            if len(itemset) < max_len:
                extend(itemset, both, candidates[pos + 1:])   # only items after this one: no duplicates

    extend((), 0, singles)
    return frequent


# =============================================================================
# Closed and maximal itemsets
# =============================================================================
def closed_itemsets(frequent: dict[tuple, int]) -> dict[tuple, int]:
    """
    Frequent itemsets with no superset of the same support.
    It is enough to look at supersets with ONE extra item: if any superset Y of X
    had the same support, then X + (any item of Y) would too, because support can
    only shrink as items are added.
    """
    not_closed = set()
    for itemset, count in frequent.items():
        if len(itemset) < 2:
            continue
        for drop in range(len(itemset)):
            sub = itemset[:drop] + itemset[drop + 1:]
            if frequent.get(sub) == count:
                not_closed.add(sub)
    return {s: c for s, c in frequent.items() if s not in not_closed}


def maximal_itemsets(frequent: dict[tuple, int]) -> dict[tuple, int]:
    """Frequent itemsets with no frequent superset (again one extra item is enough)."""
    has_superset = set()
    for itemset in frequent:
        for drop in range(len(itemset)):
            has_superset.add(itemset[:drop] + itemset[drop + 1:])
    return {s: c for s, c in frequent.items() if s not in has_superset}
