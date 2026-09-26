from django.test import TestCase

from audit.models import AuditLog
from audit.services import (
    create_audit_log,
    get_object_audit_logs,
    get_user_audit_logs,
)
from users.models import User


class AuditServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="testpassword123",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpassword123",
        )

    # ---------------------------------------------------------
    # Create audit log
    # ---------------------------------------------------------

    def test_create_audit_log(self):
        audit_log = create_audit_log(
            action="ORDER_CREATED",
            user=self.user,
            model_name="Order",
            object_id=123,
            details={
                "status": "PENDING",
                "total": "250.00",
            },
            ip_address="192.168.1.10",
        )

        self.assertEqual(audit_log.user, self.user)
        self.assertEqual(
            audit_log.action,
            "ORDER_CREATED",
        )
        self.assertEqual(
            audit_log.model_name,
            "Order",
        )
        self.assertEqual(
            audit_log.object_id,
            "123",
        )
        self.assertEqual(
            audit_log.details,
            {
                "status": "PENDING",
                "total": "250.00",
            },
        )
        self.assertEqual(
            audit_log.ip_address,
            "192.168.1.10",
        )

    def test_create_audit_log_without_optional_fields(self):
        audit_log = create_audit_log(
            action="SYSTEM_EVENT",
        )

        self.assertIsNone(audit_log.user)
        self.assertEqual(audit_log.model_name, "")
        self.assertEqual(audit_log.object_id, "")
        self.assertEqual(audit_log.details, {})
        self.assertIsNone(audit_log.ip_address)

    def test_create_audit_log_allows_anonymous_user(self):
        audit_log = create_audit_log(
            action="PUBLIC_EVENT",
            user=None,
        )

        self.assertIsNone(audit_log.user)

    def test_create_audit_log_converts_object_id_to_string(self):
        audit_log = create_audit_log(
            action="PRODUCT_UPDATED",
            model_name="Product",
            object_id=456,
        )

        self.assertEqual(
            audit_log.object_id,
            "456",
        )
        self.assertIsInstance(
            audit_log.object_id,
            str,
        )

    def test_create_audit_log_defaults_details_to_empty_dict(self):
        audit_log = create_audit_log(
            action="TEST_ACTION",
            details=None,
        )

        self.assertEqual(
            audit_log.details,
            {},
        )

    # ---------------------------------------------------------
    # User audit logs
    # ---------------------------------------------------------

    def test_get_user_audit_logs(self):
        user_log = AuditLog.objects.create(
            user=self.user,
            action="USER_ACTION",
        )

        AuditLog.objects.create(
            user=self.other_user,
            action="OTHER_USER_ACTION",
        )

        logs = get_user_audit_logs(
            user=self.user
        )

        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first(), user_log)

    def test_get_user_audit_logs_returns_newest_first(self):
        first = AuditLog.objects.create(
            user=self.user,
            action="FIRST",
        )

        second = AuditLog.objects.create(
            user=self.user,
            action="SECOND",
        )

        logs = list(
            get_user_audit_logs(
                user=self.user
            )
        )

        self.assertEqual(logs[0], second)
        self.assertEqual(logs[1], first)

    def test_get_user_audit_logs_does_not_include_anonymous_logs(self):
        AuditLog.objects.create(
            user=None,
            action="ANONYMOUS_ACTION",
        )

        user_log = AuditLog.objects.create(
            user=self.user,
            action="USER_ACTION",
        )

        logs = get_user_audit_logs(
            user=self.user
        )

        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first(), user_log)

    # ---------------------------------------------------------
    # Object audit logs
    # ---------------------------------------------------------

    def test_get_object_audit_logs(self):
        first_log = AuditLog.objects.create(
            user=self.user,
            action="ORDER_CREATED",
            model_name="Order",
            object_id="123",
        )

        AuditLog.objects.create(
            user=self.user,
            action="ORDER_CREATED",
            model_name="Order",
            object_id="456",
        )

        logs = get_object_audit_logs(
            model_name="Order",
            object_id=123,
        )

        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first(), first_log)

    def test_get_object_audit_logs_filters_by_model_and_object(self):
        matching_log = AuditLog.objects.create(
            user=self.user,
            action="PRODUCT_UPDATED",
            model_name="Product",
            object_id="10",
        )

        AuditLog.objects.create(
            user=self.user,
            action="ORDER_UPDATED",
            model_name="Order",
            object_id="10",
        )

        AuditLog.objects.create(
            user=self.user,
            action="PRODUCT_UPDATED",
            model_name="Product",
            object_id="20",
        )

        logs = get_object_audit_logs(
            model_name="Product",
            object_id=10,
        )

        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first(), matching_log)

    def test_get_object_audit_logs_returns_newest_first(self):
        first = AuditLog.objects.create(
            user=self.user,
            action="FIRST",
            model_name="Order",
            object_id="100",
        )

        second = AuditLog.objects.create(
            user=self.user,
            action="SECOND",
            model_name="Order",
            object_id="100",
        )

        logs = list(
            get_object_audit_logs(
                model_name="Order",
                object_id=100,
            )
        )

        self.assertEqual(logs[0], second)
        self.assertEqual(logs[1], first)

    def test_get_object_audit_logs_can_return_logs_from_different_users(self):
        first = AuditLog.objects.create(
            user=self.user,
            action="ORDER_CREATED",
            model_name="Order",
            object_id="500",
        )

        second = AuditLog.objects.create(
            user=self.other_user,
            action="ORDER_UPDATED",
            model_name="Order",
            object_id="500",
        )

        logs = list(
            get_object_audit_logs(
                model_name="Order",
                object_id=500,
            )
        )

        self.assertEqual(len(logs), 2)
        self.assertIn(first, logs)
        self.assertIn(second, logs)


