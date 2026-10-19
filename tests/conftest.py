"""Load explicit local/test environment before pytest evaluates skip markers.

Does not override existing environment values. Production dotenv is disabled.
"""
from aao.settings import load_local_env

load_local_env()
