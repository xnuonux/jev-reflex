"""Bridge already-decoded model tool arguments; this example makes no model call."""
from jev_reflex import Service
from jev_reflex.api import invoke

# The application, not its language model, owns this allowlist and host configuration.
FUNCTION = {
    'type':'function',
    'function': {
        'name':'jev_context_advice',
        'description':'Advisory context triage only. Keep originals and required evidence.',
        'parameters': {
            'type':'object', 'additionalProperties':False,
            'required':['project','task','request_id','privacy_namespace','goal','chunks'],
            'properties': {
                **{k:{'type':'string'} for k in ['project','task','request_id','privacy_namespace','goal']},
                'chunks': {'type':'array','minItems':1,'maxItems':8,'items':{
                    'type':'object','additionalProperties':False,
                    'required':['id','text','source_ref','mandatory_pinned'],
                    'properties':{**{k:{'type':'string'} for k in ['id','text','source_ref']},
                                  'mandatory_pinned':{'type':'boolean'}}}},
            },
        },
    },
}


def handle_tool_call(name: str, decoded_arguments: dict) -> dict:
    if name != FUNCTION['function']['name']:
        raise ValueError('unrecognized tool')
    # Invoke validates fields and values; no eval(), shell, or dynamic method lookup.
    return invoke(Service(), 'context', decoded_arguments)

# Return this result to the originating tool_call_id using your provider's documented
# tool-result protocol. This module never automatically executes model tool calls.
