from django.contrib import admin

from .models import ConsistencyFail


class ConsistencyFailAdmin(admin.ModelAdmin):
    list_display = [
        "created_on",
        "content_object",
        "validator_name",
        "resolved",
        "message",
    ]
    list_filter = ["resolved"]
    search_fields = ["validator_name"]


admin.site.register(ConsistencyFail, ConsistencyFailAdmin)
