"""A small JSON boundary shared by CLI and function-calling adapters."""
from inspect import signature
from .reflex import Service, require

METHODS = {
    'workflow': 'run', 'host_event': 'host_event',
    'artifact_put': 'put', 'artifact_get': 'get', 'calibration_audit': 'audit',
    'status': 'status', 'batch': 'judge', 'recipe': 'recipe',
    'record_outcome': 'record_outcome', 'metrics': 'recipe_metrics',
    'context': 'context',
    'shared': 'shared', 'bulk': 'bulk', 'inspect_job': 'inspect_job', 'cancel_job': 'cancel_job',
    'controller_open': 'open_controller', 'controller_event': 'event', 'controller_inspect': 'inspect',
}


def invoke(service: Service, method: str, arguments: dict) -> dict:
    require(type(method) is str and method in METHODS, 'unknown-method')
    require(type(arguments) is dict, 'arguments-object')
    if method in ('workflow','host_event','artifact_put','artifact_get','calibration_audit'):
        from functools import partial
        from . import workflows, artifacts, calibration
        module = workflows if method in ('workflow','host_event') else calibration if method=='calibration_audit' else artifacts
        target = partial(getattr(module, METHODS[method]), service)
    elif method.startswith('controller_'):
        from functools import partial
        from . import controllers
        target = partial(getattr(controllers, METHODS[method]), service)
    elif method == 'context':
        from functools import partial
        from .context import plan
        target = partial(plan, service)
    else:
        target = getattr(service, METHODS[method])
    require(all(type(k) is str and not k.startswith('_') for k in arguments), 'arguments-fields')
    try:
        signature(target).bind(**arguments)
    except TypeError:
        require(False, 'arguments-fields')
    return target(**arguments)
