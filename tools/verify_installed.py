"""Verify the installed distribution from outside its source tree, without inference."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import jev_reflex
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def verify():
    origin=Path(jev_reflex.__file__).resolve()
    if 'site-packages' not in origin.parts:
        raise AssertionError('This check requires a non-editable installed package')
    with tempfile.TemporaryDirectory(prefix='jev-reflex-install-') as directory:
        root=Path(directory)
        env={k:v for k,v in os.environ.items() if k not in
             ('PYTHONPATH','JEV_REFLEX_HOME','JEV_REFLEX_PROVIDER','OPENROUTER_API_KEY','TYPESAFE_API_KEY')}
        env.update(JEV_REFLEX_HOME=str(root/'state'),JEV_REFLEX_PROVIDER='openrouter')
        demo=subprocess.run([sys.executable,'-m','jev_reflex','demo'],cwd=root,env=env,
                            capture_output=True,text=True,timeout=15,check=True)
        result=json.loads(demo.stdout)
        assert result['synthetic'] and result['provider_calls']==1
        assert result['replay_calls']==0 and result['reuse_calls']==0
        assert not (root/'state').exists()
        params=StdioServerParameters(command=sys.executable,args=['-m','jev_reflex','serve'],
                                    env=env,cwd=str(root))
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                initialized=await session.initialize()
                tools=await session.list_tools()
                assert len(tools.tools)==10
                response=await session.call_tool('jev_reflex_status',{})
                status=response.structuredContent or json.loads(response.content[0].text)
                assert not response.isError and status['calls_today']==0
                assert status['credential_available'] is False and status['enabled'] is False
                context=await session.call_tool('jev_reflex_context',dict(
                    project='install',task='check',request_id='context',privacy_namespace='synthetic',
                    goal='Review the required evidence',chunks=[dict(id='required',text='Required evidence',
                    source_ref='fixture:1',mandatory_pinned=True)]))
                packet=context.structuredContent or json.loads(context.content[0].text)
                assert not context.isError and packet['context_plan'][0]['visibility']=='show_now'
                assert packet['may_execute'] is False
                shared=await session.call_tool('jev_reflex_shared',dict(project='install',task='check',
                    request_id='shared',snapshot_id='v1',privacy_namespace='synthetic',state='A public fixture',
                    independent_questions=True,questions=[dict(id=f'q{i}',primitive='noul',question='Relevant?') for i in range(13)]))
                assert not shared.isError and (shared.structuredContent or json.loads(shared.content[0].text))['reason']=='disabled'
                key=dict(project='install',task='check',request_id='bulk',privacy_namespace='synthetic')
                bulk=await session.call_tool('jev_reflex_bulk',dict(**key,snapshot_id='v1',independent_items=True,
                    items=[dict(id=f'i{i}',primitive='noul',text='Public fixture',question='Relevant?') for i in range(1000)]))
                assert not bulk.isError and (bulk.structuredContent or json.loads(bulk.content[0].text))['total_items']==1000
                assert (bulk.structuredContent or json.loads(bulk.content[0].text))['model_calls_this_invocation']==0
                cancelled=await session.call_tool('jev_reflex_cancel_job',key)
                assert not cancelled.isError and (cancelled.structuredContent or json.loads(cancelled.content[0].text))['cancelled']
                page=await session.call_tool('jev_reflex_inspect_job',key | dict(offset=900))
                assert not page.isError and len((page.structuredContent or json.loads(page.content[0].text))['items'])==100
        print(json.dumps(dict(installed_package=True,outside_source_cwd=True,mcp_tools=10,
                              negotiated_protocol=initialized.protocolVersion,
                              paid_provider_calls=0,demo_synthetic_calls=1)))


if __name__=='__main__':
    asyncio.run(verify())
