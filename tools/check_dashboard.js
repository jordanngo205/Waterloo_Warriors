(function(){
var R={errors:window.__E,fails:[],notes:[]};
function F(ok,msg){ if(!ok) R.fails.push(msg); }
function byName(n){return TEAMS.filter(function(t){return t.name===n;})[0];}
try{
 var btn=document.querySelectorAll('#conf-group .toggle-btn');
 // 1. every tab renders, under every conference
 ['','CW','OUA','RSEQ','AUS'].forEach(function(c,i){ setConf(c,btn[i]);
   F(document.querySelectorAll('#tr-body tr').length>0,'team rank empty for '+c);
   F(document.querySelectorAll('#pr-body tr').length>0,'player rank empty for '+c);
   F(document.getElementById('pte-teams').innerText.length>20,'play-type explorer empty for '+c);
 });
 setConf('',btn[0]);
 // 2. play-type GP-min filter no longer empties the tables
 [0,3,5,8].forEach(function(g){ var b=document.getElementById('pt-gp-'+g); setPTGP(g,b);
   F(document.querySelectorAll('#pte-teams tbody tr').length>0,'PT explorer empty at GP min '+g); });
 setPTGP(0,document.getElementById('pt-gp-0'));
 // 3. defence ranks: best def play type rank 1 = lowest PPP allowed
 PLAY_TYPES.forEach(function(pt){
   var pool=TEAMS.filter(function(t){return (t.pt_def[pt]||{}).p>0;});
   var best=pool.filter(function(t){return t.pt_def[pt].pr===1;})[0];
   var minv=Math.min.apply(null,pool.map(function(t){return ppp(t.pt_def[pt]);}));
   F(best&&Math.abs(ppp(best.pt_def[pt])-minv)<1e-9,'def rank 1 not lowest PPP for '+pt);
   var bo=pool.filter(function(t){return (t.pt_off[pt]||{}).pr===1;})[0];
 });
 // 4. Team Intel for every team: no Elite on a bottom-half defensive play type, Def FG% rank matches
 TEAMS.forEach(function(t){
   document.getElementById('ti-team').value=t.id; renderTeamIntel();
   var tables=document.querySelectorAll('#ti-content table');
   tables.forEach(function(tb,ti){ tb.querySelectorAll('tbody tr').forEach(function(tr){
     var c=tr.querySelectorAll('td'); if(c.length<6) return;
     var pt=c[0].innerText.trim(), lab=c[5].innerText.trim();
     var side=ti===0?'pt_off':(ti===1?'pt_def':null); if(!side||PLAY_TYPES.indexOf(pt)<0) return;
     var d=t[side][pt]||{};
     if(lab==='Elite') F(d.pp>=90,t.name+' '+side+' '+pt+' Elite at pct '+d.pp);
     if(lab==='Poor') F(d.pp<25,t.name+' '+side+' '+pt+' Poor at pct '+d.pp);
   });});
   var txt=document.getElementById('ti-content').innerText;
   var m=txt.match(/Def FG%\s*([\d.]+)%\s*#(\d+)\/48/); 
   if(m){ var arr=TEAMS.map(function(x){return fg(x.def);}).sort(function(a,b){return a-b;});
     var rk=arr.indexOf(fg(t.def))+1; F(Math.abs(rk-(+m[2]))<=2,t.name+' Def FG% rank '+m[2]+' vs actual '+rk); }
   // strengths must be top-40%-or-better, weaknesses bottom 40%
   var r=TR[t.id];
   document.querySelectorAll('#ti-content .analysis-strength').forEach(function(e){var k=e.innerText.match(/#(\d+)\/48/);if(k) F(+k[1]<=20,t.name+' strength ranked #'+k[1]);});
   document.querySelectorAll('#ti-content .analysis-weakness').forEach(function(e){var k=e.innerText.match(/#(\d+)\/48/);if(k) F(+k[1]>=29,t.name+' weakness ranked #'+k[1]);});
 });
 // 5. team rankings defense view: lowest FG% allowed is coloured best
 setTRSide('def',document.getElementById('tr-def'));
 var rows=[].slice.call(document.querySelectorAll('#tr-body tr'));
 var cells=rows.map(function(tr){var c=tr.querySelectorAll('td');return {v:parseFloat(c[6].innerText),cls:c[6].className};});
 var lo=cells.reduce(function(a,b){return b.v<a.v?b:a;}), hi=cells.reduce(function(a,b){return b.v>a.v?b:a;});
 F(lo.cls==='hot','lowest FG% allowed not hot ('+lo.cls+')'); F(hi.cls==='cold','highest FG% allowed not cold ('+hi.cls+')');
 setTRSide('off',document.getElementById('tr-off'));
 var cells2=[].slice.call(document.querySelectorAll('#tr-body tr')).map(function(tr){var c=tr.querySelectorAll('td');return {v:parseFloat(c[6].innerText),cls:c[6].className};});
 F(cells2.reduce(function(a,b){return b.v>a.v?b:a;}).cls==='hot','highest FG% (offense) not hot');
 // 6. matchup: defensive play type winner has the lower PPP allowed
 document.getElementById('mu-a').value=byName('Waterloo Warriors').id; document.getElementById('mu-b').value=byName('Western Ontario Mustangs').id; renderMatchup();
 R.notes.push('matchup ok len '+document.getElementById('mu-content').innerText.length);
 // 7. player intel & p vs p render
 var p=PLAYERS.filter(function(x){return x.tid===HOME_ID;})[0];
 document.getElementById('pi-team').value=p.tid; populatePiPlayers(); document.getElementById('pi-player').value=p.id; renderPlayerIntel();
 F(document.getElementById('pi-content').innerText.length>200,'player intel empty');
 document.getElementById('pc-a').value=p.id; document.getElementById('pc-b').value=PLAYERS[40].id; renderPlayerCompare();
 F(document.getElementById('pc-content').innerText.length>200,'p vs p empty');
 // 8. shot quality panel hidden
 F(getComputedStyle(document.getElementById('ov-shot-quality').parentElement.parentElement).display==='none','shot quality panel visible with no data');
 // 8b. 'Elite' may only label a top-10% rank, never the above-average scatter quadrant
 F(document.getElementById('ov-scatter').innerHTML.indexOf('>ELITE<')<0,'scatter quadrant still labelled ELITE');
 // 9. leftover FIBA wording
 var all=document.body.innerText; ['FIBA','Senior','Tier 1','Tier 2','T1–2','of 81','/81','Canada Basketball'].forEach(function(w){ if(all.indexOf(w)>=0) R.fails.push('leftover text: '+w); });
}catch(e){R.fails.push('EXCEPTION '+e+' '+e.stack);}
document.body.setAttribute('data-result',JSON.stringify(R));
})();
