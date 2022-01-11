from decimal import Decimal

from django.db import models
from django.utils import timezone

from consistency_model import consistency_validator, consistency_error


class Order(models.Model):
    """

    total - the amount that initially was charged
    refund - the amount was later refunded
    revenue - the total revenue from that order

    """

    created_on = models.DateTimeField(default=timezone.now)
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


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    name = models.CharField(max_length=10)
    price = models.DecimalField(decimal_places=2, max_digits=10)

    @consistency_validator
    def validate_price(self):
        assert self.total >= 0, "can't be negative"
