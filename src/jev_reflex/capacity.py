"""Host-owned packing and admission limits, independent of model tool arguments."""
MAX_REQUEST_BYTES = 60000
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_JOB_BYTES = 16 * 1024 * 1024
MAX_JOB_ITEMS = 10000
DEFAULT_CAPACITY = dict(max_questions=256, max_request_bytes=MAX_REQUEST_BYTES,
                        max_state_question_bytes=30000, max_concurrency=4,
                        requests_per_minute=1200, request_bytes_per_second=200000)
BOUNDS = dict(max_questions=(1,4096), max_request_bytes=(1024,MAX_REQUEST_BYTES),
              max_state_question_bytes=(512,30000), max_concurrency=(1,32),
              requests_per_minute=(1,100000), request_bytes_per_second=(1024,10000000))
HARD_CAPACITY = DEFAULT_CAPACITY | {'max_questions':4096}


def load(root, route='openrouter'):
    from .reflex import strict_json, require
    try:
        overrides = strict_json((root / 'capacity.json').read_text('utf-8'))
    except FileNotFoundError:
        overrides = {}
    require(type(overrides) is dict and set(overrides) <= set(DEFAULT_CAPACITY) | {'routes'}, 'capacity-fields')
    routes = overrides.get('routes', {})
    require(type(routes) is dict and set(routes) <= {'openrouter','typesafe'}, 'capacity-routes')
    defaults = DEFAULT_CAPACITY | {k:v for k,v in overrides.items() if k != 'routes'}
    def checked(config):
        for key, (low, high) in BOUNDS.items():
            require(type(config[key]) is int and low <= config[key] <= high, 'capacity-value')
        require(config['request_bytes_per_second'] >= config['max_request_bytes'], 'capacity-rate-too-small')
        return config
    checked(defaults)
    for settings in routes.values():
        require(type(settings) is dict and set(settings) <= set(DEFAULT_CAPACITY), 'capacity-fields')
        checked(defaults | settings)
    return checked(defaults | routes.get(route, {}))


def check_wire(wire, limits):
    from .reflex import packed, require
    size = len(packed(wire).encode('utf-8'))
    require(1 <= len(wire['questions']) <= limits['max_questions'], 'item-count')
    require(size <= limits['max_request_bytes'], 'request-size')
    largest = max(len(packed(q).encode('utf-8')) for q in wire['questions'].values())
    require(len(packed(wire['state']).encode('utf-8')) + largest <=
            limits['max_state_question_bytes'], 'state-question-size')
    return size
