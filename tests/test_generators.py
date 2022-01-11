from django.test import TestCase

from consistency_model import (
    gen_validators_by_model,
    gen_validators_by_app,
    gen_validators_by_func,
    gen_validators,
)


class TestGenerators(TestCase):
    def assertEqualValidators(self, generated, tested):
        generated = [(g[0], set([f.__name__ for f in g[1]])) for g in generated]
        self.assertEqual(generated, tested)

    def test_by_model(self):
        self.assertEqualValidators(
            gen_validators_by_model("tests.Order"),
            [(("tests", "Order"), {"validate_total", "validate_revenue"})],
        )
        self.assertEqualValidators(
            gen_validators_by_model("subapp.Store"),
            [(("subapp", "Store"), {"validate_total_items"})],
        )
        self.assertEqualValidators(
            gen_validators_by_model("tests.Unknown"),
            [],
        )
        self.assertEqualValidators(
            gen_validators_by_model(["tests.Order", "subapp.Store"]),
            [
                (("tests", "Order"), {"validate_total", "validate_revenue"}),
                (("subapp", "Store"), {"validate_total_items"}),
            ],
        )

    def test_by_app(self):
        self.assertEqualValidators(
            gen_validators_by_app("tests"),
            [
                (("tests", "Order"), {"validate_total", "validate_revenue"}),
                (("tests", "OrderItem"), {"validate_price"}),
            ],
        )
        self.assertEqualValidators(
            gen_validators_by_app("subapp"),
            [(("subapp", "Store"), {"validate_total_items"})],
        )
        self.assertEqualValidators(
            gen_validators_by_app("unknown"),
            [],
        )
        self.assertEqualValidators(
            gen_validators_by_app(["tests", "subapp"]),
            [
                (("tests", "Order"), {"validate_total", "validate_revenue"}),
                (("tests", "OrderItem"), {"validate_price"}),
                (("subapp", "Store"), {"validate_total_items"}),
            ],
        )

    def test_by_func(self):
        self.assertEqualValidators(
            gen_validators_by_func("tests.Order.validate_total"),
            [(("tests", "Order"), {"validate_total"})],
        )

        self.assertEqualValidators(
            gen_validators_by_func("subapp.Store.validate_total_items"),
            [(("subapp", "Store"), {"validate_total_items"})],
        )
        self.assertEqualValidators(
            gen_validators_by_func("tests.Store.unknown"),
            [],
        )
        self.assertEqualValidators(
            gen_validators_by_func("tests.Unknown.validate_total_items"),
            [],
        )
        self.assertEqualValidators(
            gen_validators_by_func(
                ["tests.Order.validate_total", "tests.Order.validate_revenue"]
            ),
            [(("tests", "Order"), {"validate_total", "validate_revenue"})],
        )
        self.assertEqualValidators(
            gen_validators_by_func(
                [
                    "tests.Order.validate_total",
                    "tests.Order.validate_revenue",
                    "subapp.Store.validate_total_items",
                ]
            ),
            [
                (("tests", "Order"), {"validate_total", "validate_revenue"}),
                (("subapp", "Store"), {"validate_total_items"}),
            ],
        )

    def test_by_name(self):
        self.assertEqualValidators(
            gen_validators("tests.Order"),
            [(("tests", "Order"), {"validate_total", "validate_revenue"})],
        )
        self.assertEqualValidators(
            gen_validators(["tests.Order", "subapp.Store.validate_total_items"]),
            [
                (("tests", "Order"), {"validate_total", "validate_revenue"}),
                (("subapp", "Store"), {"validate_total_items"}),
            ],
        )
        self.assertEqualValidators(
            gen_validators(
                ["tests.Order", "subapp.Store.validate_total_items", "tests"]
            ),
            [
                (("tests", "Order"), {"validate_total", "validate_revenue"}),
                (("subapp", "Store"), {"validate_total_items"}),
                (("tests", "Order"), {"validate_total", "validate_revenue"}),
                (("tests", "OrderItem"), {"validate_price"}),
            ],
        )
