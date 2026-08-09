import json
D=json.load(open('findings2.json'))
DATA=json.dumps(D,separators=(',',':'))
HTML=r"""<title>The Butterfly, Tested — cross-domain signals vs markets</title>
<style>
:root{--bg:#f5f4f1;--panel:#fff;--panel2:#eeece7;--ink:#1b1a17;--muted:#6b6459;
 --line:#dcd8cf;--grid:#e8e5de;--accent:#9b6b1f;--good:#1a7f37;--bad:#b3341c;--cool:#0e6f83;
 --shadow:0 1px 3px rgba(40,35,25,.07),0 10px 30px rgba(40,35,25,.06);
 --mono:ui-monospace,"SF Mono","JetBrains Mono",Menlo,Consolas,monospace;
 --sans:system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;
 --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --bg:#14130f;--panel:#1c1a15;--panel2:#171510;--ink:#e9e4d8;--muted:#9a917f;
 --line:#332f26;--grid:#241f18;--accent:#e0a63a;--good:#5fce6e;--bad:#f0664f;--cool:#4fc3d8;
 --shadow:0 1px 0 rgba(255,255,255,.03),0 14px 44px rgba(0,0,0,.55);}}
:root[data-theme="dark"]{--bg:#14130f;--panel:#1c1a15;--panel2:#171510;--ink:#e9e4d8;--muted:#9a917f;
 --line:#332f26;--grid:#241f18;--accent:#e0a63a;--good:#5fce6e;--bad:#f0664f;--cool:#4fc3d8;
 --shadow:0 1px 0 rgba(255,255,255,.03),0 14px 44px rgba(0,0,0,.55);}
*{box-sizing:border-box}html,body{margin:0}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.58;padding:0 0 80px;-webkit-font-smoothing:antialiased}
.wrap{max-width:1160px;margin:0 auto;padding:0 22px}
h1,h2,h3{text-wrap:balance;margin:0}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
.lbl{font-family:var(--mono);font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
.eyebrow{font-family:var(--mono);font-size:11.5px;letter-spacing:.24em;text-transform:uppercase;color:var(--accent)}
header{padding:46px 0 30px;border-bottom:1px solid var(--line);margin-bottom:28px;
 background:linear-gradient(180deg,color-mix(in srgb,var(--accent) 8%,var(--panel)),var(--bg))}
header .wrap{display:flex;flex-direction:column;gap:15px}
h1{font-family:var(--serif);font-size:clamp(30px,5vw,52px);font-weight:600;line-height:1.02;letter-spacing:-.015em}
.dek{font-family:var(--serif);font-size:clamp(17px,2.2vw,21px);color:var(--muted);max-width:65ch;line-height:1.5}
.ticker{display:flex;flex-wrap:wrap;gap:7px;margin-top:2px}
.chip{font-family:var(--mono);font-size:11.5px;border:1px solid var(--line);border-radius:999px;padding:4px 11px;color:var(--muted);background:var(--panel2)}
.chip b{color:var(--ink)}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:34px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:16px;box-shadow:var(--shadow)}
.kpi .n{font-family:var(--mono);font-size:27px;font-weight:650;letter-spacing:-.02em;line-height:1.05}
.kpi .k{margin-top:6px}.kpi .d{color:var(--muted);font-size:12.5px;margin-top:7px;line-height:1.4}
section{margin-bottom:44px}
.shead{display:flex;align-items:baseline;gap:12px;margin-bottom:6px;flex-wrap:wrap}
.shead h2{font-family:var(--serif);font-size:24px;font-weight:600;letter-spacing:-.01em}
.shead .n{font-family:var(--mono);color:var(--accent);font-size:13px}
.note{color:var(--muted);font-size:14px;max-width:78ch;margin:2px 0 18px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:var(--shadow)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.chartwrap{width:100%;overflow-x:auto}svg{display:block;width:100%;height:auto}
text{font-family:var(--mono);fill:var(--muted)}
.chain{display:grid;grid-template-columns:1fr auto;gap:6px 12px;align-items:center;padding:9px 2px;border-bottom:1px solid var(--grid)}
.chain:last-child{border-bottom:0}
.chain .flow{font-size:13.5px}
.chain .flow b{font-family:var(--mono);font-weight:600}
.chain .sig{color:var(--ink)} .chain .mkt{color:var(--ink)}
.chain .lag{font-family:var(--mono);font-size:11px;color:var(--accent);padding:1px 7px;border:1px solid var(--line);border-radius:999px;margin:0 4px}
.chain .r{font-family:var(--mono);font-variant-numeric:tabular-nums;font-weight:650;text-align:right}
.chain .meta{font-family:var(--mono);font-size:10.5px;color:var(--muted);grid-column:1/-1;margin-top:-2px}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:7px;vertical-align:middle}
.g{color:var(--good)}.b{color:var(--bad)}.c{color:var(--cool)}
.bars{display:flex;flex-direction:column;gap:9px}
.bar{display:grid;grid-template-columns:130px 1fr 60px;align-items:center;gap:10px;font-size:13px}
.bar .track{height:16px;background:var(--panel2);border-radius:5px;overflow:hidden;border:1px solid var(--grid)}
.bar .fill{height:100%;background:var(--accent);border-radius:5px 0 0 5px}
.bar .v{font-family:var(--mono);font-size:12px;color:var(--muted);text-align:right}
.finding{border-left:2px solid var(--accent);padding:3px 0 3px 15px;margin:16px 0;font-family:var(--serif);font-size:16.5px;line-height:1.5}
.finding b{color:var(--accent);font-family:var(--sans);font-weight:650}
.caveat{background:var(--panel2);border:1px dashed var(--line);border-radius:12px;padding:14px 16px;font-size:13.5px;color:var(--muted)}
.caveat b{color:var(--ink)}
footer{color:var(--muted);font-size:12.5px;border-top:1px solid var(--line);padding-top:18px;font-family:var(--mono);line-height:1.6}
@media(max-width:820px){.kpis{grid-template-columns:repeat(2,1fr)}.grid2{grid-template-columns:1fr}.bar{grid-template-columns:110px 1fr 52px}}
</style>
<header><div class="wrap">
 <div class="eyebrow">Everything → Markets · a cross-domain test</div>
 <h1>The butterfly, put on trial</h1>
 <p class="dek">A butterfly in Australia, a tornado in Texas. We took 28 signals from nine worlds — weather, war, shipping, disease-fear, earthquakes, solar storms, climate, policy uncertainty, and crowd attention — and asked a hard question of each: do you actually lead the markets, or only appear to? Then we let a bootstrap try to kill every answer.</p>
 <div class="ticker" id="ticker"></div>
</div></header>
<div class="wrap">
 <div class="kpis" id="kpis"></div>

 <section>
  <div class="shead"><span class="n">01</span><h2>What actually leads — and what was a mirage</h2></div>
  <p class="note">Every pair with a raw lead-correlation |r|≥0.10 was tested against a null built by circularly rotating the signal 500× (which preserves its own rhythm but destroys any true timing link). A relationship is called <b>robust</b> only if it beats that null (p&lt;0.05), the signal actually moves on most days (not a rare spike), and |r|≥0.12. Left: survivors. Right: seductive numbers that failed.</p>
  <div class="grid2">
   <div class="panel"><div class="lbl" style="color:var(--good);margin-bottom:10px">◆ Robust — survives the test</div><div id="robust"></div></div>
   <div class="panel"><div class="lbl" style="color:var(--bad);margin-bottom:10px">✕ Mirage — rejected</div><div id="mirage"></div></div>
  </div>
  <div class="finding" id="thesis"></div>
 </section>

 <section>
  <div class="shead"><span class="n">02</span><h2>Which worlds carry any signal at all</h2></div>
  <p class="note">Of every candidate lead a domain produced, the share that survived the bootstrap. Human <em>attention</em> to fear leads; raw physical-event feeds mostly don't — at least not as a steady daily rhythm.</p>
  <div class="panel"><div class="bars" id="domains"></div></div>
 </section>

 <section>
  <div class="shead"><span class="n">03</span><h2>The full cross-domain grid</h2></div>
  <p class="note">Best <em>leading</em> correlation (signal → market, 1–10 days ahead) for all 28 signals × 25 markets. Blue = signal rise leads a market rise; red = leads a fall. Cells with a ring survived the significance test — notice how few they are, and how many strong-looking colors did <em>not</em> survive.</p>
  <div class="panel"><div class="chartwrap"><svg id="heat" viewBox="0 0 1120 780"></svg></div></div>
 </section>

 <section>
  <div class="shead"><span class="n">04</span><h2>How to read this honestly</h2></div>
  <div class="caveat" id="caveat"></div>
 </section>
 <footer id="foot"></footer>
</div>
<script>
const D=__DATA__;
const css=k=>getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const SVG='http://www.w3.org/2000/svg';
const el=(n,a)=>{const e=document.createElementNS(SVG,n);for(const k in a)e.setAttribute(k,a[k]);return e;};
const sgn=(x,d=2)=>x==null?'–':(x>=0?'+':'')+(+x).toFixed(d);

(function(){
 const m=D.meta,s=D.sig_meta;
 document.getElementById('ticker').innerHTML=[
   `<b>${m.signals}</b> signals · 9 domains`,`<b>${m.markets}</b> markets`,
   `<b>${m.pairs.toLocaleString()}</b> pairs × 14 lags tested`,`bootstrap <b>${s.bootstrap}×</b>`,
   `${m.start} → ${m.end}`].map(t=>`<span class="chip">${t}</span>`).join('');
 const doms=Object.entries(D.domain_verdict);
 const topDom=doms.filter(([k])=>k=='Attention')[0][1];
 const k=[
  {n:D.sig_meta.n_robust,k:'robust leads',d:`out of ${D.sig_meta.n_candidates} candidates with |r|≥0.10 — the rest are noise`},
  {n:'Attention',k:'strongest domain',d:`${topDom.robust}/${topDom.tested} leads survived — Wikipedia fear-lookups beat every physical feed`},
  {n:'0/48',k:'war/conflict leads',d:'the GDELT conflict feed produced zero robust daily leads in this window'},
  {n:'−0.54→✕',k:'biggest mirage killed',d:'earthquakes “leading” copper — a sparse-signal artifact, rejected'},
 ];
 document.getElementById('kpis').innerHTML=k.map(x=>`<div class="kpi"><div class="n">${x.n}</div><div class="k lbl">${x.k}</div><div class="d">${x.d}</div></div>`).join('');
})();

function chainRow(c,good){
 const col=good?(c.r>=0?'var(--good)':'var(--cool)'):'var(--bad)';
 const why=good?`p=${c.p} · leads ${c.lag}d · moves ${(c.active*100).toFixed(0)}% of days`
   :(c.active<0.5?`rejected: sparse signal (moves only ${(c.active*100).toFixed(0)}% of days)`:`rejected: p=${c.p} (fails bootstrap)`);
 const nice=s=>s.replace(/^([A-Z]+)_/,'').replace(/_/g,' ');
 return `<div class="chain"><div class="flow"><span class="dot" style="background:${col}"></span>`+
  `<b class="sig">${nice(c.signal)}</b><span class="lag">+${c.lag}d</span><b class="mkt">${c.market}</b></div>`+
  `<div class="r" style="color:${col}">${sgn(c.r)}</div><div class="meta">${why}</div></div>`;
}
document.getElementById('robust').innerHTML=D.robust_chains.slice(0,16).map(c=>chainRow(c,true)).join('');
document.getElementById('mirage').innerHTML=D.spurious_examples.slice(0,12).map(c=>chainRow(c,false)).join('');

(function(){
 const dv=Object.entries(D.domain_verdict).map(([k,v])=>({k,...v,rate:v.tested?v.robust/v.tested:0}))
   .sort((a,b)=>b.rate-a.rate);
 const mx=Math.max(...dv.map(d=>d.rate),0.01);
 document.getElementById('domains').innerHTML=dv.map(d=>
  `<div class="bar"><div>${d.k}</div><div class="track"><div class="fill" style="width:${(d.rate/mx*100).toFixed(0)}%;background:${d.robust?'var(--accent)':'var(--line)'}"></div></div>`+
  `<div class="v">${d.robust}/${d.tested}</div></div>`).join('');
})();

document.getElementById('thesis').innerHTML=
 `The physical shocks are real — but as <b>continuous daily predictors they wash into noise</b>. What survives the test is <b>human attention to fear</b>: the day “Margin call”, “Recession” and “Bank run” get looked up, volatility and equities move within 1–3 days. The butterfly you can trade is a psychological one, not a meteorological one.`;

/* heatmap 28x25 */
(function(){
 const svg=document.getElementById('heat'),W=1120,H=780;
 const S=D.signals,M=D.matrix,Mk=D.markets,ns=S.length,nm=Mk.length;
 const robustSet=new Set(D.robust_chains.map(c=>c.signal+'|'+c.market));
 const padL=150,padT=118,cw=(W-padL-12)/nm,ch=(H-padT-24)/ns;
 const col=r=>{if(r==null)return 'var(--panel2)';const t=Math.max(-.5,Math.min(.5,r))/0.5;
   const mid=[150,150,150];let a,b,f;if(t<0){a=mid;b=[179,52,28];f=-t}else{a=mid;b=[14,111,131];f=t}
   const c=a.map((v,k)=>Math.round(v+(b[k]-v)*Math.sqrt(f)));return `rgb(${c[0]},${c[1]},${c[2]})`;};
 for(let i=0;i<ns;i++)for(let j=0;j<nm;j++){
   const r=M[i][j];const x=padL+j*cw,y=padT+i*ch;
   svg.appendChild(el('rect',{x,y,width:cw-1,height:ch-1,rx:1.5,fill:col(r)}));
   if(robustSet.has(S[i]+'|'+Mk[j]))
     svg.appendChild(el('rect',{x:x+.5,y:y+.5,width:cw-2,height:ch-2,rx:1.5,fill:'none',stroke:css('--ink'),'stroke-width':1.6}));
 }
 S.forEach((s,i)=>{const t=el('text',{x:padL-6,y:padT+i*ch+ch/2+3,'text-anchor':'end','font-size':9.5,fill:css('--ink')});t.textContent=s.replace(/_/g,' ');svg.appendChild(t);});
 Mk.forEach((m,j)=>{const cx=padL+j*cw+cw/2;const t=el('text',{x:cx,y:padT-6,'font-size':9.5,fill:css('--ink'),transform:`rotate(-55 ${cx} ${padT-6})`});t.textContent=m;svg.appendChild(t);});
 // legend
 const lx=padL,ly=H-8;for(let k=0;k<=40;k++)svg.appendChild(el('rect',{x:lx+k*5,y:ly-10,width:5,height:9,fill:col(-.5+k/40)}));
 [['−.5',0],['0',100],['+.5',200]].forEach(([t,dx])=>{const e=el('text',{x:lx+dx,y:ly+4,'font-size':10});e.textContent=t;svg.appendChild(e);});
 const r=el('text',{x:lx+220,y:ly-2,'font-size':10});r.textContent='□ ring = survived significance test';svg.appendChild(r);
})();

document.getElementById('caveat').innerHTML=
 `<b>Correlation is not a mechanism.</b> The bootstrap kills sparse-signal mirages (the M6-earthquake “effects”) and pure multiple-testing luck, but it can’t certify causation. One survivor — <b>earthquake count → copper (−1d)</b> — clears the statistics yet the sign is backwards for a supply-shock story, so treat it as an open question, not a trade. `+
 `The honest reading of ~9,800 tested relationships: a handful of <b>attention</b> and <b>shipping</b> links are real and modest (|r|≈0.15–0.22); most of the sky is noise. The dramatic butterfly chains live in <em>discrete shocks</em> (see the event-study desk), not in a steady daily signal.`;

document.getElementById('foot').innerHTML=
 `Built from the <b>market-data</b> Storj bucket · 28 event signals × 25 markets, daily ${D.meta.start}→${D.meta.end} · `+
 `signal innovation = z-scored daily change · leads tested at +1…+10 days · significance = circular-rotation bootstrap (500×), p&lt;0.05 + non-sparse + |r|≥0.12. Exploratory research, not trading advice.`;
</script>
"""
open('dashboard2.html','w').write(HTML.replace('__DATA__',DATA))
print("wrote dashboard2.html")
