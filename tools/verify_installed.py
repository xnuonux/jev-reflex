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
                assert len(tools.tools)==6
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
        print(json.dumps(dict(installed_package=True,outside_source_cwd=True,mcp_tools=6,
                              negotiated_protocol=initialized.protocolVersion,
                              paid_provider_calls=0,demo_synthetic_calls=1)))


if __name__=='__main__':
    asyncio.run(verify())
