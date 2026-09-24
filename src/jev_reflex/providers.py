"""Code-owned endpoint and version pins. No arbitrary credential destination."""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Profile:
    name: str
    endpoint: str
    request_model: str
    returned_model: str
    key_variable: str


OPENROUTER = Profile('openrouter', 'https://openrouter.ai/api/alpha/decisions',
                     'typesafe/jev-1.13', 'typesafe/jev-1.13-20260917', 'OPENROUTER_API_KEY')
TYPESAFE = Profile('typesafe', 'https://api.typesafe.ai/v1/systemone',
                   'jev-1.13.0', 'jev-1.13.0', 'TYPESAFE_API_KEY')
PROFILES = {p.name: p for p in (OPENROUTER, TYPESAFE)}


def selected():
    from .reflex import require
    name = os.environ.get('JEV_REFLEX_PROVIDER', 'openrouter')
    require(name in PROFILES, 'provider-configuration')
    return PROFILES[name]
