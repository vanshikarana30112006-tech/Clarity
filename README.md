# Clarity — AI-assisted assignment evaluation

A complete, single-user academic project with a Python backend and responsive HTML/CSS/JavaScript interface. It runs locally without a paid API key. It does not modify or depend on the original Streamlit link.

## Run on Windows

Install Python 3.11, then double-click `start.bat` in the repository. The first run installs the required libraries. The launcher opens **http://127.0.0.1:8000** when ready. Keep the command window running. Opening the HTML file directly shows these launch instructions.

Or run manually from this folder:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

On macOS/Linux use `python3 -m venv .venv`, `.venv/bin/python -m pip install -r requirements-lock.txt`, and `.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000`. The lock file records the exact library versions tested for this delivery; `requirements.txt` records the allowed version ranges.

## Try the complete flow

1. Click **Try a sample**, then **Evaluate assignment**.
2. Inspect the suggested score, rubric breakdown, covered concepts and improvement advice.
3. Download the feedback as text, or choose **Print / save PDF**.
4. Open **Saved results** to search and reopen evaluations. Use **Download CSV** to export them.
5. Choose another template or **Custom assignment**. Open **Assignment settings** to edit the reference answer and concepts or adjust scoring weights.
6. Upload a UTF-8 TXT, text-based PDF, or DOCX. Review the extracted text before evaluation. Scanned PDFs require external OCR. Maximum file size is 5 MB, maximum PDF length 30 pages, maximum answer length 30,000 characters.

## What the AI actually does

`engine.py` uses scikit-learn TF-IDF text features and a trained Ridge regression model. It measures reference similarity, explicit concept coverage, sentence structure, answer development and repetition. The learned estimate is combined with editable rubric weights. It is an explainable NLP baseline, **not a generative language model**. The grading question is context for the educator; the supplied reference and concepts drive the score.

Default rubric: answer alignment 50%, key concepts 30%, clarity and structure 10%, development 10%. Each contribution is displayed. Concepts accept alternative wording with `|`, e.g. `labelled data|labeled data`. Matching uses whole words and phrases.

The system cannot verify factual correctness, reliably understand negation, detect plagiarism, or detect AI authorship. Keyword stuffing, paraphrases and out-of-domain answers remain limitations. Scores are suggestions for teacher review, not validated autonomous grades. English prose is supported; mathematical notation and code need a different evaluator.

## Dataset and validation

The project includes **48 original synthetic demonstration examples across six computer science topics**. They include full answers, paraphrases, partial answers, short answers, unrelated answers, keyword lists, repetition and expanded answers. See `dataset.csv` and `dataset.py`. The reference labels are illustrative.

The regression benchmark uses leave-one-topic-out validation, so all variants of the tested topic stay out of its training fold. Reported MAE and R² apply to the regression estimate before custom rubric weighting. They are **not** a claim of classroom accuracy. The complete model is then fitted to all demonstration samples for local use. For a defensible research evaluation, replace illustrative labels with consented teacher-scored answers and use a larger independent held-out dataset.

Rebuild the dataset and saved model, score the included sample, and run the tests:

```powershell
.venv\Scripts\python.exe generate_dataset.py
.venv\Scripts\python.exe train_model.py
.venv\Scripts\python.exe predict.py --answer-file samples/ml_answer.txt
.venv\Scripts\python.exe -m pytest -q
```

Tests cover grading and rubric validation, saved results, exports, and file extraction. `TEST_RESULTS.md` records the verification. `benchmark.json` includes every held-out prediction. The `samples` folder provides six text answers for trying file uploads.

## Project layout

- `app.py`: API, file reading, SQLite storage and input limits.
- `dataset.py`, `dataset.csv` and `generate_dataset.py`: assignment templates, labelled examples and the CSV generator.
- `preprocess.py`: text processing and features for a pair of answers.
- `train_model.py` and `benchmark.json`: model training and validation results.
- `model.pkl`: trained Ridge regression model.
- `vectorizer.pkl`: TF-IDF settings. The app fits a fresh copy to each answer and reference pair.
- `engine.py` and `predict.py`: shared scoring and the command-line predictor.
- `static/`: responsive interface.
- `tests/`: automated checks.
- `data/clarity.db`: created at runtime; contains saved answers and feedback.

To use a different database set `CLARITY_DB` to its file path. Data persists across restarts. Delete individual evaluations from their feedback page. Browser refresh does not save an unfinished form.

## Upload to GitHub

Extract the source ZIP and add its contents to the root of the repository. Include `.gitignore`, both `.pkl` files, and the `static`, `samples` and `tests` folders. Keep local student results, virtual environments and the separate Windows portable ZIP out of the repository.

Clarity uses TF-IDF and Ridge regression. Its scoring artifacts are `model.pkl` and `vectorizer.pkl`. The screenshot's `sbert_marks_model.pkl` belongs to an SBERT implementation and is not part of Clarity.

## Deployment and privacy

This package includes a Render Blueprint for a public demo. Upload the contents to a GitHub repository, then create a **Blueprint** in Render and select that repository. Review the free web service defined in `render.yaml` and deploy it. Render assigns the public address after the service passes the health check.

The Blueprint enables `CLARITY_PUBLIC_DEMO=1`. The server processes uploads and scores but does not create or write a results database. Saved results and CSV exports use each visitor's browser. Use sample or anonymized answers for public demonstrations. Clearing browser storage removes saved results. A free Render instance can take time to wake after being idle.

For a manual Render Web Service deployment, use `pip install -r requirements-lock.txt` as the build command and `uvicorn app:app --host 0.0.0.0 --port $PORT --limit-concurrency 16` as the start command. Set `CLARITY_PUBLIC_DEMO` to `1`. Use `/api/health` for the health check.

For local use, the Windows launcher continues to keep results in its SQLite database. Use the public demo setting for an internet-facing deployment.

The interface uses system fonts and included assets. Evaluation runs on your computer.

Technical references: [FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/), [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/), [scikit-learn Ridge regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html).
