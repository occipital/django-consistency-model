import tempfile

try:
    from pid.decorator import pidfile
except ImportError:

    def pidfile(*args, **kwargs):
        def _(f):
            return f

        return _


from django.core.management.base import BaseCommand

from consistency_model import (
    gen_validators,
    monitoring_iteration,
)
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
        monitoring_iteration(validators, exclude_validators)
