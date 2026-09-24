import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SCRIPTS = Path(__file__).resolve().parents[1] / 'src'
sys.path.insert(0, str(SCRIPTS))
from jev_reflex.reflex import Service, DEFAULT_POLICY


class MCPTests(unittest.TestCase):
    def test_real_stdio_roundtrip_and_replay_offline(self):
        async def go(root):
            (root/'policy.json').write_text(json.dumps(DEFAULT_POLICY | {'enabled':True,'daily_limit_microusd':1000000}))
            launcher = root/'fixture.py'
            launcher.write_text(
                'import sys\nfrom pathlib import Path\n'
                f'sys.path.insert(0,{str(SCRIPTS)!r})\n'
                'from jev_reflex.reflex import Service,SNAPSHOT\nfrom jev_reflex.server import make_server\n'
                'def fake(w):\n'
                ' answers={}\n'
                ' for key,q in w["questions"].items():\n'
                '  if q["type"]=="noul":answers[key]={"type":"noul","noul":.99}\n'
                '  else:\n'
                '   ids=list(q["criteria"]);chosen=ids[0]\n'
                '   answers[key]={"type":"choice","choice":chosen,"confidence":.9,"probabilities":{x:(.9 if x==chosen else .1/(len(ids)-1)) for x in ids}}\n'
                ' return dict(model=SNAPSHOT,provider="TypeSafe",id="gen-fixture",answers=answers,usage={"cost":.00001})\n'
                'make_server(Service(Path(__file__).parent,transport=fake)).run(transport="stdio")\n')
            params=StdioServerParameters(command=sys.executable,args=[str(launcher)])
            async with stdio_client(params) as (read,write):
                async with ClientSession(read,write) as session:
                    await session.initialize()
                    tools=await session.list_tools()
                    self.assertEqual({t.name for t in tools.tools},{
                        'jev_reflex_status','jev_reflex_context','jev_reflex_batch','jev_reflex_recipe',
                        'jev_reflex_record_outcome','jev_reflex_recipe_metrics',
                        'jev_reflex_shared','jev_reflex_bulk','jev_reflex_inspect_job','jev_reflex_cancel_job', 'jev_reflex_controller_open',
                        'jev_reflex_controller_event', 'jev_reflex_controller_inspect','jev_reflex_workflow','jev_reflex_host_event',
                        'jev_reflex_artifact_put','jev_reflex_artifact_get','jev_reflex_calibration_audit'})
                    args=dict(project='fixture',task='mcp',request_id='one',snapshot_id='v1',items=[dict(id='relevant',primitive='noul',text='compiler error',question='About software?')])
                    a=await session.call_tool('jev_reflex_batch',args)
                    self.assertFalse(a.isError)
                    data=a.structuredContent or json.loads(a.content[0].text)
                    self.assertEqual(data['results']['relevant']['value'],True)
                    workflow=await session.call_tool('jev_reflex_host_event',dict(
                        project='fixture',task='mcp',request_id='handoff',privacy_namespace='public',
                        event='before_handoff',packet={'original':'Do not deploy','handoff':'Keep local'}))
                    self.assertFalse(workflow.isError)
                    wd=workflow.structuredContent or json.loads(workflow.content[0].text)
                    self.assertEqual(wd['workflow'],'handoff_check/v1')
                    self.assertFalse(wd['automatic_interception'])
                    stored=await session.call_tool('jev_reflex_artifact_put',dict(project='fixture',privacy_namespace='local',content='exact text'))
                    sid=(stored.structuredContent or json.loads(stored.content[0].text))['artifact_id']
                    fetched=await session.call_tool('jev_reflex_artifact_get',dict(project='fixture',privacy_namespace='local',artifact_id=sid))
                    self.assertEqual((fetched.structuredContent or json.loads(fetched.content[0].text))['content'],'exact text')
                    controller_key = dict(project='fixture', task='mcp', privacy_namespace='public', controller_id='relevance')
                    opened = await session.call_tool('jev_reflex_controller_open', controller_key | dict(
                        snapshot_id='v1', signal=dict(primitive='noul', question='About software?')))
                    self.assertFalse(opened.isError)
                    observed = await session.call_tool('jev_reflex_controller_event', controller_key | dict(
                        event_id='observe', expected_revision=0, event=dict(kind='observe', receipt=dict(
                            kind='batch', request_id='one', item_id='relevant'))))
                    self.assertFalse(observed.isError)
                    observed_data = observed.structuredContent or json.loads(observed.content[0].text)
                    self.assertEqual(observed_data['controller']['selected_id'], 'true')
                    inspected = await session.call_tool('jev_reflex_controller_inspect', controller_key)
                    self.assertFalse(inspected.isError)
                    self.assertEqual((inspected.structuredContent or json.loads(inspected.content[0].text))['controller'],
                                     observed_data['controller'])
                    b=await session.call_tool('jev_reflex_batch',args)
                    self.assertTrue((b.structuredContent or json.loads(b.content[0].text))['replayed'])
                    args['items'][0]['primitive']='score'
                    bad=await session.call_tool('jev_reflex_batch',args)
                    self.assertTrue(bad.isError)
                    recipe_args=dict(project='fixture',task='mcp',request_id='recipe-one',
                                     snapshot_id='source-a',privacy_namespace='public-fixture',
                                     recipe='context_triage/v1',independent_items=True,
                                     reuse_success=True,items=[dict(id='ctx',
                                         privacy_namespace='public-fixture',text='A selected excerpt',
                                         goal='Locate a relevant source',mandatory_pinned=True)])
                    recipe_result=await session.call_tool('jev_reflex_recipe',recipe_args)
                    self.assertFalse(recipe_result.isError)
                    recipe_data=recipe_result.structuredContent or json.loads(recipe_result.content[0].text)
                    self.assertEqual(recipe_data['results']['ctx']['advice']['visibility'],'show_now')
                    self.assertFalse(recipe_data['may_execute'])
                    reused=await session.call_tool('jev_reflex_recipe',recipe_args | {'request_id':'recipe-two'})
                    reused_data=reused.structuredContent or json.loads(reused.content[0].text)
                    self.assertTrue(reused_data['reused_success'])
                    self.assertEqual(reused_data['historical_source_receipt_id'],recipe_data['receipt_id'])
                    feedback=await session.call_tool('jev_reflex_record_outcome',dict(
                        project='fixture',task='mcp',privacy_namespace='public-fixture',
                        receipt_id=recipe_data['receipt_id'],item_id='ctx',
                        outcome=dict(outcome_version='v1',missed_important_item=False)))
                    self.assertFalse(feedback.isError)
                    metrics=await session.call_tool('jev_reflex_recipe_metrics',dict(
                        project='fixture',task='mcp',privacy_namespace='public-fixture'))
                    metrics_data=metrics.structuredContent or json.loads(metrics.content[0].text)
                    self.assertEqual(metrics_data['metrics']['receipt_count'],2)
                    self.assertEqual(metrics_data['metrics']['missed_important_item']['known_count'],1)
                    invalid=await session.call_tool('jev_reflex_recipe',recipe_args | {
                        'request_id':'bad-version','recipe':'context_triage/v99'})
                    self.assertTrue(invalid.isError)
                    status=await session.call_tool('jev_reflex_status',{})
                    sd=status.structuredContent or json.loads(status.content[0].text)
                    self.assertEqual(sd['implementation_revision'],'portable-0.6.0')
                    self.assertEqual(sd['minimum_start_interval_s'],0)
                    self.assertEqual(sd['max_inflight'],4)
                    self.assertEqual(sd['calls_today'],3)
                    self.assertEqual(sd['reused_recipe_receipts_today'],1)
                    self.assertEqual(sd['accounted_microusd'],30)
                    self.assertIn('context_triage/v1',sd['recipe_versions'])
                    context_result=await session.call_tool('jev_reflex_context',dict(
                        project='fixture',task='mcp',request_id='context-source',privacy_namespace='fixture',
                        goal='Inspect a compiler failure',chunks=[dict(id='required',text='Compiler error',
                        source_ref='test-output:1',mandatory_pinned=True)]))
                    self.assertFalse(context_result.isError)
                    cd=context_result.structuredContent or json.loads(context_result.content[0].text)
                    self.assertEqual(cd['context_plan'][0]['visibility'],'show_now')
                    self.assertEqual(cd['context_plan'][0]['source_ref'],'test-output:1')
                    shared_args=dict(project='fixture',task='bulk',request_id='shared',snapshot_id='v1',
                                     privacy_namespace='public',state='Compiler error',independent_questions=True,
                                     questions=[dict(id=f'q{x}',primitive='noul',question='About software?') for x in range(13)])
                    s=await session.call_tool('jev_reflex_shared',shared_args)
                    self.assertFalse(s.isError)
                    self.assertEqual(len((s.structuredContent or json.loads(s.content[0].text))['results']),13)
                    bulk_args=dict(project='fixture',task='bulk',request_id='bulk',snapshot_id='v1',
                                   privacy_namespace='public',independent_items=True,
                                   items=[dict(id=f'q{x}',primitive='noul',text='Compiler error',question='About software?') for x in range(1000)])
                    b=await session.call_tool('jev_reflex_bulk',bulk_args)
                    self.assertFalse(b.isError)
                    self.assertEqual((b.structuredContent or json.loads(b.content[0].text))['total_items'],1000)
                    key={k:bulk_args[k] for k in ('project','task','request_id','privacy_namespace')}
                    inspect=await session.call_tool('jev_reflex_inspect_job',key | dict(offset=900,limit=100))
                    self.assertFalse(inspect.isError)
                    self.assertEqual(len((inspect.structuredContent or json.loads(inspect.content[0].text))['items']),100)
                    cancel=await session.call_tool('jev_reflex_cancel_job',key)
                    self.assertFalse(cancel.isError)
                    self.assertTrue((cancel.structuredContent or json.loads(cancel.content[0].text))['cancelled'])
        with tempfile.TemporaryDirectory() as d:
            asyncio.run(go(Path(d)))

    def test_two_processes_share_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            Service(root)
            (root/'policy.json').write_text(json.dumps(DEFAULT_POLICY | {'enabled':True,'daily_limit_microusd':20000}))
            script=root/'worker.py'
            script.write_text(
                'import sys,time,json\nfrom pathlib import Path\n'
                f'sys.path.insert(0,{str(SCRIPTS)!r})\n'
                'from jev_reflex.reflex import Service,SNAPSHOT\nroot=Path(__file__).parent\n'
                'def fake(w):\n'
                ' with (root/"dispatched").open("a") as f:f.write("call\\n")\n'
                ' time.sleep(.5)\n'
                ' return dict(model=SNAPSHOT,provider="TypeSafe",id="gen-process",answers={"q0":{"type":"noul","noul":.9}},usage={"cost":.00001})\n'
                's=Service(root,transport=fake)\n'
                'print(json.dumps(s.judge(project="p",task="t",request_id="r",snapshot_id="v1",items=[dict(id="x",primitive="noul",text="test",question="Relevant?")])) )\n')
            flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
            processes=[subprocess.Popen([sys.executable,str(script)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags) for _ in range(2)]
            results=[]
            for process in processes:
                out,err=process.communicate(timeout=10)
                self.assertEqual(process.returncode,0,err.decode())
                results.append(json.loads(out))
            self.assertEqual((root/'dispatched').read_text().splitlines(),['call'])
            self.assertEqual(sum(r['status']=='ok' and not r.get('replayed') for r in results),1)

    def test_bulk_cancel_is_responsive_over_real_stdio_while_provider_waits(self):
        async def go(root):
            (root/'policy.json').write_text(json.dumps(DEFAULT_POLICY | {'enabled':True,'daily_limit_microusd':1000000}))
            (root/'capacity.json').write_text(json.dumps({'max_questions':1,'max_concurrency':1}))
            launcher=root/'cancel-server.py'
            launcher.write_text(
                f'import sys,time\nfrom pathlib import Path\nsys.path.insert(0,{str(SCRIPTS)!r})\n'
                'from jev_reflex.reflex import Service,SNAPSHOT\nfrom jev_reflex.server import make_server\n'
                'root=Path(__file__).parent\n'
                'def fake(w):\n'
                ' (root/"entered").write_text("yes")\n'
                ' end=time.monotonic()+5\n'
                ' while not (root/"release").exists() and time.monotonic()<end:time.sleep(.01)\n'
                ' return dict(model=SNAPSHOT,provider="TypeSafe",id="fixture",answers={k:{"type":"noul","noul":.9} for k in w["questions"]},usage={"cost":.00001})\n'
                'make_server(Service(root,transport=fake)).run(transport="stdio")\n')
            params=StdioServerParameters(command=sys.executable,args=[str(launcher)])
            async with stdio_client(params) as (read,write):
                async with ClientSession(read,write) as session:
                    await session.initialize()
                    key=dict(project='p',task='t',request_id='j',privacy_namespace='public')
                    task=asyncio.create_task(session.call_tool('jev_reflex_bulk',dict(**key,snapshot_id='v1',
                        independent_items=True,items=[dict(id=f'i{i}',primitive='noul',text='log',question='Relevant?') for i in range(4)])))
                    try:
                        for _ in range(200):
                            if (root/'entered').exists():break
                            await asyncio.sleep(.01)
                        self.assertTrue((root/'entered').exists())
                        cancelled=await asyncio.wait_for(session.call_tool('jev_reflex_cancel_job',key),timeout=2)
                        value=cancelled.structuredContent or json.loads(cancelled.content[0].text)
                        self.assertEqual(value['status'],'cancelling')
                    finally:
                        (root/'release').write_text('yes')
                    done=await task
                    value=done.structuredContent or json.loads(done.content[0].text)
                    self.assertEqual(value['status'],'cancelled')
                    self.assertEqual(value['batch_counts']['ok'],1)
                    self.assertEqual(value['batch_counts']['waiting'],3)
        with tempfile.TemporaryDirectory() as d:
            asyncio.run(go(Path(d)))


if __name__=='__main__':unittest.main()
