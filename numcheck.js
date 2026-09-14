const fs=require('fs');
const el={innerHTML:'',textContent:'',addEventListener(){},querySelector(){return el},querySelectorAll(){return []},closest(){return null},classList:{toggle(){}},dataset:{}};
global.document={createElement:()=>({set textContent(v){this._t=v},get innerHTML(){return String(this._t??'')}}),getElementById:()=>el,querySelector:()=>el,querySelectorAll:()=>[]};
eval(fs.readFileSync('check.js','utf8')+';globalThis.DATA=DATA;');
const num=s=>parseFloat(String(s).replace(/[^0-9.\-]/g,''));
for(const lab of ['daily','weekly']){
  const st=DATA.periods[lab].sections.stocks;
  for(const c of [...st.macro,...st.kr,...st.us]){
    const sp=c.spark, last=sp[sp.length-1], prev=sp[sp.length-2];
    const diff=last-prev, pct=diff/prev*100;
    const dc=num(c.change), dp=num(c.changePct), price=num(c.price);
    const pOK=Math.abs(price-last)<Math.max(0.02,Math.abs(last)*0.0005);
    const cOK=Math.abs(dc-diff)<Math.max(0.02,Math.abs(diff)*0.01);
    const ptOK=Math.abs(dp-pct)<0.06;
    const dOK=(c.direction==='up')===(diff>=0);
    if(!(pOK&&cOK&&ptOK&&dOK)) console.log(`${lab} ${c.name}: price=${price}/spark=${last} change=${dc}/${diff.toFixed(2)} pct=${dp}/${pct.toFixed(2)} dir=${c.direction}`,
      [pOK?'':'PRICE',cOK?'':'CHANGE',ptOK?'':'PCT',dOK?'':'DIR'].filter(Boolean).join(','));
  }
}
console.log('numeric check done');
