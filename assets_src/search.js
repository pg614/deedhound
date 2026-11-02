(function(){var f=document.getElementById("srch");if(!f)return;var q=document.getElementById("q"),ul=document.getElementById("sres"),idx=null,res=[],sel=-1;
function load(cb){if(idx)return cb();fetch("/search.json").then(function(r){return r.json()}).then(function(d){idx=d;cb()}).catch(function(){})}
function norm(s){return s.toLowerCase().replace(/[^a-z0-9 ]/g," ").replace(/\s+/g," ").trim()}
function find(v){v=norm(v);if(!v)return[];var z=/^\d{3,5}$/.test(v),out=[];for(var i=0;i<idx.length;i++){var x=idx[i],t=norm(x.t+" "+x.s),hit=z?(x.z||[]).some(function(k){return k.indexOf(v)===0}):(t.indexOf(v)===0||t.indexOf(" "+v)>=0);if(hit)out.push(x);if(out.length>=8)break}return out}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}
function draw(){if(!q.value.trim()){ul.hidden=true;return}ul.hidden=false;ul.innerHTML=res.length?res.map(function(x,i){return'<li role="option"'+(i===sel?' aria-selected="true"':"")+'><a href="'+x.u+'"><b>'+esc(x.t)+'</b><span>'+esc(x.s==="county"?"All sales in the county":x.s)+" · "+x.n+" upcoming</span></a></li>"}).join(""):'<li class="none">No match. Try a county name, city or 5-digit ZIP.</li>'}
q.addEventListener("input",function(){load(function(){res=find(q.value);sel=-1;draw()})});
q.addEventListener("focus",function(){load(function(){})});
q.addEventListener("keydown",function(e){if(e.key==="ArrowDown"){sel=Math.min(sel+1,res.length-1);draw();e.preventDefault()}else if(e.key==="ArrowUp"){sel=Math.max(sel-1,0);draw();e.preventDefault()}else if(e.key==="Escape"){ul.hidden=true}});
f.addEventListener("submit",function(e){e.preventDefault();load(function(){res=find(q.value);var x=res[sel>=0?sel:0];if(x)location.href=x.u;else draw()})});
document.addEventListener("click",function(e){if(!f.contains(e.target))ul.hidden=true})})();
