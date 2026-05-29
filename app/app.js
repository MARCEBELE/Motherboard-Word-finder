// Board Word Finder — viewer logic
window.addEventListener('error', e => {
  const el = document.getElementById('empty');
  if (el) { el.style.display = 'block'; el.textContent = 'Error: ' + e.message; }
});

const $ = id => document.getElementById(id);
const cv = $('cv'), ctx = cv.getContext('2d');
let BOARD = null, imgs = [], labelsFlat = [], matches = [], cur = -1, showAll = false;
let view = { i: 0, s: 1, tx: 0, ty: 0 };

const MAP = { 'O':'0','Q':'0','D':'0','I':'1','L':'1','|':'1','S':'5','B':'8','Z':'2','G':'6','T':'7' };
const norm = s => (s||'').toUpperCase().replace(/[^A-Z0-9]/g,'');
const fuzz = s => norm(s).split('').map(c=>MAP[c]||c).join('');
function bbox(box){ const xs=box.map(p=>p[0]), ys=box.map(p=>p[1]);
  return { x0:Math.min(...xs), y0:Math.min(...ys), x1:Math.max(...xs), y1:Math.max(...ys) }; }

async function api(path, opts){
  const r = await fetch(path, opts);
  if(!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}
function showEmpty(msg){ $('empty').style.display='block'; $('empty').textContent=msg; }
function hideEmpty(){ $('empty').style.display='none'; }

async function loadBoards(selectId){
  let data;
  try { data = await api('/api/boards'); }
  catch(e){ showEmpty('Please open this tool with "Start Word Finder.bat" (it must run through the local server, not by double-clicking the HTML file).'); return; }
  const sel = $('board'); sel.replaceChildren();
  if(!data.boards.length){
    showEmpty('No boards yet. Click "+ Add" and choose a folder that contains this board’s photos.');
    $('stat').textContent = ''; updateCounter(); draw(); return;
  }
  hideEmpty();
  data.boards.forEach(b => { const o=document.createElement('option');
    o.value=b.id; o.textContent=`${b.name} (${b.labels} labels)`; sel.appendChild(o); });
  const pick = (selectId && data.boards.some(b=>b.id===selectId))
    ? selectId : data.boards[0].id;
  sel.value = pick;
  await loadBoard(pick);
}

async function loadBoard(id){
  const data = await api('/api/boards/' + id);
  BOARD = data; imgs = []; labelsFlat = []; matches = []; cur = -1;
  data.images.forEach((im, i) => {
    const el = new Image(); el.src = im.file; imgs[i] = el;
    (im.labels||[]).forEach(L => { const b = bbox(L.box);
      labelsFlat.push({ i, text:L.text, norm:norm(L.text), fuzz:fuzz(L.text), box:L.box,
        score:L.score, cx:(b.x0+b.x1)/2, cy:(b.y0+b.y1)/2, w:b.x1-b.x0, h:b.y1-b.y0 }); });
  });
  $('q').value=''; $('stat').textContent = `${data.images.length} photos · ${labelsFlat.length} labels`;
  $('list').replaceChildren();
  view.i = 0; updateCounter(); resize(); whenReady(0, ()=>fitImage());
}

function search(raw){
  const q = norm(raw), qf = fuzz(raw);
  if(!q){ matches=[]; cur=-1; renderList();
    if(BOARD) $('stat').textContent = `${BOARD.images.length} photos · ${labelsFlat.length} labels`;
    updateCounter(); draw(); return; }
  const scored = [];
  for(const L of labelsFlat){
    let tier = -1;
    if(L.norm === q) tier = 0;
    else if(L.norm.includes(q)) tier = 1;
    else if(L.fuzz.includes(qf)) tier = 2;
    if(tier >= 0) scored.push(Object.assign({ tier }, L));
  }
  scored.sort((a,b)=> a.tier-b.tier || b.score-a.score);
  matches = scored; cur = matches.length ? 0 : -1;
  renderList();
  $('stat').textContent = matches.length
    ? `${matches.length} match${matches.length>1?'es':''} — click one, or press Enter`
    : `No match for “${raw}”`;
  if(cur>=0) goMatch(0); else { updateCounter(); draw(); }
}

function renderList(){
  const listEl = $('list'); listEl.replaceChildren();
  matches.forEach((m, k) => {
    const src = BOARD.images[m.i].source || ('photo ' + (m.i+1));
    const row = document.createElement('div'); row.className='row'+(k===cur?' active':'');
    const t=document.createElement('span'); t.className='t'; t.textContent=m.text;
    const s=document.createElement('span'); s.className='src'; s.textContent=src;
    const pc=document.createElement('span'); pc.className='m'; pc.textContent=Math.round(m.score*100)+'%';
    row.append(t, s, pc); row.onclick=()=>goMatch(k); listEl.appendChild(row);
  });
}
function updateCounter(){ $('counter').textContent = BOARD ? `Photo ${view.i+1} / ${BOARD.images.length}` : '—'; }

function goImage(i){
  if(!BOARD) return;
  const n = BOARD.images.length;
  view.i = ((i % n) + n) % n;        // wrap around
  updateCounter();
  whenReady(view.i, fitImage);
}

function goMatch(k){
  if(k<0 || k>=matches.length) return;
  cur = k; const m = matches[k];
  view.i = m.i;                       // switch to the match's photo first
  [...$('list').children].forEach((r,idx)=>r.classList.toggle('active', idx===cur));
  if($('list').children[cur]) $('list').children[cur].scrollIntoView({block:'nearest'});
  updateCounter();
  whenReady(m.i, ()=>{
    const vw=cv.clientWidth, vh=cv.clientHeight;
    const s = Math.max(0.05, Math.min(8, 0.35*Math.min(vw/Math.max(m.w,30), vh/Math.max(m.h,30))));
    view.s=s; view.tx=vw/2 - m.cx*s; view.ty=vh/2 - m.cy*s; draw();
  });
}

function whenReady(i, cb){
  const el = imgs[i];
  if(!el){ cb(); return; }
  if(el.complete && el.naturalWidth){ cb(); } else el.onload = ()=>cb();
}
function fitImage(){
  if(!BOARD) return;
  const im = BOARD.images[view.i], el = imgs[view.i];
  const W=(el&&el.naturalWidth)||im.w, H=(el&&el.naturalHeight)||im.h;
  const vw=cv.clientWidth, vh=cv.clientHeight;
  const s=Math.min(vw/W, vh/H)*0.96;
  view.s=s; view.tx=(vw-W*s)/2; view.ty=(vh-H*s)/2; draw();
}

function draw(){
  const vw=cv.clientWidth, vh=cv.clientHeight, dpr=window.devicePixelRatio||1;
  ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,vw,vh);
  ctx.fillStyle='#0b0e12'; ctx.fillRect(0,0,vw,vh);
  const el = imgs[view.i];
  if(el && el.complete && el.naturalWidth){
    ctx.imageSmoothingQuality='high';
    ctx.drawImage(el, view.tx, view.ty, el.naturalWidth*view.s, el.naturalHeight*view.s);
  }
  const T = p => [p[0]*view.s+view.tx, p[1]*view.s+view.ty];
  if(showAll){ ctx.lineWidth=1; ctx.strokeStyle='rgba(120,200,255,.35)';
    for(const L of labelsFlat){ if(L.i!==view.i) continue; poly(L.box,T); ctx.stroke(); } }
  ctx.lineWidth=2; ctx.strokeStyle='#ff9f43';
  matches.forEach((m,k)=>{ if(m.i===view.i && k!==cur){ poly(m.box,T); ctx.stroke(); } });
  if(cur>=0 && matches[cur] && matches[cur].i===view.i){
    const m=matches[cur];
    ctx.lineWidth=4; ctx.strokeStyle='#ffe14d'; ctx.shadowColor='#ffe14d'; ctx.shadowBlur=18;
    poly(m.box,T); ctx.stroke(); ctx.shadowBlur=0;
    const topY=Math.min(...m.box.map(p=>p[1])); const tp=T([m.cx-m.w/2, topY]);
    ctx.font='bold 15px Segoe UI'; const w=ctx.measureText(m.text).width+12;
    ctx.fillStyle='#ffe14d'; ctx.fillRect(tp[0], tp[1]-24, w, 20);
    ctx.fillStyle='#000'; ctx.fillText(m.text, tp[0]+6, tp[1]-9);
  }
}
function poly(box,T){ ctx.beginPath(); box.forEach((p,idx)=>{ const q=T(p);
  idx?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]); }); ctx.closePath(); }

