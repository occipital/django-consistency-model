__title__ = "Django Consistency Model"
__version__ = "0.1"
__author__ = "Alex Liabakh"

from .tools import (
    ConsistencyChecker,
    register_consistency,
    consistency_error,
    consistency_validator,
    gen_validators_by_model,
    gen_validators_by_app,
    gen_validators_by_func,
    gen_validators,
    gen_consistency_errors,
)
