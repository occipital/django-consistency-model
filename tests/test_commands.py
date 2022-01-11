from io import StringIO

from django.test import TestCase
from django.core.management import call_command

from tests.models import Order
from tests.subapp.models import Store
from consistency_model.models import ConsistencyFail


def call_command_stdout(*args):
    out = StringIO()
    err = StringIO()
    call_command(*args, stdout=out, stderr=err)
    return out.getvalue(), err.getvalue()


class TestCheck(TestCase):
    def setUp(self) -> None:
        Order.objects.create(total=5, refund=0, revenue=5)
        Order.objects.create(total=5, refund=5, revenue=0)
        Order.objects.create(total=5, refund=2, revenue=3)

        Store.objects.create(name="blocks", total_items=15)
        Store.objects.create(name="tools", total_items=10)

    def test_all_objects(self):
        out, err = call_command_stdout("consistency_model_check")
        assert not err
        assert "tests.Order.validate_total" in out
        assert "tests.Order.validate_revenue" in out
        assert "subapp.Store.validate_total_items" in out

    def test_one_obj_fail_found(self):
        obj = Store.objects.get(name="tools")
        obj.total_items = -10
        obj.save()

        out, err = call_command_stdout("consistency_model_check")

        assert (
            "subapp.Store.validate_total_items [{}] <class 'AssertionError'>:can't be negative".format(
                obj.id
            )
            in err
        )

    def test_check_only_orders(self):
        obj = Store.objects.get(name="tools")
        obj.total_items = -10
        obj.save()

        out, err = call_command_stdout(
            "consistency_model_check", "--filter", "tests.Order"
        )
        assert not err

        out, err = call_command_stdout(
            "consistency_model_check", "--filter", "tests.Order", "subapp"
        )
        assert err

    def test_exclude_subapp(self):
        obj = Store.objects.get(name="tools")
        obj.total_items = -10
        obj.save()

        out, err = call_command_stdout("consistency_model_check", "--exclude", "subapp")
        assert not err

        out, err = call_command_stdout(
            "consistency_model_check", "--exclude", "tests.Order"
        )
        assert err

        out, err = call_command_stdout(
            "consistency_model_check",
            "--exclude",
            "tests.Order",
            "subapp.Store.validate_total_items",
        )
        assert not err

    def test_single_object(self):
        obj = Store.objects.get(name="tools")
        obj.total_items = -10
        obj.save()

        valid_obj = Store.objects.get(name="blocks")

        out, err = call_command_stdout(
            "consistency_model_check",
            "--object",
            "subapp.Store.{}".format(valid_obj.pk),
        )
        assert not err

        out, err = call_command_stdout(
            "consistency_model_check", "--object", "subapp.Store.{}".format(obj.pk)
        )
        assert err

        out, err = call_command_stdout(
            "consistency_model_check",
            "--exclude",
            "subapp.Store.validate_total_items",
            "--object",
            "subapp.Store.{}".format(obj.pk),
        )
        assert not err


class TestMonitoring(TestCase):
    def setUp(self) -> None:
        Order.objects.create(total=5, refund=0, revenue=5)
        Order.objects.create(total=5, refund=5, revenue=0)
        Order.objects.create(total=5, refund=2, revenue=3)

        Store.objects.create(name="blocks", total_items=15)
        Store.objects.create(name="tools", total_items=10)

    def assertUnresolvedFails(self, check):
        unresolved_checks = [
            (f.validator_name, f.object_id)
            for f in ConsistencyFail.objects.filter(resolved=False)
        ]
        self.assertEqual(unresolved_checks, check)

    def test_all_data_is_good(self):
        call_command("consistency_model_monitoring")
        self.assertUnresolvedFails([])

    def test_store_fail(self):
        obj1 = Store.objects.get(name="tools")
        obj1.total_items = -10
        obj1.save()

        call_command("consistency_model_monitoring")
        self.assertUnresolvedFails([("subapp.Store.validate_total_items", obj1.pk)])

        call_command("consistency_model_monitoring")
        self.assertUnresolvedFails([("subapp.Store.validate_total_items", obj1.pk)])

        obj2 = Store.objects.get(name="blocks")
        obj2.total_items = -15
        obj2.save()

        call_command("consistency_model_monitoring")
        self.assertUnresolvedFails(
            [
                ("subapp.Store.validate_total_items", obj1.pk),
                ("subapp.Store.validate_total_items", obj2.pk),
            ]
        )

        call_command("consistency_model_monitoring")
        self.assertUnresolvedFails(
            [
                ("subapp.Store.validate_total_items", obj1.pk),
                ("subapp.Store.validate_total_items", obj2.pk),
            ]
        )

        obj1.total_items = 5
        obj1.save()

        call_command("consistency_model_monitoring")
        self.assertUnresolvedFails(
            [
                ("subapp.Store.validate_total_items", obj2.pk),
            ]
        )

        call_command("consistency_model_monitoring")
        self.assertUnresolvedFails(
            [
                ("subapp.Store.validate_total_items", obj2.pk),
            ]
        )

        obj2.total_items = 5
        obj2.save()

        call_command("consistency_model_monitoring")
        self.assertUnresolvedFails([])

    def test_order_fail_with_named_errors(self):
        obj1, obj2, obj3 = list(Order.objects.all())

        obj1.revenue = -10
        obj1.save()

        call_command("consistency_model_monitoring")
        self.assertUnresolvedFails(
            [
                ("tests.Order.validate_revenue.negative", obj1.pk),
                ("tests.Order.validate_revenue.formula", obj1.pk),
            ]
        )

        call_command("consistency_model_monitoring")
        self.assertUnresolvedFails(
            [
                ("tests.Order.validate_revenue.negative", obj1.pk),
                ("tests.Order.validate_revenue.formula", obj1.pk),
            ]
        )

        obj2.revenue = -20
        obj2.save()

        call_command("consistency_model_monitoring")
        self.assertUnresolvedFails(
            [
                ("tests.Order.validate_revenue.negative", obj1.pk),
                ("tests.Order.validate_revenue.formula", obj1.pk),
                ("tests.Order.validate_revenue.negative", obj2.pk),
                ("tests.Order.validate_revenue.formula", obj2.pk),
            ]
        )

        obj1.revenue = 100
        obj1.save()

        call_command("consistency_model_monitoring")
        self.assertUnresolvedFails(
            [
                ("tests.Order.validate_revenue.formula", obj1.pk),
                ("tests.Order.validate_revenue.negative", obj2.pk),
                ("tests.Order.validate_revenue.formula", obj2.pk),
            ]
        )

        obj1.revenue = 5
        obj1.save()

        call_command("consistency_model_monitoring")
        self.assertUnresolvedFails(
            [
                ("tests.Order.validate_revenue.negative", obj2.pk),
                ("tests.Order.validate_revenue.formula", obj2.pk),
            ]
        )

        obj2.revenue = 0
        obj2.save()

        call_command("consistency_model_monitoring")
        self.assertUnresolvedFails([])