function resize(){ const dpr=window.devicePixelRatio||1;
  cv.width=cv.clientWidth*dpr; cv.height=cv.clientHeight*dpr; draw(); }
window.addEventListener('resize', resize);

cv.addEventListener('wheel', e=>{ e.preventDefault();
  const f=e.deltaY<0?1.15:1/1.15, mx=e.offsetX, my=e.offsetY;
  const ix=(mx-view.tx)/view.s, iy=(my-view.ty)/view.s;
  view.s=Math.max(0.03,Math.min(20,view.s*f));
  view.tx=mx-ix*view.s; view.ty=my-iy*view.s; draw(); }, {passive:false});
let drag=null;
cv.addEventListener('mousedown', e=>{ drag={x:e.clientX,y:e.clientY,tx:view.tx,ty:view.ty}; cv.classList.add('drag'); });
window.addEventListener('mousemove', e=>{ if(!drag)return; view.tx=drag.tx+(e.clientX-drag.x); view.ty=drag.ty+(e.clientY-drag.y); draw(); });
window.addEventListener('mouseup', ()=>{ drag=null; cv.classList.remove('drag'); });

$('prev').onclick=()=>goImage(view.i-1);
$('next').onclick=()=>goImage(view.i+1);
$('fit').onclick=fitImage;
$('toggleAll').onclick=()=>{ showAll=!showAll; draw(); };
$('board').onchange=()=>loadBoard($('board').value);
let tmr; $('q').addEventListener('input', ()=>{ clearTimeout(tmr); tmr=setTimeout(()=>search($('q').value.trim()),120); });
$('q').addEventListener('keydown', e=>{ if(e.key==='Enter' && matches.length){ e.preventDefault(); goMatch((cur+1)%matches.length); } });

