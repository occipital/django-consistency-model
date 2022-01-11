from django.db import models
from django.utils import timezone

from consistency_model import consistency_validator


class Store(models.Model):
    """
    All items in stock are in here

    """

    created_on = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=100)
    total_items = models.IntegerField(default=0)

    @consistency_validator
    def validate_total_items(self):
        assert self.total_items >= 0, "can't be negative"
