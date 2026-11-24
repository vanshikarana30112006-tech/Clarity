# Verification report

## GitHub source package

The dataset generator produced 48 records. Training from that CSV reproduced a mean absolute error of 12.10 and an R² of 0.813. The command-line predictor loaded the saved artifacts and scored the included machine-learning answer 80.3/100.

Verified on 24 November 2026 with Python 3.11 on Windows and Microsoft Edge through Playwright.

## Automated checks

**35 tests passed** after the interface and launcher update.

- Creating, reading, exporting and deleting evaluations.
- Persistent results across independent application clients.
- Empty fields, invalid references, invalid concept lists, long answers and invalid rubric weights.
- Full, paraphrased, partial, unrelated, repetitive and keyword-only answers across all six topics.
- Score bounds and agreement between total score and displayed contributions.
- Whole-phrase matching and alternative concept wording.
- Text extraction from TXT, real text PDF, DOCX paragraphs and DOCX tables.
- Rejection of unsupported files, damaged documents, non-UTF-8 text, empty files and scanned/blank PDFs.
- File size, extracted text length and overall request size limits.
- Spreadsheet formula escaping in exported CSV names.

`node --check static/app.js` and Python compilation passed. The test runner emits one upstream deprecation warning about Starlette's existing HTTPX test-client integration. It does not affect test outcomes; the exact verified dependencies are recorded in `requirements-lock.txt`.

## Browser walkthrough

- Opened the HTML file directly and checked its styling, launch instructions and link to the running app.
- Started Clarity using the Windows launcher and confirmed it opened the browser once ready.
- Inspected the updated desktop layout at 1440 × 900 and phone layout at 390 × 844. The phone layout fit without horizontal scrolling.
- Evaluated the sample and checked its score of 80.3/100, then downloaded feedback.
- Searched saved results, reopened a result and confirmed deletion.
- Uploaded a TXT sample and verified that its text was ready to review.
- Confirmed the assignment settings start closed and open when a custom assignment is selected.
- The browser walkthrough reported no JavaScript errors.
## Model benchmark

48 original synthetic examples, six topics, leave-one-topic-out validation:

| Metric | Measured value |
| --- | ---: |
| Mean absolute error | 12.10 / 100 points |
| R² | 0.813 |
| Held-out topic folds | 6 |

Every held-out prediction is included in `data/benchmark.json`. These values measure the regression estimate before custom rubric weighting. The illustrative dataset is small and template-derived; it cannot establish accuracy for real student work. No real classroom validation, plagiarism detection or factual correctness verification is claimed.

## Scope

This delivery is a local, single-user Python application. Mobile checks used a browser viewport, not a physical phone. PDF/Word parsing was checked using generated representative files, not every document format variant. Native operating-system print dialogs were not automated; feedback text downloads and CSV export were verified. Public hosting and multi-user authentication are outside this delivery.