function overlay(msg, done){ $('overlay').style.display='flex'; $('omsg').textContent=msg;
  $('ospin').style.display = done ? 'none' : 'block'; $('oclose').style.display = done ? 'inline-block' : 'none'; }
function hideOverlay(){ $('overlay').style.display='none'; }
$('oclose').onclick=hideOverlay;

$('addBoard').onclick = async () => {
  overlay('Opening the folder chooser… pick the folder that has the board photos.', false);
  try {
    const r = await api('/api/add_board', { method:'POST', headers:{'Content-Type':'application/json'}, body:'{}' });
    if(!r.started){ overlay(r.msg || 'Busy processing another board.', true); return; }
  } catch(e){ overlay('Error: ' + e.message, true); return; }
  pollStatus();
};

$('importBoard').onclick = async () => {
  overlay('Opening the file chooser… pick a board file (.zip) someone shared with you.', false);
  try {
    const r = await api('/api/import_board', { method:'POST', headers:{'Content-Type':'application/json'}, body:'{}' });
    if(!r.started){ overlay(r.msg || 'Busy processing another board.', true); return; }
  } catch(e){ overlay('Error: ' + e.message, true); return; }
  pollStatus();
};

$('exportBoard').onclick = () => {
  const id = $('board').value;
  if(!id) return;
  const a = document.createElement('a');
  a.href = '/api/export/' + encodeURIComponent(id);
  document.body.appendChild(a); a.click(); a.remove();
};

$('deleteBoard').onclick = async () => {
  const sel = $('board'); const id = sel.value;
  if(!id) return;
  const name = sel.options[sel.selectedIndex] ? sel.options[sel.selectedIndex].textContent : id;
  if(!confirm('Delete board "' + name + '"?\n\nThis permanently removes its OCR data and photo copies from the tool. It cannot be undone.\n(Your original photo folder is not touched.)')) return;
  try {
    const r = await api('/api/delete_board', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ id }) });
    if(r.error){ overlay('Error: ' + r.error, true); return; }
  } catch(e){ overlay('Error: ' + e.message, true); return; }
  await loadBoards();
};
async function pollStatus(){
  let s;
  try { s = await api('/api/status'); } catch(e){ overlay('Error: ' + e.message, true); return; }
  if(s.state==='picking') overlay('Waiting for you to choose a folder…', false);
  else if(s.state==='starting') overlay('Starting…', false);
  else if(s.state==='processing') overlay(s.msg + (s.total ? `  (${Math.round(100*s.done/s.total)}%)` : ''), false);
  else if(s.state==='done'){ hideOverlay(); await loadBoards(s.board_id); return; }
  else if(s.state==='error'){ overlay('Error: ' + s.msg, true); return; }
  else if(s.state==='idle'){ hideOverlay(); return; }
  setTimeout(pollStatus, 1200);
}

$('q').focus();
loadBoards();
