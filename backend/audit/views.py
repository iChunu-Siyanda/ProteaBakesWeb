from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import AuditLogSerializer
from .services import (
    get_object_audit_logs,
    get_user_audit_logs,
)


class AuditLogListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = get_user_audit_logs(
            user=request.user
        )

        serializer = AuditLogSerializer(
            logs,
            many=True,
        )

        return Response(serializer.data)


class AuditObjectLogListView(APIView):
    """
    Staff see every log for an object. Customers only see log entries they
    caused themselves, so they can't read other people's activity.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, model_name, object_id):
        logs = get_object_audit_logs(
            model_name=model_name,
            object_id=object_id,
        )

        if not request.user.is_staff:
            logs = logs.filter(user=request.user)

        serializer = AuditLogSerializer(
            logs,
            many=True,
        )

        return Response(serializer.data)
