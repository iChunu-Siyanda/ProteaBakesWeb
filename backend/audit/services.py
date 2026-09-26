from .models import AuditLog

def create_audit_log(
    *,
    action,
    user=None,
    model_name="",
    object_id="",
    details=None,
    ip_address=None,
):
    return AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id else "",
        details=details or {},
        ip_address=ip_address,
    )


def get_user_audit_logs(*, user):
    return AuditLog.objects.filter(
        user=user
    ).order_by("-created_at")


def get_object_audit_logs(*, model_name, object_id):
    return AuditLog.objects.filter(
        model_name=model_name,
        object_id=str(object_id),
    ).order_by("-created_at")
