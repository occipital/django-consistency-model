from django.test import TestCase

from consistency_model import (
    gen_consistency_errors,
)

from tests.custom_consistency.models import OrderWithLastCheck, OrderWithSkipCheck


class TestOrderWithLastCheck(TestCase):
    def setUp(self) -> None:
        OrderWithLastCheck.objects.create(name="First", total_items=10)
        OrderWithLastCheck.objects.create(name="Last", total_items=10)

    def test_all_good(self):
        errors = gen_consistency_errors(
            create_validators="custom_consistency.OrderWithLastCheck",
        )
        assert not list(errors)

    def test_first_will_not_be_checked(self):
        order = OrderWithLastCheck.objects.get(name="First")
        order.total_items = -10
        order.save()

        errors = gen_consistency_errors(
            create_validators="custom_consistency.OrderWithLastCheck",
        )
        assert not list(errors)

    def test_last_will_not_be_checked(self):
        order = OrderWithLastCheck.objects.get(name="Last")
        order.total_items = -10
        order.save()

        errors = gen_consistency_errors(
            create_validators="custom_consistency.OrderWithLastCheck",
        )
        assert list(errors)


class TestOrderWithSkipCheck(TestCase):
    def setUp(self) -> None:
        OrderWithSkipCheck.objects.create(name="First", total_items=10)
        OrderWithSkipCheck.objects.create(name="Last", total_items=10)

    def test_all_good(self):
        errors = gen_consistency_errors(
            create_validators="custom_consistency.OrderWithSkipCheck",
        )
        assert not list(errors)

    def test_fail_if_not_skip(self):
        order = OrderWithSkipCheck.objects.first()
        order.total_items = -10
        order.save()

        errors = gen_consistency_errors(
            create_validators="custom_consistency.OrderWithSkipCheck",
        )
        assert list(errors)

    def test_not_fail_if_skip(self):
        order = OrderWithSkipCheck.objects.first()
        order.total_items = -10
        order.skip_consistency_check = True
        order.save()

        errors = gen_consistency_errors(
            create_validators="custom_consistency.OrderWithSkipCheck",
        )
        assert not list(errors)