from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class AuditAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="testpassword123",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpassword123",
        )

        self.list_url = reverse("audit-list")

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def create_log(
        self,
        user=None,
        action="TEST_ACTION",
        model_name="Order",
        object_id="123",
        details=None,
        ip_address=None,
    ):
        return AuditLog.objects.create(
            user=user or self.user,
            action=action,
            model_name=model_name,
            object_id=object_id,
            details=details or {},
            ip_address=ip_address,
        )

    # ---------------------------------------------------------
    # User audit logs
    # ---------------------------------------------------------

    def test_unauthenticated_user_cannot_list_audit_logs(self):
        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_user_can_list_audit_logs(self):
        self.authenticate()

        log = self.create_log()

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            log.id,
        )

    def test_user_only_sees_their_own_audit_logs(self):
        self.authenticate()

        own_log = self.create_log()

        self.create_log(
            user=self.other_user,
            action="OTHER_USER_ACTION",
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            own_log.id,
        )

    def test_audit_logs_are_newest_first(self):
        self.authenticate()

        first = self.create_log(
            action="FIRST_ACTION",
        )

        second = self.create_log(
            action="SECOND_ACTION",
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data[0]["id"],
            second.id,
        )

        self.assertEqual(
            response.data[1]["id"],
            first.id,
        )

    def test_audit_log_contains_expected_fields(self):
        self.authenticate()

        self.create_log(
            action="ORDER_CREATED",
            model_name="Order",
            object_id="123",
            details={
                "status": "PENDING",
                "total": "250.00",
            },
            ip_address="192.168.1.10",
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        log = response.data[0]

        self.assertIn("id", log)
        self.assertIn("action", log)
        self.assertIn("model_name", log)
        self.assertIn("object_id", log)
        self.assertIn("details", log)
        self.assertIn("ip_address", log)
        self.assertIn("created_at", log)

        self.assertEqual(
            log["action"],
            "ORDER_CREATED",
        )

        self.assertEqual(
            log["model_name"],
            "Order",
        )

        self.assertEqual(
            log["object_id"],
            "123",
        )

        self.assertEqual(
            log["details"],
            {
                "status": "PENDING",
                "total": "250.00",
            },
        )

        self.assertEqual(
            log["ip_address"],
            "192.168.1.10",
        )

    def test_audit_logs_are_read_only(self):
        self.authenticate()

        response = self.client.post(
            self.list_url,
            {
                "action": "FAKE_ACTION",
                "model_name": "Order",
                "object_id": "999",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.assertFalse(
            AuditLog.objects.filter(
                action="FAKE_ACTION"
            ).exists()
        )

    # ---------------------------------------------------------
    # Object audit logs
    # ---------------------------------------------------------

    def test_unauthenticated_user_cannot_list_object_audit_logs(self):
        url = reverse(
            "audit-object-list",
            kwargs={
                "model_name": "Order",
                "object_id": "123",
            },
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_user_can_list_object_audit_logs(self):
        self.authenticate()

        first = self.create_log(
            action="ORDER_CREATED",
            model_name="Order",
            object_id="123",
        )

        second = self.create_log(
            action="ORDER_CONFIRMED",
            model_name="Order",
            object_id="123",
        )

        response = self.client.get(
            reverse(
                "audit-object-list",
                kwargs={
                    "model_name": "Order",
                    "object_id": "123",
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 2)

        self.assertEqual(
            response.data[0]["id"],
            second.id,
        )

        self.assertEqual(
            response.data[1]["id"],
            first.id,
        )

    def test_object_logs_are_filtered_by_model_name(self):
        self.authenticate()

        matching_log = self.create_log(
            action="ORDER_CREATED",
            model_name="Order",
            object_id="123",
        )

        self.create_log(
            action="PRODUCT_UPDATED",
            model_name="Product",
            object_id="123",
        )

        response = self.client.get(
            reverse(
                "audit-object-list",
                kwargs={
                    "model_name": "Order",
                    "object_id": "123",
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            matching_log.id,
        )

    def test_object_logs_are_filtered_by_object_id(self):
        self.authenticate()

        matching_log = self.create_log(
            action="ORDER_CREATED",
            model_name="Order",
            object_id="123",
        )

        self.create_log(
            action="ORDER_CREATED",
            model_name="Order",
            object_id="456",
        )

        response = self.client.get(
            reverse(
                "audit-object-list",
                kwargs={
                    "model_name": "Order",
                    "object_id": "123",
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            matching_log.id,
        )

    def test_object_logs_can_contain_logs_from_multiple_users(self):
        self.authenticate()

        first = self.create_log(
            user=self.user,
            action="ORDER_CREATED",
            model_name="Order",
            object_id="500",
        )

        second = self.create_log(
            user=self.other_user,
            action="ORDER_UPDATED",
            model_name="Order",
            object_id="500",
        )

        response = self.client.get(
            reverse(
                "audit-object-list",
                kwargs={
                    "model_name": "Order",
                    "object_id": "500",
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 2)

        returned_ids = {
            log["id"]
            for log in response.data
        }

        self.assertEqual(
            returned_ids,
            {first.id, second.id},
        )

    def test_object_with_no_audit_logs_returns_empty_list(self):
        self.authenticate()

        response = self.client.get(
            reverse(
                "audit-object-list",
                kwargs={
                    "model_name": "Order",
                    "object_id": "999999",
                },
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            [],
        )

    def test_audit_logs_are_read_only_for_object_endpoint(self):
        self.authenticate()

        url = reverse(
            "audit-object-list",
            kwargs={
                "model_name": "Order",
                "object_id": "123",
            },
        )

        response = self.client.post(
            url,
            {
                "action": "FAKE_ACTION",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        self.assertFalse(
            AuditLog.objects.filter(
                action="FAKE_ACTION"
            ).exists()
        )
