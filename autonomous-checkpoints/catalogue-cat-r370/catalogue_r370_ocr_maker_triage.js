/* CAT-R370: reproducible, read-only OCR and maker-label risk triage.
 * Input: snapshots/CAT-R363/CAT_R363_PAIR_REVIEW_LEDGER.csv
 * No canonical catalogue edits, no photo, no physical validation.
 */
'use strict';
function parseCsvR370(s) {
 const out=[];let row=[],field='',quoted=false;
 for(let i=0;i<s.length;i++){const c=s[i];
   if(quoted){if(c==='"'&&s[i+1]==='"'){field+='"';i++;}else if(c==='"')quoted=false;else field+=c;}
   else if(c==='"')quoted=true;
   else if(c===','){row.push(field);field='';}
   else if(c==='\n'){row.push(field.replace(/\r$/,''));out.push(row);row=[];field='';}
   else field+=c;
 }
 if(field||row.length){row.push(field);out.push(row);}
 if(quoted)throw Error('unclosed quoted CSV field');
 return out;
}
function auditCatalogueR370(csv) {
 const data=parseCsvR370(csv),head=data.shift();
 const rows=data.map((line,n)=>{
   if(line.length!==head.length)throw Error('CSV column-count mismatch line '+(n+2));
   return Object.fromEntries(head.map((k,i)=>[k,line[i]]));
 });
 if(rows.length!==393)throw Error('Expected exactly 393 theoretical risk pairs');
 if(new Set(rows.map(x=>x.component)).size!==345)throw Error('Unexpected review group count');
 const refs=new Set(rows.flatMap(x=>[x.reference_a,x.reference_b]));
 if(refs.size!==732)throw Error('Unexpected distinct reference count');
 const result={schema:'bres-cat-r370-ocr-maker-label-risk-v1',
  milestone:'CAT-R370',date:'2026-11-05',
  source:'snapshots/CAT-R363/CAT_R363_PAIR_REVIEW_LEDGER.csv',
  total_theoretical_pairs:rows.length,distinct_references:refs.size,review_groups:345,
  categories:{},ocr_label_review_queue:[],checks:{}};
 for(const [name,subset] of [['ocr',rows.filter(x=>x.already_known_hypothetical_OCR==='True')],
                             ['typing',rows.filter(x=>x.already_known_hypothetical_OCR!=='True')]]){
   const c={total:subset.length,same_label:0,different_labels:0,missing_label:0,unclassified:0};
   for(const x of subset){
     const different=!!x.manufacturer_a_UNVERIFIED&&!!x.manufacturer_b_UNVERIFIED&&
       x.manufacturer_a_UNVERIFIED!==x.manufacturer_b_UNVERIFIED;
     if(x.manufacturer_missing_SOURCE_ONLY==='True')c.missing_label++;
     else if(x.same_manufacturer_SOURCE_ONLY==='True')c.same_label++;
     else if(different)c.different_labels++;
     else c.unclassified++;
     if(name==='ocr'&&(different||x.manufacturer_missing_SOURCE_ONLY==='True'))
       result.ocr_label_review_queue.push({ref_a:x.reference_a,ref_b:x.reference_b,
         label_a_UNVERIFIED:x.manufacturer_a_UNVERIFIED||null,
         label_b_UNVERIFIED:x.manufacturer_b_UNVERIFIED||null,
         component:x.component,
         label_issue:x.manufacturer_missing_SOURCE_ONLY==='True'?'missing-label':'different-labels',
         physically_equivalent:false});
   }
   result.categories[name]=c;
 }
 result.ocr_label_review_queue.sort((a,b)=>a.ref_a.localeCompare(b.ref_a)||a.ref_b.localeCompare(b.ref_b));
 result.checks={
   exact_partition_ocr_68_typing_325:result.categories.ocr.total===68&&result.categories.typing.total===325,
   labelled_categories_exhaustive:['ocr','typing'].every(k=>{const c=result.categories[k];return c.total===c.same_label+c.different_labels+c.missing_label+c.unclassified;}),
   ocr_61_different_plus_1_missing:result.categories.ocr.different_labels===61&&result.categories.ocr.missing_label===1,
   typing_212_different_25_missing:result.categories.typing.different_labels===212&&result.categories.typing.missing_label===25,
   queue_exactly_62:result.ocr_label_review_queue.length===62,
   no_auto_validation:rows.every(x=>x.auto_validate==='False'&&x.review_state==='UNVERIFIED_TEXT_ONLY'),
   no_physical_equivalence_claim:result.ocr_label_review_queue.every(x=>x.physically_equivalent===false)
 };
 result.ok=Object.values(result.checks).every(Boolean);
 if(!result.ok)throw Error('Audit invariant failed');
 return result;
}
if(typeof require==='function'&&typeof module!=='undefined'&&require.main===module) {
 const fs=require('node:fs');
 const input=fs.readFileSync('snapshots/CAT-R363/CAT_R363_PAIR_REVIEW_LEDGER.csv','utf8');
 process.stdout.write(JSON.stringify(auditCatalogueR370(input),null,2)+'\n');
}
if(typeof module!=='undefined')module.exports={auditCatalogueR370};
