from collections import defaultdict
from contextlib import contextmanager
from typing import (
    Any,
    Callable,
    Dict,
    Tuple,
    Union,
    Generator,
    Iterable,
    Optional,
    List,
)

from django.apps import apps
from django.db import models
from django.db.models.base import Model
from django.db.models.query import QuerySet
from django.utils.module_loading import import_string

from .settings import DEFAULT_MONITORING_LIMIT, DEFAULT_ORDER_BY, DEFAULT_CHECKER

TValidators = Generator[
    Tuple[Tuple[str, str], List[Callable[[Any], Optional[bool]]]], None, None
]

# all of the validators available in the project.
# (app: str, model: str) => [func, func, ...]
VALIDATORS: Dict[Tuple[str, str], List[Callable[[Any], Optional[bool]]]] = defaultdict(
    list
)

# all checkers in the system.
# Model => ConsistencyChecker(Model)
CONSISTENCY_CHECKERS = {}


class ConsistencyChecker:
    """
    the class explains how specific model should be monitored.
    """

    limit = DEFAULT_MONITORING_LIMIT
    order_by = DEFAULT_ORDER_BY
    queryset = None

    def __init__(self, cls, **kwargs) -> None:
        self.cls = cls
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_queryset(self):
        if self.queryset is not None:
            return self.queryset

        order_by = self.order_by
        if isinstance(order_by, str):
            order_by = (order_by,)

        return self.cls.objects.all().order_by(*order_by)

    def get_objects(self):
        queryset = self.get_queryset()

        if self.limit is None:
            return queryset

        return queryset[: self.limit]


def _register_consistency(cls, cls_checker=None, **kwargs):
    if cls_checker is None:
        cls_checker = import_string(DEFAULT_CHECKER)
    new_checker = cls_checker(cls, **kwargs)

    assert issubclass(cls, Model)
    assert isinstance(new_checker, ConsistencyChecker)

    CONSISTENCY_CHECKERS[cls] = new_checker
    return new_checker


def register_consistency(*args, **kwargs):
    """
    assign ConsistencyChecker to the django Model.

    can be used asa decorator or a function.
    """
    if not args or not issubclass(args[0], models.Model):

        def _(cls):
            _register_consistency(cls, *args, **kwargs)
            return cls

        return _

    def _(cls_checker):
        _register_consistency(*args, cls_checker=cls_checker, **kwargs)
        return cls_checker

    _register_consistency(*args, **kwargs)
    return _


def get_register_consistency(cls):

    if cls in CONSISTENCY_CHECKERS:
        return CONSISTENCY_CHECKERS[cls]
    return _register_consistency(cls)


_ERRORS = []


def consistency_error(message: Any = "", name: Optional[str] = None) -> None:
    """
    for cases when validator can raise more than one error use this function.

    name is a unique value for the function where consistency_error is called.

    the name is using for consistency_model_monitoring command
    """
    assert name is None or "." not in name, "(dot) can't be part of the name"
    global _ERRORS
    _ERRORS.append((message, name))


@contextmanager
def trace_consistency_errors():
    """
    context manager for catching consistency_error calls
    """
    global _ERRORS
    prev_errors = _ERRORS
    errors = _ERRORS = []
    try:
        yield errors
    finally:
        _ERRORS = prev_errors


def consistency_validator(func):
    """
    decorator for model's method that register that function as consistency validator
    """
    model = func.__qualname__.split(".")[0]
    app = func.__module__.split(".")[-2]

    VALIDATORS[(app, model)].append(func)
    return func


def gen_validators_by_model(names: Union[Iterable[str], str]) -> TValidators:
    """
    Generator of validators by model name(s).

    Model name is string in format "app.Model".

    @names - can be a string (one model name) or iterable of strings where each item is a model name
    """
    if isinstance(names, str):
        names = [names]
    _names = [tuple(n.split(".")) for n in names]
    for name, list_funcs in VALIDATORS.items():
        if name in _names:
            yield name, list_funcs


def gen_validators_by_app(names: Union[Iterable[str], str]) -> TValidators:
    """
    Generator of validators by app name(s).

    @names - can be a string (one app name) or iterable of strings where each item is a app name
    """
    if isinstance(names, str):
        names = [names]
    names = set(names)
    for name, list_funcs in VALIDATORS.items():
        if name[0] in names:
            yield name, list_funcs


def gen_validators_by_func(names: Union[Iterable[str], str]) -> TValidators:
    """
    Generator of validators by function(validator) name(s).

    Model name is string in format "app.Model".

    @names - can be a string (one model name) or iterable of strings where each item is a model name
    """
    if isinstance(names, str):
        names = [names]
    _names = [tuple(n.split(".")) for n in names]

    funcs = defaultdict(set)
    for name in _names:
        funcs[name[:2]].add(name[2])

    for name, list_funcs in VALIDATORS.items():
        if name in funcs.keys():
            filtered_list_funcs = [f for f in list_funcs if f.__name__ in funcs[name]]
            if filtered_list_funcs:
                yield name, filtered_list_funcs


