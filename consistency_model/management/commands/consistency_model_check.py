from django.core.management.base import BaseCommand, CommandError
from django.apps import apps

from consistency_model.tools import gen_consistency_errors, gen_validators


class Command(BaseCommand):
    help = "Checks consistency of your data."

    def add_arguments(self, parser):
        parser.add_argument("--filter", type=str, nargs="*")
        parser.add_argument("--exclude", type=str, nargs="*")
        parser.add_argument("--object", type=str, nargs="?")

    def handle(self, *args, **options):
        validators = gen_validators(options["filter"]) if options["filter"] else None
        exclude_validators = (
            gen_validators(options["exclude"]) if options["exclude"] else None
        )
        if options.get("object"):
            object_str = options.get("object")
            if object_str.count(".") != 2:
                raise CommandError(
                    "Wrong object value. The format should be app.model.pk"
                )
            app, model, pk = object_str.split(".")
            objects = [
                apps.get_model(app_label=app, model_name=model).objects.get(pk=pk)
            ]
        else:
            objects = None

        stats = {}
        for v_name, obj, message in gen_consistency_errors(
            validators,
            exclude_validators=exclude_validators,
            objects=objects,
            stats=stats,
        ):
            print("{} [{}] {}".format(v_name, obj.pk, message), file=self.stderr)

        print("\nStats:", file=self.stdout)
        print(
            "\n".join(
                [
                    "{}:{}".format(*a)
                    for a in sorted(stats.items(), key=lambda a: a[1], reverse=True)
                ]
            ),
            file=self.stdout,
        )
