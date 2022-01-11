from django.db import models
from django.utils import timezone

from consistency_model import (
    consistency_validator,
    register_consistency,
    ConsistencyChecker,
)


@register_consistency(limit=1, order_by="-created_on")
class OrderWithLastCheck(models.Model):
    created_on = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=100)
    total_items = models.IntegerField(default=0)

    @consistency_validator
    def validate_total_items(self):
        assert self.total_items >= 0, "can't be negative"


class OrderWithSkipCheck(models.Model):
    created_on = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=100)
    total_items = models.IntegerField(default=0)
    skip_consistency_check = models.BooleanField(default=False)

    @consistency_validator
    def validate_total_items(self):
        assert self.total_items >= 0, "can't be negative"


@register_consistency(OrderWithSkipCheck)
class OrderWithSkipCheckConsistency(ConsistencyChecker):
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.exclude(skip_consistency_check=True)
