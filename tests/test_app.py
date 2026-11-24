import io
import csv
import pytest
from fastapi.testclient import TestClient
from docx import Document
from pypdf import PdfWriter
import app as service
from dataset import TOPICS, records
from engine import evaluate, BENCHMARK, features

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'DB_PATH',tmp_path/'test.db')
    with TestClient(service.app) as c: yield c

@pytest.fixture
def submission():
    t=TOPICS[0]
    return dict(student='Test Student',title=t['title'],question=t['question'],answer=t['paraphrase'],reference=t['reference'],concepts=t['concepts'])

def test_create_read_export_delete(client,submission):
    assert client.get('/').status_code==200
    assert client.get('/api/health').json()['status']=='ok'
    assert client.get('/api/evaluations').json()==[]
    response=client.post('/api/evaluate',json=submission)
    assert response.status_code==201,response.text
    result=response.json()
    assert 0<=result['score']<=100
    assert abs(sum(c['earned'] for c in result['criteria'])-result['score'])<0.3
    assert client.get('/api/evaluations/'+result['id']).json()==result
    assert len(client.get('/api/evaluations').json())==1
    assert 'Test Student' in client.get('/api/export').text
    assert client.delete('/api/evaluations/'+result['id']).status_code==204
    assert client.get('/api/evaluations/'+result['id']).status_code==404
    assert client.delete('/api/evaluations/'+result['id']).status_code==404
    assert client.get('/api/evaluations').json()==[]

@pytest.mark.parametrize('field,value',[
    ('student','   '),('answer','! '*25),('answer','short'),('reference','! '*20),
    ('concepts',[]),('concepts',['   ']),('concepts',['data','data']),('concepts',['data|']),
    ('weights',{'alignment':90,'concepts':30,'structure':10,'completeness':10}),
    ('weights',{'alignment':100}),('answer','word '*6100),
])
def test_validation(client,submission,field,value):
    submission[field]=value
    assert client.post('/api/evaluate',json=submission).status_code==422
    assert not client.get('/api/evaluations').json()

@pytest.mark.parametrize('topic',TOPICS,ids=[t['id'] for t in TOPICS])
def test_answer_quality_ordering(topic):
    score=lambda text:evaluate(text,topic['reference'],topic['concepts'])['score']
    complete=score(topic['reference']);paraphrase=score(topic['paraphrase']);partial=score(topic['partial'])
    irrelevant=score('A wonderful cake contains sugar and flour. Baking takes careful preparation. My favorite recipe uses chocolate and fresh cherries.')
    repetition=score((topic['partial'].split('.')[0]+'. ')*10)
    keywords=score(', '.join(c.split('|')[0] for c in topic['concepts']))
    assert complete>paraphrase>partial>irrelevant,(topic['id'],complete,paraphrase,partial,irrelevant)
    assert complete>=80 and irrelevant<20
    assert keywords<45 and repetition<55

def test_alternative_concepts_and_boundaries():
    _,found=features('Unlabelled data is useful for clustering groups.',TOPICS[0]['reference'],['labelled data','unlabelled data','cluster'])
    assert found==[False,True,False]

def test_all_samples_finite_and_bounded():
    topics={t['id']:t for t in TOPICS}
    for r in records():
        t=topics[r['topic_id']];result=evaluate(r['answer'],t['reference'],t['concepts'])
        assert 0<=result['score']<=100
    assert BENCHMARK['samples']==48
    assert len(BENCHMARK['predictions'])==48
    assert BENCHMARK['mae']<20

def test_custom_weights(client,submission):
    submission['weights']={'alignment':0,'concepts':100,'structure':0,'completeness':0}
    response=client.post('/api/evaluate',json=submission)
    assert response.status_code==201
    result=response.json()
    assert result['score']==result['criteria'][1]['earned']

def test_text_upload(client):
    response=client.post('/api/extract',files={'file':('answer.txt',b'This is a readable test answer.','text/plain')})
    assert response.status_code==200
    assert response.json()['words']==6

def test_docx_upload_with_table(client):
    doc=Document();doc.add_paragraph('A paragraph in a document.');table=doc.add_table(rows=1,cols=1);table.cell(0,0).text='Table content is included.'
    output=io.BytesIO();doc.save(output)
    r=client.post('/api/extract',files={'file':('answer.docx',output.getvalue())})
    assert r.status_code==200
    assert 'Table content is included.' in r.json()['text']

def test_pdf_upload(client):
    # Minimal real PDF with an embedded text stream, no external test assets.
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
    writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 50 700 Td (This is a readable PDF answer.) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream)
    output=io.BytesIO();writer.write(output)
    r=client.post('/api/extract',files={'file':('answer.pdf',output.getvalue())})
    assert r.status_code==200,r.text
    assert 'readable PDF answer' in r.json()['text']

@pytest.mark.parametrize('name,data,status',[
    ('bad.exe',b'executable',415),('bad.pdf',b'not a PDF',422),('bad.docx',b'not a document',422),
    ('bad.txt',b'\xff\xfe',422),('empty.txt',b'  ',422),('long.txt',b'a'*30001,422),
    ('large.txt',b'a'*(5*1024*1024+1),413)
])
def test_rejected_files(client,name,data,status):
    assert client.post('/api/extract',files={'file':(name,data)}).status_code==status

def test_blank_pdf(client):
    writer=PdfWriter();writer.add_blank_page(width=200,height=200);output=io.BytesIO();writer.write(output)
    r=client.post('/api/extract',files={'file':('scan.pdf',output.getvalue())})
    assert r.status_code==422 and 'OCR' in r.json()['detail']

def test_csv_formula_safety(client,submission):
    submission['student']='=SUM(1,2)'
    assert client.post('/api/evaluate',json=submission).status_code==201
    rows=list(csv.reader(io.StringIO(client.get('/api/export').text)))
    assert rows[1][0].startswith("'=")

def test_oversized_body(client):
    assert client.post('/api/evaluate',content=b'x'*(6*1024*1024+1)).status_code==413

def test_persistence_across_clients(client,submission):
    first=client.post('/api/evaluate',json=submission).json()
    with TestClient(service.app) as second:
        assert second.get('/api/evaluations/'+first['id']).json()['score']==first['score']
