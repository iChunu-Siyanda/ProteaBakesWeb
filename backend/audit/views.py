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
    permission_classes = [IsAuthenticated]

    def get(self, request, model_name, object_id):
        logs = get_object_audit_logs(
            model_name=model_name,
            object_id=object_id,
        )

        serializer = AuditLogSerializer(
            logs,
            many=True,
        )

        return Response(serializer.data)
