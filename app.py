from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from io import BytesIO, StringIO
import csv
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from pypdf import PdfReader
from docx import Document
from zipfile import ZipFile, BadZipFile
from dataset import TOPICS
from engine import evaluate, BENCHMARK, DEFAULT_WEIGHTS, words

ROOT=Path(__file__).parent
DB_PATH=Path(os.environ.get('CLARITY_DB',ROOT/'data'/'clarity.db'))

@contextmanager
def connection():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row
    con.execute('CREATE TABLE IF NOT EXISTS evaluations (id TEXT PRIMARY KEY, created TEXT NOT NULL, payload TEXT NOT NULL)')
    try:
        with con:
            yield con
    finally:
        con.close()

@asynccontextmanager
async def lifespan(app):
    with connection(): pass
    yield

app=FastAPI(title='Clarity Assignment Evaluation',lifespan=lifespan)

@app.middleware('http')
async def limits(request:Request,call_next):
    if request.method=='POST':
        total=0; chunks=[]
        async for chunk in request.stream():
            total+=len(chunk)
            if total>6*1024*1024: return Response('Request exceeds 6 MB.',status_code=413)
            chunks.append(chunk)
        request._body=b''.join(chunks)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    return response

class Submission(BaseModel):
    student:str=Field(min_length=1,max_length=100)
    title:str=Field(min_length=1,max_length=160)
    question:str=Field(min_length=10,max_length=5000)
    answer:str=Field(min_length=20,max_length=30000)
    reference:str=Field(min_length=30,max_length=20000)
    concepts:list[str]=Field(min_length=1,max_length=20)
    weights:dict[str,int]=Field(default_factory=lambda:dict(DEFAULT_WEIGHTS))

    @field_validator('student','title','question','answer','reference')
    @classmethod
    def strip_text(cls,value):
        value=value.strip()
        if not value: raise ValueError('This field cannot be blank.')
        return value

    @field_validator('answer')
    @classmethod
    def actual_words(cls,value):
        if len(words(value))<5: raise ValueError('Please provide at least 5 words.')
        return value

    @field_validator('reference')
    @classmethod
    def reference_words(cls,value):
        if len(words(value))<10: raise ValueError('Reference answer needs at least 10 words.')
        return value

    @field_validator('concepts')
    @classmethod
    def valid_concepts(cls,values):
        clean=[v.strip().lower() for v in values]
        if any(not v or len(v)>150 or any(not words(a) for a in v.split('|')) for v in clean): raise ValueError('Provide non-empty concepts of at most 150 characters.')
        if len(set(clean))!=len(clean): raise ValueError('Concepts must be unique.')
        return clean

    @field_validator('weights')
    @classmethod
    def valid_weights(cls,value):
        if set(value)!=set(DEFAULT_WEIGHTS) or any(v<0 or v>100 for v in value.values()) or sum(value.values())!=100: raise ValueError('The four rubric weights must total 100.')
        return value

@app.get('/api/health')
def health(): return {'status':'ok','model':'TF-IDF + Ridge regression (local)'}

@app.get('/api/templates')
def templates(): return TOPICS

@app.get('/api/benchmark')
def benchmark(): return BENCHMARK

@app.post('/api/evaluate',status_code=201)
def grade(submission:Submission):
    result=dict(id=uuid.uuid4().hex,created=datetime.now(timezone.utc).isoformat(),**submission.model_dump(),**evaluate(submission.answer,submission.reference,submission.concepts,submission.weights))
    with connection() as con:
        con.execute('INSERT INTO evaluations VALUES (?,?,?)',(result['id'],result['created'],json.dumps(result)))
    return result

@app.get('/api/evaluations')
def history():
    with connection() as con:
        return [json.loads(r['payload']) for r in con.execute('SELECT payload FROM evaluations ORDER BY created DESC')]

@app.get('/api/evaluations/{evaluation_id}')
def detail(evaluation_id:str):
    with connection() as con:
        row=con.execute('SELECT payload FROM evaluations WHERE id=?',(evaluation_id,)).fetchone()
    if not row: raise HTTPException(404,'Evaluation not found.')
    return json.loads(row['payload'])

@app.delete('/api/evaluations/{evaluation_id}',status_code=204)
def delete(evaluation_id:str):
    with connection() as con:
        cursor=con.execute('DELETE FROM evaluations WHERE id=?',(evaluation_id,))
        if not cursor.rowcount: raise HTTPException(404,'Evaluation not found.')

@app.get('/api/export')
def export():
    output=StringIO(); writer=csv.writer(output)
    writer.writerow(['Student','Assignment','Score','Band','Words','Date'])
    def safe(value):
        text=str(value)
        return "'"+text if text.lstrip().startswith(('=','+','-','@')) else text
    for row in history(): writer.writerow([safe(row[k]) for k in ['student','title','score','band','word_count','created']])
    return Response(output.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="clarity-results.csv"'})

@app.post('/api/extract')
async def extract(file:UploadFile=File(...)):
    data=await file.read(5*1024*1024+1)
    if len(data)>5*1024*1024: raise HTTPException(413,'Choose a file smaller than 5 MB.')
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in {'.txt','.pdf','.docx'}: raise HTTPException(415,'Supported formats: TXT, PDF and DOCX.')
    try:
        if suffix=='.txt': text=data.decode('utf-8-sig')
        elif suffix=='.pdf':
            pdf=PdfReader(BytesIO(data))
            if pdf.is_encrypted: raise ValueError('Encrypted PDF')
            if len(pdf.pages)>30: raise HTTPException(422,'PDF files may contain at most 30 pages.')
            text='\n'.join(page.extract_text() or '' for page in pdf.pages)
        else:
            with ZipFile(BytesIO(data)) as archive:
                if sum(i.file_size for i in archive.infolist())>20*1024*1024: raise HTTPException(413,'Expanded document exceeds 20 MB.')
            doc=Document(BytesIO(data))
            text='\n'.join([p.text for p in doc.paragraphs]+[' '.join(c.text for c in r.cells) for t in doc.tables for r in t.rows])
    except HTTPException: raise
    except Exception:
        raise HTTPException(422,'Could not read this file. Use a valid UTF-8 TXT, unlocked text PDF, or DOCX.')
    if not text.strip(): raise HTTPException(422,'No readable text found. Scanned PDFs need OCR first; paste the text instead.')
    if len(text)>30000: raise HTTPException(422,'The extracted text exceeds 30,000 characters. Submit a shorter document.')
    return {'text':text.strip(),'filename':file.filename,'words':len(words(text))}

app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')

@app.get('/')
def index(): return FileResponse(ROOT/'static'/'index.html')
