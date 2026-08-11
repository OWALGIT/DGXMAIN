import json
D = json.load(open('findings.json'))
DATA = json.dumps(D, separators=(',',':'))

HTML = r"""<title>Cross-Asset Contagion Desk — 2023→2026</title>
<style>
:root{
  --bg:#f4f5f7; --panel:#ffffff; --panel2:#eef0f4; --ink:#171b22; --muted:#5b6472;
  --line:#d5d9e0; --grid:#e6e9ee; --accent:#b8860b; --accent2:#0e7490;
  --pos:#1a7f37; --neg:#c4341c; --hi:#0e7490; --shadow:0 1px 3px rgba(20,30,50,.08),0 8px 24px rgba(20,30,50,.06);
  --mono:ui-monospace,"SF Mono","Cascadia Mono","JetBrains Mono",Menlo,Consolas,monospace;
  --sans:system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;
}
:root:not([data-theme="light"]){ }
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0a0d13; --panel:#121722; --panel2:#0f141d; --ink:#d3dae6; --muted:#7f8b9e;
  --line:#232c3a; --grid:#1b2330; --accent:#e8b339; --accent2:#4dd0e1;
  --pos:#3fb950; --neg:#f85149; --hi:#4dd0e1; --shadow:0 1px 0 rgba(255,255,255,.03),0 12px 40px rgba(0,0,0,.5);
}}
:root[data-theme="dark"]{
  --bg:#0a0d13; --panel:#121722; --panel2:#0f141d; --ink:#d3dae6; --muted:#7f8b9e;
  --line:#232c3a; --grid:#1b2330; --accent:#e8b339; --accent2:#4dd0e1;
  --pos:#3fb950; --neg:#f85149; --hi:#4dd0e1; --shadow:0 1px 0 rgba(255,255,255,.03),0 12px 40px rgba(0,0,0,.5);
}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased;padding:0 0 80px}
.wrap{max-width:1180px;margin:0 auto;padding:0 22px}
h1,h2,h3{text-wrap:balance;margin:0}
.eyebrow{font-family:var(--mono);font-size:11.5px;letter-spacing:.22em;text-transform:uppercase;color:var(--accent)}
.lbl{font-family:var(--mono);font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
.pos{color:var(--pos)} .neg{color:var(--neg)} .hi{color:var(--hi)}

/* header */
header{border-bottom:1px solid var(--line);background:
  linear-gradient(180deg,color-mix(in srgb,var(--accent) 7%,var(--panel)),var(--panel));
  padding:30px 0 26px;margin-bottom:26px}
header .wrap{display:flex;flex-direction:column;gap:14px}
h1{font-size:clamp(26px,4.3vw,40px);font-weight:750;letter-spacing:-.02em;line-height:1.02}
.sub{color:var(--muted);max-width:60ch;font-size:15.5px}
.ticker{display:flex;flex-wrap:wrap;gap:7px;margin-top:4px}
.chip{font-family:var(--mono);font-size:11.5px;border:1px solid var(--line);border-radius:999px;
  padding:4px 11px;color:var(--muted);background:var(--panel2)}
.chip b{color:var(--ink)}

/* kpi row */
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:0 0 30px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:15px 16px;box-shadow:var(--shadow)}
.kpi .n{font-family:var(--mono);font-size:26px;font-weight:650;letter-spacing:-.02em;line-height:1.1}
.kpi .k{margin-top:5px}
.kpi .d{color:var(--muted);font-size:12.5px;margin-top:7px;line-height:1.4}

section{margin:0 0 40px}
.shead{display:flex;align-items:baseline;gap:12px;margin-bottom:6px;flex-wrap:wrap}
.shead h2{font-size:21px;font-weight:700;letter-spacing:-.01em}
.shead .n{font-family:var(--mono);color:var(--accent);font-size:13px}
.note{color:var(--muted);font-size:13.5px;max-width:74ch;margin:2px 0 16px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:var(--shadow)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.legend{display:flex;flex-wrap:wrap;gap:14px;margin:6px 2px 0;font-family:var(--mono);font-size:12px;color:var(--muted)}
.legend i{display:inline-block;width:11px;height:3px;border-radius:2px;vertical-align:middle;margin-right:6px}
.chartwrap{width:100%;overflow-x:auto}
svg{display:block;width:100%;height:auto}
text{font-family:var(--mono);fill:var(--muted)}

/* tables */
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:9px 10px;text-align:right;border-bottom:1px solid var(--grid);font-variant-numeric:tabular-nums;font-family:var(--mono)}
th:first-child,td:first-child{text-align:left;font-family:var(--sans)}
thead th{color:var(--muted);font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;border-bottom:1px solid var(--line)}
tbody tr:hover{background:var(--panel2)}
.tag{font-family:var(--mono);font-size:11px;padding:2px 8px;border-radius:999px;border:1px solid var(--line)}

.ll-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.ll-card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:13px 14px;box-shadow:var(--shadow)}
.ll-card .t{font-size:13px;font-weight:650;margin-bottom:2px}
.ll-card .m{font-family:var(--mono);font-size:12px;color:var(--muted);margin-bottom:8px}
.finding{border-left:2px solid var(--accent);padding:2px 0 2px 15px;margin:14px 0;color:var(--ink)}
.finding b{color:var(--accent)}
footer{color:var(--muted);font-size:12.5px;border-top:1px solid var(--line);padding-top:18px;margin-top:10px;font-family:var(--mono)}
@media(max-width:820px){.kpis{grid-template-columns:repeat(2,1fr)}.grid2{grid-template-columns:1fr}.ll-grid{grid-template-columns:1fr}}
@media(prefers-reduced-motion:no-preference){.kpi,.panel{transition:transform .15s ease}}
</style>

<header><div class="wrap">
  <div class="eyebrow">Cross-Asset Contagion Desk</div>
  <h1>How shocks travel through markets</h1>
  <p class="sub">A single unified daily panel — equities, volatility, rates, credit, commodities, FX, crypto, and geopolitical event signals — stitched together to trace how an external shock in one corner of the world propagates into prices somewhere else. The butterfly effect, quantified.</p>
  <div class="ticker" id="ticker"></div>
</div></header>

<div class="wrap">
  <div class="kpis" id="kpis"></div>

  <section id="s-timeline">
    <div class="shead"><span class="n">01</span><h2>The stress timeline</h2></div>
    <p class="note">S&amp;P 500 (rebased to 100) against the VIX, 2023→today, with four external shocks marked. Read it as cause and reaction: where the amber VIX line spikes, equities buckle — but each shock hits a <em>different</em> set of assets hardest.</p>
    <div class="panel"><div class="chartwrap"><svg id="timeline" viewBox="0 0 1120 420"></svg></div>
      <div class="legend"><span><i style="background:var(--accent2)"></i>S&amp;P 500 (rebased)</span><span><i style="background:var(--accent)"></i>VIX</span><span><i style="background:var(--neg)"></i>shock event</span></div>
    </div>
  </section>

  <section id="s-butterfly">
    <div class="shead"><span class="n">02</span><h2>The butterfly: Red Sea → the world's cargo</h2></div>
    <p class="note">Houthi attacks on shipping turned the Bab el-Mandeb Strait — the Red Sea gateway carrying ~12% of global trade — into a no-go zone. Container traffic there collapsed while the Cape of Good Hope detour surged. This is a physical shock you can watch propagate, days before it shows up in oil, freight, and supply-chain-sensitive equities.</p>
    <div class="panel"><div class="chartwrap"><svg id="butterfly" viewBox="0 0 1120 380"></svg></div>
      <div class="legend"><span><i style="background:var(--neg)"></i>Bab el-Mandeb (Red Sea) container transits</span><span><i style="background:var(--pos)"></i>Cape of Good Hope (detour)</span></div>
    </div>
    <div class="finding" id="butterfly-finding"></div>
  </section>

  <section id="s-corr">
    <div class="shead"><span class="n">03</span><h2>The correlation grid</h2></div>
    <p class="note">Daily co-movement across 24 instruments (returns; rates &amp; VIX as daily change), full window. Blue = move together, red = move opposite. This is the map of which levers are secretly the same lever.</p>
    <div class="panel"><div class="chartwrap"><svg id="heatmap" viewBox="0 0 1120 640"></svg></div></div>
  </section>

  <section id="s-regime">
    <div class="shead"><span class="n">04</span><h2>When everything becomes one trade</h2></div>
    <p class="note">Average pairwise correlation across nine global equity indices, on a rolling ~2-month window. When this line climbs, diversification quietly stops working — regional markets stop being regional and start moving as a single risk asset. The peaks are the regimes where contagion is easiest.</p>
    <div class="panel"><div class="chartwrap"><svg id="regime" viewBox="0 0 1120 300"></svg></div></div>
  </section>

  <section id="s-leadlag">
    <div class="shead"><span class="n">05</span><h2>Lead &amp; lag — who moves first</h2></div>
    <p class="note">Cross-correlation of an event signal against an asset at day-offsets −10…+10. A bar to the right of zero means the <em>signal leads</em> the asset by that many days; to the left, the market moved first and the signal only caught up. The honest result: at daily frequency most of these are weak — the clean propagation lives in discrete shocks (§02, §06), not in a steady daily rhythm.</p>
    <div class="ll-grid" id="leadlag"></div>
  </section>

  <section id="s-events">
    <div class="shead"><span class="n">06</span><h2>Event studies — the reaction fingerprints</h2></div>
    <p class="note">Move from 3 days before to 5 days after each shock. Every crisis has a signature: a banking scare crushes oil and lifts gold; a Middle-East war does the opposite to oil; a shipping halt lands on China and freight.</p>
    <div class="panel" style="overflow-x:auto"><table id="events"></table></div>
  </section>

  <section id="s-safe">
    <div class="shead"><span class="n">07</span><h2>What actually protects you</h2></div>
    <div class="grid2">
      <div class="panel"><div class="lbl" id="safe-desc" style="margin-bottom:12px"></div><table id="safe"></table></div>
      <div class="panel">
        <div class="lbl" style="margin-bottom:12px">Strongest linkages (|r|)</div>
        <table id="topcorr"></table>
      </div>
    </div>
  </section>

  <footer id="foot"></footer>
</div>

<script>
const D=__DATA__;
const css=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const C={ink:()=>css('--ink'),mut:()=>css('--muted'),acc:()=>css('--accent'),acc2:()=>css('--accent2'),
  pos:()=>css('--pos'),neg:()=>css('--neg'),grid:()=>css('--grid'),line:()=>css('--line'),panel:()=>css('--panel')};
const SVG='http://www.w3.org/2000/svg';
function el(n,a){const e=document.createElementNS(SVG,n);for(const k in a)e.setAttribute(k,a[k]);return e;}
function fmt(x,d=2){return x==null||isNaN(x)?'–':(+x).toFixed(d);}
function signed(x,d=1){if(x==null||isNaN(x))return '–';const s=(+x>=0?'+':'')+(+x).toFixed(d);return s;}

/* ---- ticker + kpis ---- */
(function(){
  const m=D.meta;
  document.getElementById('ticker').innerHTML=
    [`panel <b>${m.rows.toLocaleString()}</b> days`,`<b>${m.cols}</b> series`,
     `${m.start} → <b>${m.end}</b>`,`73 datasets · 2.4&nbsp;GB · Storj S3`]
    .map(t=>`<span class="chip">${t}</span>`).join('');
  const sys=D.syscorr.vals, sysNow=sys[sys.length-1], sysMax=Math.max(...sys);
  const spxDD=Math.min(...D.timeline.dd.filter(v=>v!=null));
  const cn=D.leadlag['CrashNews -> VIX'];
  const k=[
    {n:signed(D.top_corr.find(p=>p.a=='SPX'&&p.b=='VIX').r,2),k:'SPX ↔ VIX',d:'daily-return correlation — the market’s built-in fear gauge, inverted and tight'},
    {n:fmt(sysNow,2),k:'equity co-movement now',d:`avg pairwise corr of 9 world indices · peaked at ${fmt(sysMax,2)} in stress`},
    {n:signed(spxDD,1)+'%',k:'deepest S&P drawdown',d:'peak-to-trough over the window, weekly close'},
    {n:D.safehaven.vals.Gold>0?'Gold':'—',k:'best crisis hedge',d:`+${fmt(D.safehaven.vals.Gold,2)}% avg on the worst-5% S&P days (n=${D.safehaven.n_days})`},
  ];
  document.getElementById('kpis').innerHTML=k.map(x=>
    `<div class="kpi"><div class="n">${x.n}</div><div class="k lbl">${x.k}</div><div class="d">${x.d}</div></div>`).join('');
})();

/* ---- generic line chart on svg ---- */
function axes(svg,W,H,pad,xr,yr,yticks,fmtY,xlabels){
  // grid + y ticks
  yticks.forEach(t=>{
    const y=pad.t+(1-(t-yr[0])/(yr[1]-yr[0]))*(H-pad.t-pad.b);
    svg.appendChild(el('line',{x1:pad.l,y1:y,x2:W-pad.r,y2:y,stroke:C.grid(),'stroke-width':1}));
    const tx=el('text',{x:pad.l-8,y:y+4,'text-anchor':'end','font-size':11});tx.textContent=fmtY(t);svg.appendChild(tx);
  });
  (xlabels||[]).forEach(o=>{
    const x=pad.l+((o.i-xr[0])/(xr[1]-xr[0]))*(W-pad.l-pad.r);
    const tx=el('text',{x,y:H-pad.b+18,'text-anchor':'middle','font-size':11});tx.textContent=o.t;svg.appendChild(tx);
  });
}
function path(svg,pts,xr,yr,W,H,pad,color,wd){
  let d='';let started=false;
  pts.forEach(p=>{
    if(p.v==null||isNaN(p.v)){started=false;return;}
    const x=pad.l+((p.i-xr[0])/(xr[1]-xr[0]))*(W-pad.l-pad.r);
    const y=pad.t+(1-(p.v-yr[0])/(yr[1]-yr[0]))*(H-pad.t-pad.b);
    d+=(started?'L':'M')+x.toFixed(1)+' '+y.toFixed(1)+' ';started=true;
  });
  svg.appendChild(el('path',{d,fill:'none',stroke:color,'stroke-width':wd||2,'stroke-linejoin':'round','stroke-linecap':'round'}));
}
function monthTicks(dates){
  const out=[];let last='';
  dates.forEach((d,i)=>{const ym=d.slice(0,7);const yr=d.slice(0,4);
    if(d.slice(5,7)=='01'&&yr!=last){out.push({i,t:yr});last=yr;}});
  return out;
}

/* ---- 01 timeline ---- */
(function(){
  const svg=document.getElementById('timeline'),W=1120,H=420,pad={l:46,r:52,t:18,b:34};
  const T=D.timeline,N=T.dates.length,xr=[0,N-1];
  const spx=T.spx,vix=T.vix;
  const syr=[Math.min(...spx.filter(v=>v!=null))*0.98,Math.max(...spx.filter(v=>v!=null))*1.02];
  const vyr=[10,Math.max(...vix.filter(v=>v!=null))*1.1];
  axes(svg,W,H,pad,xr,syr,[80,100,120,140,160,180].filter(t=>t>=syr[0]&&t<=syr[1]),v=>v,monthTicks(T.dates));
  // vix right axis ticks
  [15,25,35,45].forEach(t=>{if(t<=vyr[1]){const y=pad.t+(1-(t-vyr[0])/(vyr[1]-vyr[0]))*(H-pad.t-pad.b);
    const tx=el('text',{x:W-pad.r+8,y:y+4,'font-size':11,fill:C.acc()});tx.textContent=t;svg.appendChild(tx);}});
  // event markers
  const EV=D.events.map(e=>({d:e.date,n:e.name}));
  EV.forEach(e=>{let i=T.dates.findIndex(x=>x>=e.d);if(i<0)i=N-1;
    const x=pad.l+(i/(N-1))*(W-pad.l-pad.r);
    svg.appendChild(el('line',{x1:x,y1:pad.t,x2:x,y2:H-pad.b,stroke:C.neg(),'stroke-width':1,'stroke-dasharray':'3 3',opacity:.7}));
    const tx=el('text',{x:x+4,y:pad.t+12,'font-size':10.5,fill:C.neg()});tx.textContent=e.n;svg.appendChild(tx);});
  path(svg,vix.map((v,i)=>({i,v})),xr,vyr,W,H,pad,C.acc(),1.6);
  path(svg,spx.map((v,i)=>({i,v})),xr,syr,W,H,pad,C.acc2(),2.4);
})();

/* ---- 02 butterfly ---- */
(function(){
  const svg=document.getElementById('butterfly'),W=1120,H=380,pad={l:46,r:20,t:18,b:34};
  const T=D.timeline,N=T.dates.length,xr=[0,N-1];
  const rs=T.redsea,cp=T.cape;
  const all=rs.concat(cp).filter(v=>v!=null);
  const yr=[0,Math.max(...all)*1.1];
  const yt=[];for(let t=0;t<=yr[1];t+=20)yt.push(t);
  axes(svg,W,H,pad,xr,yr,yt,v=>v,monthTicks(T.dates));
  path(svg,cp.map((v,i)=>({i,v})),xr,yr,W,H,pad,C.pos(),2.2);
  path(svg,rs.map((v,i)=>({i,v})),xr,yr,W,H,pad,C.neg(),2.2);
  // mark Red Sea escalation
  const e='2023-12-18';let i=T.dates.findIndex(x=>x>=e);
  const x=pad.l+(i/(N-1))*(W-pad.l-pad.r);
  svg.appendChild(el('line',{x1:x,y1:pad.t,x2:x,y2:H-pad.b,stroke:C.mut(),'stroke-width':1,'stroke-dasharray':'3 3'}));
  const tx=el('text',{x:x+5,y:pad.t+12,'font-size':10.5,fill:C.mut()});tx.textContent='carriers divert (Dec 2023)';svg.appendChild(tx);
  // finding text
  const rsPre=rs.slice(40,52).filter(v=>v!=null),rsNow=rs.slice(-8).filter(v=>v!=null);
  const a=rsPre.reduce((s,v)=>s+v,0)/rsPre.length,b=rsNow.reduce((s,v)=>s+v,0)/rsNow.length;
  document.getElementById('butterfly-finding').innerHTML=
    `<b>Red Sea transits fell ~${Math.round((1-b/a)*100)}%</b> from a pre-crisis baseline of ~${fmt(a,0)} to ~${fmt(b,0)} container ships/period, while Cape-of-Good-Hope traffic absorbed the diversion. A one-week attack headline becomes a months-long re-routing of the planet's cargo — and a persistent premium on anything that has to move by sea.`;
})();

/* ---- 03 heatmap ---- */
(function(){
  const svg=document.getElementById('heatmap'),W=1120,H=640;
  const L=D.corr.labels,M=D.corr.matrix,n=L.length;
  const padL=92,padT=92,cell=(W-padL-14)/n,gridH=cell*n;
  function col(r){if(r==null||isNaN(r))return C.panel();
    const t=Math.max(-1,Math.min(1,r));
    // diverging: neg->red, 0->neutral, pos->teal
    const neg=[196,52,28],mid=[130,140,155],pos=[14,116,144];
    let a,b,f;if(t<0){a=mid;b=neg;f=-t;}else{a=mid;b=pos;f=t;}
    const c=a.map((v,k)=>Math.round(v+(b[k]-v)*Math.sqrt(f)));
    return `rgb(${c[0]},${c[1]},${c[2]})`;}
  for(let i=0;i<n;i++){for(let j=0;j<n;j++){
    svg.appendChild(el('rect',{x:padL+j*cell,y:padT+i*cell,width:cell-1,height:cell-1,rx:2,fill:col(M[i][j])}));
  }}
  L.forEach((l,i)=>{
    const ty=el('text',{x:padL-6,y:padT+i*cell+cell/2+3,'text-anchor':'end','font-size':10.5,fill:C.ink()});ty.textContent=l;svg.appendChild(ty);
    const tx=el('text',{x:padL+i*cell+cell/2,y:padT-6,'font-size':10.5,fill:C.ink(),transform:`rotate(-52 ${padL+i*cell+cell/2} ${padT-6})`,'text-anchor':'start'});tx.textContent=l;svg.appendChild(tx);
  });
  // scale legend
  const lx=padL,ly=padT+gridH+26;
  for(let s=0;s<=40;s++){svg.appendChild(el('rect',{x:lx+s*5,y:ly,width:5,height:11,fill:col(-1+s/20)}));}
  [['−1',0],['0',100],['+1',200]].forEach(([t,dx])=>{const e=el('text',{x:lx+dx,y:ly+26,'font-size':11});e.textContent=t;svg.appendChild(e);});
  const cap=el('text',{x:lx+215,y:ly+10,'font-size':11});cap.textContent='← move opposite      move together →';svg.appendChild(cap);
})();

/* ---- 04 regime ---- */
(function(){
  const svg=document.getElementById('regime'),W=1120,H=300,pad={l:44,r:16,t:16,b:32};
  const s=D.syscorr,N=s.dates.length,xr=[0,N-1];
  const yr=[Math.min(...s.vals)*0.9,Math.max(...s.vals)*1.05];
  axes(svg,W,H,pad,xr,yr,[0.2,0.3,0.4,0.5,0.6].filter(t=>t>=yr[0]&&t<=yr[1]),v=>v.toFixed(1),monthTicks(s.dates));
  // area fill
  const pts=s.vals.map((v,i)=>({i,v}));
  let d='';pts.forEach((p,k)=>{const x=pad.l+(p.i/(N-1))*(W-pad.l-pad.r);const y=pad.t+(1-(p.v-yr[0])/(yr[1]-yr[0]))*(H-pad.t-pad.b);d+=(k?'L':'M')+x.toFixed(1)+' '+y.toFixed(1)+' ';});
  const x0=pad.l,x1=W-pad.r,yb=H-pad.b;
  svg.appendChild(el('path',{d:`${d}L${x1} ${yb} L${x0} ${yb} Z`,fill:C.acc(),opacity:.12}));
  path(svg,pts,xr,yr,W,H,pad,C.acc(),2.2);
})();

/* ---- 05 lead-lag small multiples ---- */
(function(){
  const box=document.getElementById('leadlag');
  Object.entries(D.leadlag).forEach(([name,o])=>{
    const div=document.createElement('div');div.className='ll-card';
    const nn=name.split(' -> ');
    const w=300,h=110,pad={l:6,r:6,t:8,b:16},mid=(pad.l+ (w-pad.r))/2;
    const mx=Math.max(0.06,...o.corr.filter(v=>v!=null).map(v=>Math.abs(v)));
    const bw=(w-pad.l-pad.r)/o.lags.length;
    let bars='';
    o.corr.forEach((v,i)=>{if(v==null)return;const x=pad.l+i*bw;
      const bh=Math.abs(v)/mx*((h-pad.t-pad.b)/2);
      const y0=(pad.t+(h-pad.b))/2;
      const y=v>=0?y0-bh:y0;
      const isBest=o.lags[i]===o.best_lag;
      bars+=`<rect x="${x+0.5}" y="${y}" width="${bw-1}" height="${Math.max(0.6,bh)}" rx="1" fill="${isBest?'var(--accent)':(v>=0?'var(--accent2)':'var(--neg)')}" opacity="${isBest?1:.55}"/>`;});
    const y0=(pad.t+(h-pad.b))/2;
    const zx=pad.l+((10-0)/1)*0; // zero-lag position = index 10
    const zeroX=pad.l+10*bw+bw/2;
    div.innerHTML=`<div class="t">${nn[0]} <span style="color:var(--muted)">→</span> ${nn[1]}</div>`+
      `<div class="m">best offset <b style="color:var(--accent)">${signed(o.best_lag,0)}d</b> · r=${signed(o.best_corr,2)}</div>`+
      `<svg viewBox="0 0 ${w} ${h}"><line x1="${pad.l}" y1="${y0}" x2="${w-pad.r}" y2="${y0}" stroke="var(--line)"/>`+
      `<line x1="${zeroX}" y1="${pad.t}" x2="${zeroX}" y2="${h-pad.b}" stroke="var(--grid)" stroke-dasharray="2 2"/>`+
      bars+
      `<text x="${pad.l}" y="${h-4}" font-size="9">−10d</text>`+
      `<text x="${zeroX}" y="${h-4}" font-size="9" text-anchor="middle">0</text>`+
      `<text x="${w-pad.r}" y="${h-4}" font-size="9" text-anchor="end">+10d</text></svg>`;
    box.appendChild(div);
  });
})();

/* ---- 06 events table ---- */
(function(){
  const cols=['SPX','HangSeng','VIX','WTI','Brent','Gold','DXY','UST10Y','BTC','TLT'];
  const pct=new Set(['SPX','HangSeng','WTI','Brent','Gold','DXY','BTC','TLT']);
  const t=document.getElementById('events');
  let h='<thead><tr><th>Shock</th><th>Date</th>'+cols.map(c=>`<th>${c}</th>`).join('')+'</tr></thead><tbody>';
  D.events.forEach(e=>{
    h+=`<tr><td>${e.name}</td><td style="color:var(--muted)">${e.date}</td>`+
      cols.map(c=>{const v=e.moves[c];if(v==null)return '<td>–</td>';
        const cls=v>0?'pos':(v<0?'neg':'');const suf=pct.has(c)?'%':'';
        return `<td class="${cls}">${signed(v,pct.has(c)?1:2)}${suf}</td>`;}).join('')+'</tr>';
  });
  t.innerHTML=h+'</tbody>';
})();

/* ---- 07 safehaven + topcorr ---- */
(function(){
  document.getElementById('safe-desc').textContent='Avg move on the worst-5% S&P days · n='+D.safehaven.n_days;
  const s=D.safehaven.vals;
  const order=['Gold','TLT','DXY','USDJPY','BTC','WTI','VIX'];
  let h='<thead><tr><th>Asset</th><th>avg move</th><th></th></tr></thead><tbody>';
  order.forEach(a=>{if(!(a in s))return;const v=s[a];const isVix=a=='VIX';
    const cls=isVix?(v>0?'neg':'pos'):(v>0?'pos':'neg');
    const suf=isVix?' pts':'%';
    const good=isVix? v>0 : v>0;
    h+=`<tr><td>${a}</td><td class="${cls}">${signed(v,2)}${suf}</td><td style="color:var(--muted)">${a=='Gold'||a=='TLT'||a=='USDJPY'||(a=='VIX')?'hedge':'risk-on'}</td></tr>`;});
  document.getElementById('safe').innerHTML=h+'</tbody>';

  let c='<thead><tr><th>Pair</th><th>r</th></tr></thead><tbody>';
  D.top_corr.slice(0,10).forEach(p=>{const cls=p.r>0?'pos':'neg';
    c+=`<tr><td>${p.a} ~ ${p.b}</td><td class="${cls}">${signed(p.r,2)}</td></tr>`;});
  document.getElementById('topcorr').innerHTML=c+'</tbody>';
})();

document.getElementById('foot').innerHTML=
  `Built from a live pull of the <b>market-data</b> Storj bucket · 1,683 parquet files · unified daily panel ${D.meta.start}→${D.meta.end} · `+
  `correlations on daily returns, rates &amp; VIX on daily change · event studies [−3d,+5d] · lead-lag = cross-correlation at day offsets. Signals are exploratory, not trading advice.`;
</script>
"""

open('dashboard.html','w').write(HTML.replace('__DATA__', DATA))
print("wrote dashboard.html", len(HTML), "bytes template")