def gen_validators(names: Union[Iterable[str], str]) -> TValidators:
    """
    Generator of validators by name(s).

    The name can be app name, model name or func name.

    @names - can be a string (one name) or iterable of strings where each item is a name
    """
    if isinstance(names, str):
        names = [names]

    for name in names:
        count_dots = name.count(".")
        if not count_dots:
            yield from gen_validators_by_app(name)
        elif count_dots == 1:
            yield from gen_validators_by_model(name)
        elif count_dots == 2 or count_dots == 3:
            yield from gen_validators_by_func(name)
        else:
            raise ValueError(f'Unknow format for name "{name}"')


def gen_consistency_errors(
    validators=None,
    objects=None,
    create_validators=None,
    exclude_validators=None,
    create_exclude_validators=None,
    stats=None,
) -> Generator[Tuple[str, Any, Any], None, None]:
    """
    generates inconsistency errors based on project validators.

    @validators - filter validators you want to use for model validation.

    Can be set as:
        * generator from `gen_validators_*`
        * iterable of ((app:str, model:str), [func, func, ...])
        * dict of (app: str, model: str) => [func, func, ...]
        * None (default) - all project validators

    @objects - objects we want to validate. All objects should be the same model

    Can be set as:
        * list/tuple of the objects
        * queryset

    @create_validators - (can't be set when validators are set)
        Generate validators using function gen_validators

    @exclude_validators the same as @validators, but works in oposite way.
    It describes which validators we don't want to use for validation.
    None means nothing is excluded.

    @create_exclude_validators the same @create_validators but for @exclude_validators

    @stats - link to an empty dict for collecting validation stats.
    Is using for commands.
    """

    assert not (
        validators is not None and create_validators is not None
    ), "can not set both validators and create_validators"

    if objects is None:
        objects_cls = None
    elif isinstance(objects, QuerySet):
        objects_cls = objects.model
    else:
        objects_cls = objects[0]._meta.model

    if create_validators is not None:
        validators = gen_validators(create_validators)

    if validators is None:
        validators = VALIDATORS

    if isinstance(validators, dict):
        validators = validators.items()

    if create_exclude_validators is not None:
        exclude_validators = gen_validators(create_exclude_validators)

    if exclude_validators is None:
        exclude_validators = {}

    if not isinstance(exclude_validators, dict):
        exclude_validators = dict(exclude_validators)

    for name, list_funcs in validators:
        if name in exclude_validators:
            exclude_funcs = exclude_validators[name]
            list_funcs = list(set(list_funcs).difference(set(exclude_funcs)))

        if not list_funcs:
            continue

        app_label, model = name
        cls_model = apps.get_model(app_label=app_label, model_name=model)

        if objects_cls is not None and cls_model != objects_cls:
            continue

        if objects_cls:
            objects_all = objects
        else:
            objects_all = get_register_consistency(cls_model).get_objects()

        for obj in objects_all:
            for func in list_funcs:
                with trace_consistency_errors() as errors:
                    validator_name = "{}.{}.{}".format(app_label, model, func.__name__)
                    check_stats_k = "check." + validator_name
                    count_stats = True
                    try:
                        count_stats = not func(obj)
                    except Exception as e:
                        if stats is not None:
                            stats_k = "ERR." + validator_name
                            stats[stats_k] = stats.get(stats_k, 0) + 1
                            stats[check_stats_k] = stats.get(check_stats_k, 0) + 1
                        yield (
                            validator_name,
                            obj,
                            "{}:{}".format(e.__class__, e),
                        )
                    finally:
                        if count_stats and stats is not None:
                            stats[check_stats_k] = stats.get(check_stats_k, 0) + 1
                        for (message, name) in errors:
                            if stats is not None:
                                stats_k = "ERR." + validator_name
                                stats[stats_k] = stats.get(stats_k, 0) + 1

                            validator_name_message = validator_name
                            if name:
                                validator_name_message += "." + name
                            yield (validator_name_message, obj, message)


def monitoring_iteration(validators=None, exclude_validators=None) -> None:
    """
    One iteration of monitoring that checks consistency using @validators and @exclude_validators
    and saves the result into ConsistencyFail model
    """
    from .models import ConsistencyFail

    fail_ids = set()

    for validator_name, obj, message in gen_consistency_errors(
        validators,
        exclude_validators=exclude_validators,
    ):
        fail = ConsistencyFail.objects.filter(
            resolved=False,
            validator_name=validator_name,
            object_id=obj.id,
        ).first()
        if fail:
            fail.update_message(message)
        else:
            fail = ConsistencyFail.objects.create(
                validator_name=validator_name,
                content_object=obj,
                message=str(message),
            )
        fail_ids.add(fail.id)

    for fail in ConsistencyFail.objects.filter(resolved=False):
        if fail.id in fail_ids:
            continue

        func_validators = gen_validators_by_func(fail.validator_name)
        for validator_name, obj, message in gen_consistency_errors(
            func_validators, objects=[fail.content_object]
        ):
            if fail.validator_name == validator_name:
                fail.update_message(message)
                break
        else:
            fail.resolve()
