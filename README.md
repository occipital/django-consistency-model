[![PyPI version fury.io](https://badge.fury.io/py/django-consistency-model.svg)](https://pypi.python.org/pypi/django-consistency-model/) 
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/django-consistency-model.svg)](https://pypi.python.org/pypi/django-consistency-model/)
[![PyPI - Django Version](https://img.shields.io/pypi/djversions/django-consistency-model)](https://pypi.python.org/pypi/django-consistency-model/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# Django Consistency Model

DCM is a set of tools that helps you to keep your data in your Django Models consistent.

![Django Consistency Model](https://github.com/occipital/django-consistency-model/blob/master/title-800.png)

## Motivation

* You have a lot of legacy and inconsistent data in your project and you need to clean it out
* You want to monitor the broken data
* You are looking for a very simple solution.

## Quick Start

Install the package:

```bash
pip install django-consistency-model
```

Add new app into `INSTALLED_APPS`:

```python
INSTALLED_APPS = (
    # ...
    "consistency_model",
)
```

Add your first validator using decorator consistency_validator:

```python
from decimal import Decimal
from django.db import models
from consistency_model import consistency_validator

class Order(models.Model):
    total = models.DecimalField(
        default=Decimal("0.00"), decimal_places=2, max_digits=10
    )
    refund = models.DecimalField(
        default=Decimal("0.00"), decimal_places=2, max_digits=10
    )
    revenue = models.DecimalField(
        default=Decimal("0.00"), decimal_places=2, max_digits=10
    )

    @consistency_validator
    def validate_revenue(self):
        assert self.revenue == self.total - self.refund, "revenue = total - refund"
```

Run command to check validators:

```bash
./manage.py consistency_model_check
```

## What if I need to check more than one condition in one validator

The first thing you may think of is using more than one validator, and it is common to have more than one validator (for example, one validator per field).

Sometimes, you want to check more than one aspect in one validator or have a complex calculation you don't want to do for every validator.

For those cases, you may want to use function `consistency_error`. It shows the system an error without raising an exception, so one validator can generate more than one error.

```python
from decimal import Decimal

from django.db import models

from consistency_model import consistency_validator, consistency_error


class Order(models.Model):
    total = models.DecimalField(
        default=Decimal("0.00"), decimal_places=2, max_digits=10
    )
    refund = models.DecimalField(
        default=Decimal("0.00"), decimal_places=2, max_digits=10
    )
    revenue = models.DecimalField(
        default=Decimal("0.00"), decimal_places=2, max_digits=10
    )

    @consistency_validator
    def validate_total(self):
        assert self.total >= 0, "can't be negative"

    @consistency_validator
    def validate_revenue(self):
        if self.revenue < 0:
            consistency_error("can't be negative", "negative")

        if self.revenue != self.total - self.refund:
            consistency_error("revenue = total - refund", "formula")
```

As you can see, one validator (`validate_revenue`) checks two factors of the field revenue.

The function `consistency_error` has two arguments - message and name(optional). The name is a unique value for the validator and will be used in monitoring.

## I don't want to check all of the data, but only one model instead.

When you add a new validator, you don't want to check all the data. You want to test only one validator instead.

Argument `--filter` can help you with that

```bash
./manage.py consistency_model_check --filter storeapp.Order.validate_revenue
```

Check only one model

```bash
./manage.py consistency_model_check --filter storeapp.Order
```

Check the model but excluding one validator. Argument `--exclude` excludes validator from validation circle.

```bash
./manage.py consistency_model_check --filter storeapp.Order --exclude storeapp.Order.validate_revenue
```

Check only one object. Using `--object` you can check a specific object in db.

```bash
./manage.py consistency_model_check --object storeapp.Order.56
```

You can combine `--object` with `--filter` and `--exclude` as well.

## I want to monitor my DB on consistency constantly.

The idea of consistency monitoring is very simple. You add the command `consistency_model_monitoring` to your cron. The command checks DB and saves all of the errors in `ConsistencyFail`. Nothing is too complicated.

As the result, you can see all of the inconsistency errors in admin panel. Or you can connect `pre_save` signal to `consistency_model.ConsistencyFail` and send an email notification in case of any new inconsistency.

## Monitoring configuration.

A typical situation is when you don't want to monitor all the data but only recently added/updated data. By default, the system checks only 10k recent IDs, but you have a lot of flexibility to change that with function `register_consistency`.

Let's take a look of how one can be used.

For model `Order` you want to check only 10 last ids.

```python
from consistency_model import register_consistency
register_consistency(Order, limit=10)
```

`register_consistency` can be used as class decorator

```python
from consistency_model import register_consistency

@register_consistency(limit=10)
class Order(models.Model):
    # ...
```

you can order not by id, but `modified_on` field

```python
from consistency_model import register_consistency
register_consistency(Order, order_by='modified_on')
```

you can use a consistency checker class to overwrite the whole query for consistency check

```python
from django.db import models

from consistency_model import register_consistency, ConsistencyChecker


class Order(models.Model):
    is_legacy = models.BooleanField(dafult=False)
    # ...


class OrderConsistencyChecker(ConsistencyChecker):
    limit = None # I don't want to have any limitation
    order_by = 'modified_on'

    def get_queryset(self):
        return self.cls.objects.filter(is_legacy=False)

register_consistency(Order, OrderConsistencyChecker)
```

Again, it is possible to be used as class decorator for any  on both classes.

For Model:

```python
from django.db import models

from consistency_model import register_consistency, ConsistencyChecker


class OrderConsistencyChecker(ConsistencyChecker):
    # ...

@register_consistency(OrderConsistencyChecker)
class Order(models.Model):
    is_legacy = models.BooleanField(dafult=False)
    # ...

```

For Checker:

```python
from django.db import models

from consistency_model import register_consistency, ConsistencyChecker


class Order(models.Model):
    is_legacy = models.BooleanField(dafult=False)
    # ...


@register_consistency(Order)
class OrderConsistencyChecker(ConsistencyChecker):
    # ...

```

## Settings

`CONSISTENCY_DEFAULT_MONITORING_LIMIT` (default: `10_000`) - default limit rows per model

`CONSISTENCY_DEFAULT_ORDER_BY` (default: `"-id"`) - defaul model ordering for monitoring

`CONSISTENCY_DEFAULT_CHECKER` (default: `"consistency_model.tools.ConsistencyChecker"`) - default class for consistency monitoring

If you have `pid` package installed, one will be used for monitoring command to prevent running multiple monitpring process. The following settings will be used for monitoring

`CONSISTENCY_PID_MONITORING_FILENAME` (default: `"consistency_monitoring"`) 

`CONSISTENCY_PID_MONITORING_FOLDER` (default: `None`) - folder the pid file is stored. `tempfile.gettempdir()` is using if it is `None`

## Contributing

We’re looking to grow the project and get more contributors especially to support more languages/versions. We’d also like to get the .pre-commit-hooks.yaml files added to popular linters without maintaining forks / mirrors.

Feel free to submit bug reports, pull requests, and feature requests.

Tools:

* [tox](https://tox.wiki/en/latest/)
* [pre-commit](https://pre-commit.com/)
* [black](https://github.com/psf/black)
