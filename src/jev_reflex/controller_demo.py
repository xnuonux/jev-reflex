"""Offline end-to-end temporal experiment. All model results are injected fixtures."""
import json
from pathlib import Path
import tempfile
from .api import invoke
from .reflex import Service, DEFAULT_POLICY, SNAPSHOT
from .providers import OPENROUTER


def run():
    signal = dict(primitive='choice', question='Which investigation direction fits?',
                  choices={'code':'Implementation', 'fixture':'Test fixture'})
    key = dict(project='demo', task='investigate', privacy_namespace='synthetic', controller_id='route')
    labels = ['code', 'fixture', 'code', 'fixture', 'code', 'fixture', 'fixture']
    selected = 'code'
    def fake(wire):
        return dict(model=SNAPSHOT, provider='TypeSafe', id='synthetic', usage={'cost':0},
                    answers={k:dict(type='choice', choice=selected, confidence=.9,
                        probabilities={x:.9 if x == selected else .1 for x in signal['choices']})
                        for k in wire['questions']})
    with tempfile.TemporaryDirectory(prefix='jev-controller-demo-') as directory:
        root = Path(directory)
        (root/'policy.json').write_text(json.dumps(DEFAULT_POLICY | {
            'enabled':True, 'daily_limit_microusd':1000000}))
        service = Service(root, transport=fake, profile=OPENROUTER, clock=lambda:100000.)
        current = invoke(service, 'controller_open', key | dict(snapshot_id='s0', signal=signal))
        events = 0
        def send(event):
            nonlocal current, events
            events += 1
            current = invoke(service, 'controller_event', key | dict(event_id=f'e{events}',
                expected_revision=current['controller']['revision'], event=event))
            return current['controller']
        trace = []
        for i, selected in enumerate(labels):
            if i:
                send(dict(kind='bind', snapshot_id=f's{i}'))
            service.judge('demo', 'investigate', f'r{i}', f's{i}',
                          [signal | dict(id='route',text=f'Synthetic observation {i}')])
            state = send(dict(kind='observe', receipt=dict(kind='batch', request_id=f'r{i}', item_id='route')))
            trace.append(dict(source=f's{i}', raw_proposal=selected, held_hint=state['selected_id'],
                              reason=state['reason'], evidence_origin=state['last_evidence']['evidence_origin']))
        corrected = send(dict(kind='override', selected_id='code'))['selected_id']
        stopped = send(dict(kind='stop'))
        return dict(schema='controller-demo/v1', evidence='synthetic-offline', paid_calls=0,
                    trace=trace, stateless_switches=sum(a != b for a,b in zip(labels, labels[1:])),
                    controller_switches=sum(a['held_hint'] != b['held_hint'] for a,b in zip(trace, trace[1:])),
                    sustained_change_extra_observations=1, manual_correction=corrected,
                    stopped_hint=stopped['selected_id'], authority='none', may_execute=False,
                    limitation='Mechanics on a designed trace, not measured agent productivity.')
