from django.conf import settings

DEFAULT_MONITORING_LIMIT = getattr(
    settings, "CONSISTENCY_DEFAULT_MONITORING_LIMIT", 10_000
)
DEFAULT_ORDER_BY = getattr(settings, "CONSISTENCY_DEFAULT_ORDER_BY", "-id")
DEFAULT_CHECKER = getattr(
    settings,
    "CONSISTENCY_DEFAULT_CHECKER",
    "consistency_model.tools.ConsistencyChecker",
)

PID_MONITORING_FILENAME = getattr(
    settings, "CONSISTENCY_PID_MONITORING_FILENAME", "consistency_monitoring"
)
PID_MONITORING_FOLDER = getattr(settings, "CONSISTENCY_PID_MONITORING_FOLDER", None)
