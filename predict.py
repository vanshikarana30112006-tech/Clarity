"""Evaluate a sample or UTF-8 answer file without opening the browser."""
import argparse
import json
from pathlib import Path

from dataset import TOPICS
from engine import evaluate


def main():
    topics = {topic["id"]: topic for topic in TOPICS}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic", choices=topics, default="ml")
    parser.add_argument("--answer-file", type=Path, help="UTF-8 text. Defaults to the bundled sample.")
    options = parser.parse_args()
    topic = topics[options.topic]
    answer = options.answer_file.read_text(encoding="utf-8-sig") if options.answer_file else topic["paraphrase"]
    result = evaluate(answer, topic["reference"], topic["concepts"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
