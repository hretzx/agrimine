"""
api/state.py
------------
Warm everything once at startup (the whole app trains in about 1 s; only the K-Means diagnostics take about 3.4 s, so they
run in a background thread). Nothing else is cached here: core/cache.py already remembers every result.
"""
import threading

from core import models
from core.advice import cluster_summary
from core.checks import backfill_predictions


def warm_up() -> dict:
    """Train the models the first requests need, fill in predictions for old rows, and start the slow job (silhouette for k = 2..10, used by the teacher pages only) in the background."""
    models.get_data()
    models.train_id3()
    models.train_naive_bayes()
    for k in (3, 4, 5):
        models.train_kmeans(k)
        models.kmeans_silhouette(k)
        cluster_summary(k)
    models.get_projection()
    models.crop_rules()
    filled = backfill_predictions()
    threading.Thread(target=models.kmeans_diagnostics, name="kmeans-diagnostics", daemon=True).start()
    return {"backfilled_checks": filled}
