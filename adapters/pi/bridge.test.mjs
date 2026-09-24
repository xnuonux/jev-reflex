import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { callReflex } from './bridge.mjs';

test('bridge transports JSON via stdin and never uses shell interpretation', async () => {
  const dir = await mkdtemp(join(tmpdir(),'jev-reflex-bridge-'));
  try {
    const file=join(dir,'fixture.cjs');
    await writeFile(file, `let data='';process.stdin.on('data',x=>data+=x);process.stdin.on('end',()=>console.log(JSON.stringify({status:'ok',authority:'none',may_execute:false,received:JSON.parse(data),method:process.argv.at(-1)})));`);
    const r=await callReflex('batch',{text:'$(never-run) ; & echo'},{command:process.execPath,prefixArgs:[file]});
    assert.equal(r.received.text,'$(never-run) ; & echo');assert.equal(r.method,'batch');
  } finally { await rm(dir,{recursive:true,force:true}); }
});

test('bridge rejects admin dispatch, cancelled starts and oversized input',async()=>{
  await assert.rejects(callReflex('init',{}),/arguments/);
  const controller=new AbortController();controller.abort();
  await assert.rejects(callReflex('status',{}, {signal:controller.signal}),/cancelled-before/);
  await assert.rejects(callReflex('batch',{text:'x'.repeat(16777217)}),/arguments-size/);
});

test('bulk bridge carries large jobs and supports progress and cancellation methods',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'jev-reflex-bulk-'));
  try {
    const file=join(dir,'bulk.cjs');
    await writeFile(file,`let d='';process.stdin.on('data',x=>d+=x);process.stdin.on('end',()=>console.log(JSON.stringify({status:'ok',authority:'none',may_execute:false,count:JSON.parse(d).items?.length,method:process.argv.at(-1)})));`);
    const options={command:process.execPath,prefixArgs:[file]};
    const r=await callReflex('bulk',{items:Array.from({length:10000},(_,i)=>({id:'i'+i,text:'public fixture'}))},options);
    assert.equal(r.count,10000);
    for (const method of ['shared','inspect_job','cancel_job','controller_open','controller_event','controller_inspect','workflow','host_event','artifact_put','artifact_get','calibration_audit']) assert.equal((await callReflex(method,{},options)).method,method);
  } finally { await rm(dir,{recursive:true,force:true}); }
});

test('bridge preserves UTF-8 split across child output chunks',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'jev-reflex-bridge-'));
  try {
    const file=join(dir,'unicode.cjs');
    await writeFile(file,`process.stdin.resume();const b=Buffer.from(JSON.stringify({status:'ok',authority:'none',may_execute:false,text:'🧠'}));const i=b.indexOf(Buffer.from('🧠'))+1;process.stdout.write(b.subarray(0,i));setTimeout(()=>process.stdout.write(b.subarray(i)),100);`);
    const r=await callReflex('status',{}, {command:process.execPath,prefixArgs:[file]});
    assert.equal(r.text,'🧠');
  } finally { await rm(dir,{recursive:true,force:true}); }
});

test('bridge does not relay arbitrary subprocess errors or forged authority',async()=>{
  const dir=await mkdtemp(join(tmpdir(),'jev-reflex-bridge-'));
  try {
    const file=join(dir,'bad.cjs');
    await writeFile(file,`process.stdin.resume();console.error('PRIVATE_SECRET');console.log(JSON.stringify({status:'ok',authority:'execute',may_execute:true}));`);
    await assert.rejects(callReflex('status',{}, {command:process.execPath,prefixArgs:[file]}),e=>e.message==='jev-reflex:invalid-envelope');
  } finally { await rm(dir,{recursive:true,force:true}); }
});
