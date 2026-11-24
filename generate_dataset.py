"""Export the original synthetic demonstration answers to dataset.csv."""
import csv
from pathlib import Path

from dataset import records


if __name__ == "__main__":
    target = Path(__file__).resolve().with_name("dataset.csv")
    rows = records()
    with target.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} examples to {target.name}.")
