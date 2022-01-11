import tempfile

try:
    from pid.decorator import pidfile
except ImportError:

    def pidfile(*args, **kwargs):
        def _(f):
            return f

        return _


from django.core.management.base import BaseCommand

from consistency_model.tools import (
    gen_validators_by_func,
    gen_validators,
    gen_consistency_errors,
)
from consistency_model.models import ConsistencyFail
from consistency_model.settings import PID_MONITORING_FILENAME, PID_MONITORING_FOLDER


class Command(BaseCommand):
    help = "Cron Command for monotoring models consistency. All of the inconsistencies will be saved as ConsistencyFail object"

    def add_arguments(self, parser):
        parser.add_argument("--filter", type=str, nargs="*")
        parser.add_argument("--exclude", type=str, nargs="*")

    @pidfile(
        piddir=(
            PID_MONITORING_FOLDER if PID_MONITORING_FOLDER else tempfile.gettempdir()
        ),
        pidname=PID_MONITORING_FILENAME,
    )
    def handle(self, *args, **options):

        validators = gen_validators(options["filter"]) if options["filter"] else None
        exclude_validators = (
            gen_validators(options["exclude"]) if options["exclude"] else None
        )

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
