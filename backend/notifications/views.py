from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    NotificationPreferenceSerializer,
    NotificationSerializer,
)
from .services import (
    get_or_create_notification_preferences,
    get_user_notifications,
    mark_notification_as_read,
    update_notification_preferences,
)


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = get_user_notifications(user=request.user)

        serializer = NotificationSerializer(
            notifications,
            many=True,
        )

        return Response(serializer.data)


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        try:
            notification = mark_notification_as_read(
                notification_id=notification_id,
                user=request.user,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            NotificationSerializer(notification).data,
            status=status.HTTP_200_OK,
        )


class NotificationPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        preferences = get_or_create_notification_preferences(
            user=request.user,
        )

        serializer = NotificationPreferenceSerializer(
            preferences,
        )

        return Response(serializer.data)


    def patch(self, request):
        serializer = NotificationPreferenceSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        preferences = update_notification_preferences(
            user=request.user,
            **serializer.validated_data,
        )

        return Response(
            NotificationPreferenceSerializer(preferences).data,
            status=status.HTTP_200_OK,
        )
