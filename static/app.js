'use strict';
const $ = id => document.getElementById(id);
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const defaults = {alignment:50, concepts:30, structure:10, completeness:10};
const labels = {alignment:'Answer alignment', concepts:'Key concepts', structure:'Clarity & structure', completeness:'Development'};
let templates = [], evaluations = [], deleteId = null, toastTimer, uploadBusy = false;

async function api(url, options={}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = 'Something went wrong. Please try again.';
    try { const data = await response.json(); message = Array.isArray(data.detail) ? data.detail.map(d => `${d.loc.at(-1)}: ${d.msg}`).join(' ') : data.detail || message; } catch (_) { if (response.status===413) message='The file is too large. Choose a file smaller than 5 MB.'; }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}
function toast(message, error=false) {clearTimeout(toastTimer);$('toast').textContent=message;$('toast').className=error?'error':'';$('toast').hidden=false;toastTimer=setTimeout(()=>$('toast').hidden=true,error?8500:4500);}
function show(view) {
  document.querySelectorAll('.view').forEach(el=>el.hidden=el.id!==`view-${view}`);
  document.querySelectorAll('[data-view]').forEach(el=>{el.classList.toggle('active',el.dataset.view===view);if(el.dataset.view===view)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
  if(view==='history')renderHistory();
  window.scrollTo({top:0,behavior:'instant'});
}
function navigate(view){location.hash=view;if(location.hash===`#${view}`)show(view);}
document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>navigate(button.dataset.view));
window.addEventListener('hashchange',()=>show(['evaluate','history'].includes(location.hash.slice(1))?location.hash.slice(1):'evaluate'));

function renderWeights() {
  $('weights').innerHTML=Object.keys(defaults).map(key=>`<div class="weight-row"><label class="weight-label" for="weight-${key}">${labels[key]}<span class="weight-value"><input id="weight-${key}" aria-label="${labels[key]} weight" type="number" min="0" max="100" step="1" value="${defaults[key]}">%</span></label></div>`).join('');
  Object.keys(defaults).forEach(key=>$(`weight-${key}`).addEventListener('input',updateWeights)); updateWeights();
}
function getWeights(){return Object.fromEntries(Object.keys(defaults).map(key=>[key,Number($(`weight-${key}`).value)]));}
function updateWeights(){const weights=getWeights(), total=Object.values(weights).reduce((a,b)=>a+b,0);$('weight-total').textContent=`${total}%`;$('weight-total').style.color=total===100?'':'#a34438';}
$('reset-weights').onclick=renderWeights;
function updateWords(){$('word-count').textContent=`${($('answer').value.match(/[a-zA-Z]+(?:'[a-z]+)?/g)||[]).length} words`;}
$('answer').addEventListener('input',updateWords);
function applyTemplate() {
  const t=templates.find(t=>t.id===$('template').value);
  if(!t){$('title').value='';$('question').value='';$('reference').value='';$('concepts').value='';$('reference-details').open=true;return;}
  $('title').value=t.title;$('question').value=t.question;$('reference').value=t.reference;$('concepts').value=t.concepts.join(', ');
}
$('template').onchange=applyTemplate;
$('demo').onclick=()=>{if(!templates.length)return toast('Templates are still loading. Try again shortly.',true);$('template').value='ml';applyTemplate();$('student').value='Alex Morgan (sample)';$('answer').value=templates[0].paraphrase;updateWords();toast('Sample loaded. Adjust the rubric or evaluate when ready.');};
async function upload(file) {
  if(!file || uploadBusy)return;
  if(file.size>5*1024*1024)return toast('Choose a file smaller than 5 MB.',true);
  uploadBusy=true;$('file-status').textContent='Reading your document…';$('evaluate-button').disabled=true;
  const data=new FormData();data.append('file',file);
  try{const result=await api('/api/extract',{method:'POST',body:data});$('answer').value=result.text;updateWords();$('file-status').textContent=`${result.filename} · text ready to review`;toast('Document loaded. Review the extracted text before evaluating.');}
  catch(e){$('file-status').textContent='File was not loaded. Your previous text has been kept.';toast(e.message,true);}
  finally{uploadBusy=false;$('evaluate-button').disabled=false;$('file').value='';}
}
$('file').onchange=e=>upload(e.target.files[0]);
$('evaluation-form').addEventListener('invalid',e=>{if(e.target.closest('details'))$('reference-details').open=true;},true);
$('evaluation-form').onsubmit=async e=>{
  e.preventDefault();const weights=getWeights();
  if(Object.values(weights).some(v=>!Number.isInteger(v)||v<0||v>100)||Object.values(weights).reduce((a,b)=>a+b,0)!==100)return toast('Rubric weights must be whole numbers that add up to 100%.',true);
  const payload={student:$('student').value.trim(),title:$('title').value.trim(),question:$('question').value.trim(),answer:$('answer').value.trim(),reference:$('reference').value.trim(),concepts:$('concepts').value.split(',').map(x=>x.trim()).filter(Boolean),weights};
  $('evaluate-button').disabled=true;$('evaluate-button').textContent='Evaluating…';
  try{const result=await api('/api/evaluate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});evaluations.unshift(result);renderResult(result);show('result');toast('Evaluation complete and saved.');}
  catch(error){toast(error.message,true);}
  finally{$('evaluate-button').disabled=false;$('evaluate-button').textContent='Evaluate assignment';}
};
const date=value=>new Date(value).toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric'});
function renderHistory(){
  const search=$('search').value.trim().toLowerCase();
  const rows=evaluations.filter(r=>`${r.student} ${r.title}`.toLowerCase().includes(search));
  $('history-list').innerHTML = rows.length ? rows.map(r => `<div class="history-row">
    <div><strong>${escapeHTML(r.student)}</strong><small>${escapeHTML(r.title)} · ${date(r.created)}</small></div>
    <strong>${r.score}/100</strong>
    <button class="row-open" data-open="${r.id}" aria-label="View evaluation for ${escapeHTML(r.student)}">View</button>
  </div>`).join('') : `<p class="empty-state">${evaluations.length ? 'No matching results.' : 'Your saved evaluations will appear here.'}</p>`;
  document.querySelectorAll('[data-open]').forEach(button=>button.onclick=()=>{const r=evaluations.find(x=>x.id===button.dataset.open);renderResult(r);show('result');});
}
$('search').oninput=renderHistory;
function renderResult(r){
  $('view-result').innerHTML = `
    <div class="page-heading">
      <div><h1>Evaluation feedback</h1><p>${escapeHTML(r.student)} · ${escapeHTML(r.title)}</p></div>
      <button class="button secondary" id="back-to-form">Back to form</button>
    </div>
    <section class="panel">
      <div class="score-summary"><strong>${r.score}/100</strong><div>${r.band}<small>Suggested score · ${r.covered.length} of ${r.concepts.length} concepts mentioned</small></div></div>
      ${r.strengths.length ? `<div class="feedback-block"><h2>What worked</h2><ul>${r.strengths.map(x => `<li>${escapeHTML(x)}</li>`).join('')}</ul></div>` : ''}
      <div class="feedback-block"><h2>What to improve</h2><ul>${r.improvements.map(x => `<li>${escapeHTML(x)}</li>`).join('')}</ul></div>
      <p class="result-note">Review the suggested score before using it as a grade.</p>
      <details><summary>Score breakdown and answers</summary><div class="detail-body">
        ${r.criteria.map(c => `<div class="criterion"><span>${c.label}</span><strong>${c.earned} / ${c.weight}</strong></div>`).join('')}
        <h3 style="margin-top: 16px">Student answer</h3><p class="saved-answer">${escapeHTML(r.answer)}</p>
        <h3>Reference answer</h3><p class="saved-answer">${escapeHTML(r.reference)}</p>
      </div></details>
      <div class="result-actions"><button class="button primary" id="download-report">Download feedback</button><button class="button secondary" id="print-report">Print / save PDF</button><button class="text-button" id="delete-result">Delete</button></div>
    </section>`;
  $('back-to-form').onclick=()=>navigate('evaluate');$('print-report').onclick=()=>window.print();$('download-report').onclick=()=>downloadReport(r);$('delete-result').onclick=()=>{deleteId=r.id;$('delete-dialog').showModal();};
}
$('cancel-delete').onclick=()=>$('delete-dialog').close();
$('confirm-delete').onclick=async()=>{try{await api(`/api/evaluations/${deleteId}`,{method:'DELETE'});evaluations=evaluations.filter(r=>r.id!==deleteId);$('delete-dialog').close();navigate('history');toast('Evaluation deleted.');}catch(e){toast(e.message,true);}};
function downloadReport(r){const text=`CLARITY · ASSIGNMENT FEEDBACK\n\nStudent: ${r.student}\nAssignment: ${r.title}\nDate: ${date(r.created)}\nSuggested score: ${r.score}/100 — ${r.band}\n\nSCORE BREAKDOWN\n${r.criteria.map(c=>`${c.label}: ${c.earned}/${c.weight}`).join('\n')}\n\nWHAT'S WORKING\n${r.strengths.map(x=>'- '+x).join('\n')}\n\nNEXT STEPS\n${r.improvements.map(x=>'- '+x).join('\n')}\n\nQUESTION\n${r.question}\n\nSUBMITTED ANSWER\n${r.answer}\n\nREFERENCE ANSWER\n${r.reference}\n\n${r.review_note}\n`;const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`clarity-feedback-${r.id.slice(0,8)}.txt`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function start(){renderWeights();try{[templates,evaluations]=await Promise.all([api('/api/templates'),api('/api/evaluations')]);templates.forEach(t=>{const option=document.createElement('option');option.value=t.id;option.textContent=t.title;$('template').appendChild(option);});$('template').value=templates[0].id;applyTemplate();show(['history'].includes(location.hash.slice(1))?location.hash.slice(1):'evaluate');}catch(e){toast('Could not connect to the Python service. Start the app and reload. '+e.message,true);}}
if (location.protocol === 'file:') {
  $('local-setup').hidden = false;
  document.querySelector('nav').hidden = true;
} else {
  show('evaluate');
  start();
}

