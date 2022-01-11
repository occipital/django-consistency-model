from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


class ConsistencyFail(models.Model):
    """
    The result of consistency_model_monitoring command
    """

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now_add=True)
    resolved_on = models.DateTimeField(null=True)
    validator_name = models.CharField(max_length=500)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    message = models.TextField()
    resolved = models.BooleanField(default=False, db_index=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["validator_name", "object_id", "resolved_on"],
                name="consistency_fail_vor",
            )
        ]

    def resolve(self):
        assert not self.resolved
        self.resolved = True
        self.resolved_on = timezone.now()
        self.save()

    def update_message(self, msg):
        assert not self.resolved
        str_msg = str(msg)
        if self.message == str_msg:
            return
        self.message = str_msg
        self.updated_on = timezone.now()
        self.save()

    def __str__(self) -> str:
        return f"{self.validator_name}: {self.message}" + (
            " - RESOLVED" if self.resolved else ""
        )
