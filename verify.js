const fs=require('fs');
let src=fs.readFileSync('check.js','utf8');
// document 스텁
const el={innerHTML:'',textContent:'',addEventListener(){},querySelector(){return el},
  querySelectorAll(){return []},closest(){return null},classList:{toggle(){},add(){},remove(){}},dataset:{}};
global.document={createElement:()=>({set textContent(v){this._t=v},get innerHTML(){return String(this._t??'')}}),
  getElementById:()=>el, querySelector:()=>el, querySelectorAll:()=>[]};
eval(src + ';globalThis.DATA=DATA;');

const T='2026-09-13', W='2026-09-07';
let fail=0;
const bad=(m)=>{console.log('FAIL: '+m);fail++;};
const ok =(m)=>console.log('ok  : '+m);

// (a) archive.daily 연속성
const keys=Object.keys(DATA.archive.daily).sort();
console.log('archive.daily keys:', keys.join(' '));
let gaps=[];
for(let i=1;i<keys.length;i++){
  const p=new Date(keys[i-1]+'T00:00:00Z'), c=new Date(keys[i]+'T00:00:00Z');
  const d=(c-p)/86400000;
  if(d!==1) gaps.push(keys[i-1]+'→'+keys[i]+'('+d+'일)');
}
gaps.length?bad('daily 날짜 끊김: '+gaps.join(', ')):ok('daily 날짜 연속');
keys[keys.length-1]===T?ok('최신 daily 키 = '+T):bad('최신 daily 키가 '+T+'가 아님: '+keys[keys.length-1]);
console.log('archive.weekly keys:', Object.keys(DATA.archive.weekly).sort().join(' '));
console.log('archive.monthly keys:', Object.keys(DATA.archive.monthly).sort().join(' '));
console.log('보존 한도 daily/weekly/monthly:',keys.length,Object.keys(DATA.archive.weekly).length,Object.keys(DATA.archive.monthly).length);

// 직전 기록이 참조로 덮이지 않았는지
DATA.archive.daily['2026-09-12'].asOf.includes('9/12')?ok('9/12 기록 리터럴 보존'):bad('9/12 기록 훼손');
DATA.archive.weekly['2026-08-31'].asOf.includes('8/31')?ok('8/31 주간 리터럴 보존'):bad('8/31 주간 훼손');

for(const [label,p] of [['daily',DATA.periods.daily],['weekly',DATA.periods.weekly]]){
  const s=p.sections, st=s.stocks;
  // (b) 8장 + 첫 장 + tag
  st.kr.length===8?ok(label+' kr 8장'):bad(label+' kr '+st.kr.length+'장');
  st.us.length===8?ok(label+' us 8장'):bad(label+' us '+st.us.length+'장');
  st.kr[0].name==='KOSPI 지수'?ok(label+' kr 첫 장 KOSPI 지수'):bad(label+' kr 첫 장 '+st.kr[0].name);
  st.us[0].name==='S&P 500 지수'?ok(label+' us 첫 장 S&P 500 지수'):bad(label+' us 첫 장 '+st.us[0].name);
  st.macro.length===2?ok(label+' macro 2장'):bad(label+' macro '+st.macro.length+'장');
  const all=[...st.macro,...st.kr,...st.us];
  const notag=all.filter(c=>!c.tag).map(c=>c.name);
  notag.length?bad(label+' tag 없음: '+notag):ok(label+' 모든 카드 tag 있음');
  // (c) spark
  const sp=all.filter(c=>!Array.isArray(c.spark)||c.spark.length<2).map(c=>c.name);
  sp.length?bad(label+' spark 2개 미만: '+sp):ok(label+' 모든 카드 spark>=2');
  const mis=all.filter(c=>!Array.isArray(c.sparkDates)||c.sparkDates.length!==c.spark.length).map(c=>c.name);
  mis.length?bad(label+' spark/sparkDates 길이 불일치: '+mis):ok(label+' spark 길이 일치');
  // 전일 대비 = spark 마지막 두 값 차 (지수/원화 카드만 대략 검증)
  // (d) issues
  const need = label==='daily'?10:5;
  st.issuesKr.length===need?ok(label+' issuesKr '+need+'건'):bad(label+' issuesKr '+st.issuesKr.length+'건');
  st.issuesUs.length===need?ok(label+' issuesUs '+need+'건'):bad(label+' issuesUs '+st.issuesUs.length+'건');
  for(const [k,arr] of [['issuesKr',st.issuesKr],['issuesUs',st.issuesUs]]){
    const words='삼성전자 SK하이닉스 코스피 코스닥 오라클 엔비디아 국채금리 국제유가 환율 CPI'.split(' ');
    for(const w of words){
      const n=arr.filter(x=>(x.title+x.summary).includes(w)).length;
      if(n>=3) console.log('  주의: '+label+' '+k+' 에 "'+w+'" '+n+'건');
    }
  }
  // (e) christian cat
  const nocat=(s.christian||[]).filter(x=>!x.cat).length;
  nocat?bad(label+' christian cat 없음 '+nocat+'건'):ok(label+' christian 모두 cat 있음 ('+(s.christian||[]).length+'건)');
  // (f) 핫이슈 금칙어
  const banned=['총기','난사','살인','타살','투신','피살','흉기','추락사'];
  const hit=(s.buzz||[]).filter(x=>banned.some(w=>(x.title+x.summary+x.keyword).includes(w))).map(x=>x.keyword);
  hit.length?bad(label+' buzz 금칙어: '+hit):ok(label+' buzz 금칙어 없음 ('+(s.buzz||[]).length+'건)');
  // 빈 섹션
  for(const k of ['buzz','politics','economy','entertainment','drama','variety','movies','christian']){
    if(!s[k]||!s[k].length) bad(label+' 섹션 비어있음: '+k);
  }
}
console.log(fail? '\n=== '+fail+'건 실패 ===' : '\n=== 전부 통과 ===');
process.exit(fail?1:0);
