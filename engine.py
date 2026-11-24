"""Score an answer using the bundled Clarity model."""
import json
from pathlib import Path

import joblib
import numpy as np

from preprocess import features, words

ROOT = Path(__file__).resolve().parent
MODEL = joblib.load(ROOT / 'model.pkl')
VECTORIZER = joblib.load(ROOT / 'vectorizer.pkl')
BENCHMARK = json.loads((ROOT / 'benchmark.json').read_text(encoding='utf-8'))

DEFAULT_WEIGHTS={'alignment':50,'concepts':30,'structure':10,'completeness':10}

def evaluate(answer,reference,concepts,weights=None):
    weights=weights or DEFAULT_WEIGHTS
    f,found=features(answer, reference, concepts, VECTORIZER)
    estimate=float(np.clip(MODEL.predict([f])[0],0,100))
    # No credit for polished but unrelated prose. These are heuristic checks.
    relevance=min(1,float(f[0])*5+float(f[1]))
    values={'alignment':estimate*relevance,'concepts':100*float(f[1])*max(float(f[2]),0.2),'structure':100*float(f[2])*relevance,'completeness':100*float(f[3])*relevance}
    score=round(sum(values[k]*weights[k]/100 for k in weights),1)
    strengths=[]; improvements=[]
    covered=[c.split('|')[0] for c,present in zip(concepts,found) if present]
    missing=[c.split('|')[0] for c,present in zip(concepts,found) if not present]
    if covered: strengths.append('Your response mentions '+', '.join(covered)+'.')
    if f[2]>=0.75: strengths.append('The response contains several distinct, complete sentences.')
    if f[0]>=0.3: strengths.append('The vocabulary aligns with the reference answer.')
    if missing: improvements.append('Explain the missing concepts: '+', '.join(missing)+'.')
    if f[3]<0.75: improvements.append('Develop the explanation with a comparison and a concrete example.')
    if f[2]<0.75: improvements.append('Use original, complete sentences instead of lists or repeated statements.')
    if relevance<0.5: improvements.append('Address the assignment question directly; the response has little overlap with the reference.')
    if not improvements: improvements.append('Check factual details and connect each example explicitly to the question.')
    return dict(score=score,band='Strong' if score>=80 else 'Developing' if score>=50 else 'Needs revision',word_count=len(words(answer)),similarity=round(float(f[0])*100,1),model_estimate=round(estimate,1),criteria=[dict(key=k,label={'alignment':'Answer alignment','concepts':'Key concepts','structure':'Clarity & structure','completeness':'Development'}[k],score=round(values[k],1),weight=weights[k],earned=round(values[k]*weights[k]/100,1)) for k in weights],covered=covered,missing=missing,strengths=strengths,improvements=improvements,review_note='Suggested feedback only. This local NLP model compares language and concepts; it cannot verify facts, detect plagiarism, or reliably understand negation. A teacher should review the result.')
