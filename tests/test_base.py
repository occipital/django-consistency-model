from django.test import TestCase
from tests.models import Order
from tests.subapp.models import Store

from consistency_model import (
    gen_consistency_errors,
    gen_validators_by_model,
    gen_validators_by_func,
)


class TestOrderValidators(TestCase):
    def assertEqualErrors(self, generated, tested):
        generated = [(g[0], g[1].pk, g[2]) for g in generated]
        self.assertEqual(generated, tested)

    def setUp(self) -> None:
        Order.objects.create(total=5, refund=0, revenue=5)
        Order.objects.create(total=5, refund=5, revenue=0)
        Order.objects.create(total=5, refund=2, revenue=3)

    def test_all_data_is_good(self):

        order_validators = gen_validators_by_model("tests.Order")
        errors = gen_consistency_errors(order_validators)
        assert not len(list(errors))

    def test_one_fail_data(self):
        last_order = Order.objects.all().last()
        last_order.revenue = 100
        last_order.save()

        order_validators = gen_validators_by_model("tests.Order")
        self.assertEqualErrors(
            gen_consistency_errors(order_validators),
            [
                (
                    "tests.Order.validate_revenue.formula",
                    last_order.pk,
                    "revenue = total - refund",
                )
            ],
        )

    def test_one_fail_data_but_excluded(self):
        last_order = Order.objects.all().last()
        last_order.revenue = 100
        last_order.save()

        order_validators = gen_validators_by_model("tests.Order")
        order_validate_revenue_validators = gen_validators_by_func(
            "tests.Order.validate_revenue"
        )
        self.assertEqualErrors(
            gen_consistency_errors(
                order_validators, exclude_validators=order_validate_revenue_validators
            ),
            [],
        )
        self.assertEqualErrors(
            gen_consistency_errors(
                order_validators,
                create_exclude_validators="tests.Order.validate_revenue",
            ),
            [],
        )
        self.assertEqualErrors(
            gen_consistency_errors(
                order_validators,
                exclude_validators=dict(order_validate_revenue_validators),
            ),
            [],
        )

    def test_test_fail_with_unhandled_exception(self):
        last_order = Order.objects.all().last()
        last_order.total = -100
        last_order.save()

        order_validators = gen_validators_by_func("tests.Order.validate_total")
        self.assertEqualErrors(
            gen_consistency_errors(order_validators),
            [
                (
                    "tests.Order.validate_total",
                    last_order.pk,
                    "<class 'AssertionError'>:can't be negative",
                ),
            ],
        )

    def test_multiple_failed_data_in_one_validator(self):
        last_order = Order.objects.all().last()
        last_order.revenue = -100
        last_order.save()

        order_validators = gen_validators_by_func("tests.Order.validate_revenue")
        self.assertEqualErrors(
            gen_consistency_errors(order_validators),
            [
                (
                    "tests.Order.validate_revenue.negative",
                    last_order.pk,
                    "can't be negative",
                ),
                (
                    "tests.Order.validate_revenue.formula",
                    last_order.pk,
                    "revenue = total - refund",
                ),
            ],
        )

    def test_all_good_using_query(self):
        self.assertEqualErrors(
            gen_consistency_errors(objects=Order.objects.all()),
            [],
        )

    def test_test_fail_using_query(self):
        last_order = Order.objects.all().last()
        last_order.total = -100
        last_order.save()

        self.assertEqualErrors(
            gen_consistency_errors(objects=Order.objects.all()),
            [
                (
                    "tests.Order.validate_total",
                    last_order.pk,
                    "<class 'AssertionError'>:can't be negative",
                ),
                (
                    "tests.Order.validate_revenue.formula",
                    last_order.pk,
                    "revenue = total - refund",
                ),
            ],
        )

        self.assertEqualErrors(
            gen_consistency_errors(objects=Order.objects.exclude(id=last_order.pk)),
            [],
        )

    def test_all_good_using_list(self):
        self.assertEqualErrors(
            gen_consistency_errors(objects=list(Order.objects.all())),
            [],
        )

    def test_fail_using_list(self):
        last_order = Order.objects.all().last()
        last_order.total = -100
        last_order.save()

        self.assertEqualErrors(
            gen_consistency_errors(objects=[last_order]),
            [
                (
                    "tests.Order.validate_total",
                    last_order.pk,
                    "<class 'AssertionError'>:can't be negative",
                ),
                (
                    "tests.Order.validate_revenue.formula",
                    last_order.pk,
                    "revenue = total - refund",
                ),
            ],
        )

        self.assertEqualErrors(
            gen_consistency_errors(objects=[Order.objects.all().first()]),
            [],
        )


class TestSubAppStorage(TestCase):
    def setUp(self) -> None:
        Store.objects.create(name="blocks", total_items=15)

    def test_all_data_is_good(self):

        order_validators = gen_validators_by_model("subapp.Store")
        errors = gen_consistency_errors(order_validators)
        assert not len(list(errors))
