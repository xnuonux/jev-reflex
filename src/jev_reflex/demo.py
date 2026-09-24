"""An explicitly synthetic, network-free demonstration of real accounting."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from .reflex import DEFAULT_POLICY, SNAPSHOT, Service


def run():
    calls = []

    def fake(wire):
        calls.append(True)
        answers = {}
        for key, question in wire['questions'].items():
            ids = list(question['criteria'])
            choice = 'low_relevance'
            answers[key] = dict(type='choice', choice=choice, confidence=.95,
                                probabilities={i: .97 if i == choice else .03/(len(ids)-1) for i in ids})
        return dict(model=SNAPSHOT, provider='TypeSafe', id='synthetic-demo',
                    answers=answers, usage={'cost': .00001})

    with TemporaryDirectory(prefix='jev-reflex-demo-') as directory:
        root = Path(directory)
        (root/'policy.json').write_text(json.dumps(DEFAULT_POLICY | {
            'enabled': True, 'daily_limit_microusd': 100000}), encoding='utf-8')
        service = Service(root, transport=fake)
        args = dict(project='demo', task='debugging', request_id='first',
                    snapshot_id='source-v1', privacy_namespace='public-demo',
                    recipe='context_triage/v1', independent_items=True, reuse_success=True,
                    items=[dict(id='failing-test', privacy_namespace='public-demo',
                                text='A required failing-test excerpt.',
                                goal='Diagnose the failure.', mandatory_pinned=True)])
        first = service.recipe(**args)
        replay = service.recipe(**args)
        reused = service.recipe(**(args | {'request_id': 'second'}))
        return dict(synthetic=True, provider_calls=len(calls), live_provider_calls=0,
                    replay_calls=replay['model_calls_this_invocation'],
                    reuse_calls=reused['model_calls_this_invocation'],
                    pinned_context_visibility=first['results']['failing-test']['advice']['visibility'],
                    authority=first['authority'], may_execute=first['may_execute'],
                    description='Fixture deliberately calls required evidence low-relevance; code preserves it.',
                    first=first, reused=reused,
                    benchmark_claim=False)
