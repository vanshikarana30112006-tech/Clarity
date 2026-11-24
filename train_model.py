"""Train and save the Clarity regression model and validation results."""
import csv
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import LeaveOneGroupOut

from dataset import TOPICS
from preprocess import features, new_vectorizer


def train(root):
    topics = {topic["id"]: topic for topic in TOPICS}
    with (root / "dataset.csv").open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    vectorizer = new_vectorizer()
    training_features = []
    for row in rows:
        topic = topics[row["topic_id"]]
        values, _ = features(row["answer"], topic["reference"], topic["concepts"], vectorizer)
        training_features.append(values)
    x = np.asarray(training_features)
    y = np.asarray([int(row["expected_score"]) for row in rows])
    groups = np.asarray([row["topic_id"] for row in rows])
    predictions = np.zeros(len(rows))
    folds = LeaveOneGroupOut()
    for train_indices, test_indices in folds.split(x, y, groups):
        fold_model = Ridge(alpha=0.5).fit(x[train_indices], y[train_indices])
        predictions[test_indices] = np.clip(fold_model.predict(x[test_indices]), 0, 100)
    benchmark = {
        "samples": len(rows),
        "topics": len(set(groups)),
        "mae": round(mean_absolute_error(y, predictions), 2),
        "r2": round(r2_score(y, predictions), 3),
        "method": f"Leave-one-topic-out validation ({folds.get_n_splits(groups=groups)} folds)",
        "source": "Original synthetic demonstration dataset; labels are illustrative, not teacher grades.",
        "predictions": [
            {"topic": row["topic_id"], "variant": row["variant"],
             "expected": int(y[index]), "predicted": round(float(predictions[index]), 2)}
            for index, row in enumerate(rows)
        ],
    }
    joblib.dump(Ridge(alpha=0.5).fit(x, y), root / "model.pkl")
    joblib.dump(vectorizer, root / "vectorizer.pkl")
    (root / "benchmark.json").write_text(json.dumps(benchmark, indent=2) + "\n", encoding="utf-8")
    return benchmark


if __name__ == "__main__":
    metrics = train(Path(__file__).resolve().parent)
    print(f"Trained on {metrics['samples']} answers. MAE: {metrics['mae']}. R²: {metrics['r2']}.")
