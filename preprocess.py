"""Text processing and pair-local TF-IDF features."""
import re

import numpy as np
from sklearn.base import clone
from sklearn.feature_extraction.text import TfidfVectorizer


def new_vectorizer():
    return TfidfVectorizer(stop_words='english', ngram_range=(1, 2), sublinear_tf=True)


def words(text):
    return re.findall(r"[a-zA-Z]+(?:'[a-z]+)?", text.lower())

def features(answer, reference, concepts, vectorizer_template=None):
    tokens=words(answer); ref=words(reference)
    # Pair-local comparison; no corpus vocabulary is shared across held-out topics.
    vectorizer = clone(vectorizer_template) if vectorizer_template is not None else new_vectorizer()
    try:
        vectors=vectorizer.fit_transform([reference,answer])
        similarity=float((vectors[0]@vectors[1].T).toarray()[0,0])
    except ValueError:
        similarity=0.0
    normalized=' '.join(tokens)
    found=[any(re.search(r'(?<!\w)'+re.escape(' '.join(words(alias)))+r'(?!\w)',normalized) for alias in c.split('|')) for c in concepts]
    coverage=sum(found)/max(len(found),1)
    sentences=[s.strip() for s in re.split(r'[.!?]+',answer) if len(words(s))>=4]
    diversity=len(set(tokens))/max(len(tokens),1)
    unique_sentences=len(set(s.lower() for s in sentences))/max(len(sentences),1)
    structure=min(len(sentences)/3,1)*min(diversity/0.4,1)*unique_sentences
    completeness=min(len(set(tokens))/max(len(set(ref))*0.85,1),1)
    return np.array([similarity,coverage,structure,completeness,unique_sentences]),found

