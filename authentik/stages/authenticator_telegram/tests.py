"""Test Telegram API"""

import hashlib
import hmac
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse
from requests_mock import Mocker
from rest_framework.test import APITestCase

from authentik.core.tests.utils import create_test_admin_user, create_test_flow, create_test_user
from authentik.flows.models import FlowStageBinding
from authentik.flows.tests import FlowTestCase
from authentik.lib.generators import generate_id
from authentik.stages.authenticator.tests import ThrottlingTestMixin
from authentik.stages.authenticator_telegram.models import (
    AuthenticatorTelegramStage,
    TelegramDevice,
)
from authentik.stages.authenticator_telegram.stage import PLAN_CONTEXT_TELEGRAM_DEVICE


class MockTelegramResponseMixin:
    def _add_hash(self, response):
        to_hash = "\n".join([f"{key}={value}" for key, value in sorted(response.items())])
        response["hash"] = hmac.new(
            hashlib.sha256(self.stage.bot_token.encode("utf-8")).digest(),
            to_hash.encode("utf-8"),
            "sha256",
        ).hexdigest()

    def _make_valid_response(self, id_="123456789"):
        resp = {
            "id": id_,
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser",
            "auth_date": str(int(datetime.now().timestamp())),
        }
        self._add_hash(resp)
        return resp


class AuthenticatorTelegramStageTests(MockTelegramResponseMixin, FlowTestCase):
    """Test Telegram API"""

    def setUp(self) -> None:
        super().setUp()
        self.flow = create_test_flow()
        self.stage: AuthenticatorTelegramStage = AuthenticatorTelegramStage.objects.create(
            name="foo",
            bot_username="test_bot",
            bot_token=generate_id(),
            configure_flow=self.flow,
        )
        FlowStageBinding.objects.create(target=self.flow, stage=self.stage, order=0)
        self.user = create_test_admin_user()
        self.client.force_login(self.user)

    def test_stage_no_prefill(self):
        """test stage"""
        self.client.get(
            reverse("authentik_flows:configure", kwargs={"stage_uuid": self.stage.stage_uuid}),
        )
        response = self.client.get(
            reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
        )
        self.assertStageResponse(
            response,
            self.flow,
            self.user,
            component="ak-stage-authenticator-telegram",
            code_required=False,
            bot_username=self.stage.bot_username,
        )

    def test_stage_deletion_is_protected(self):
        """A setup stage with enrolled devices cannot be deleted."""
        device = TelegramDevice.objects.create(user=self.user, stage=self.stage, chat_id="1234")

        with self.assertRaises(ProtectedError):
            self.stage.delete()

        self.assertTrue(AuthenticatorTelegramStage.objects.filter(pk=self.stage.pk).exists())
        self.assertTrue(TelegramDevice.objects.filter(pk=device.pk).exists())

    def test_stage_submit(self):
        """test stage (submit)"""
        self.client.get(
            reverse("authentik_flows:configure", kwargs={"stage_uuid": self.stage.stage_uuid}),
        )
        response = self.client.get(
            reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
        )
        self.assertStageResponse(
            response,
            self.flow,
            self.user,
            component="ak-stage-authenticator-telegram",
            code_required=False,
        )
        telegram_send_mock = MagicMock()
        with patch(
            "authentik.stages.authenticator_telegram.models.AuthenticatorTelegramStage.send",
            telegram_send_mock,
        ):
            response = self.client.post(
                reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
                data={
                    "component": "ak-stage-authenticator-telegram",
                    **self._make_valid_response(),
                },
            )
            self.assertEqual(response.status_code, 200)
            telegram_send_mock.assert_called_once()
        self.assertStageResponse(
            response,
            self.flow,
            self.user,
            component="ak-stage-authenticator-telegram",
            response_errors={},
            code_required=True,
        )

    def test_stage_submit_sends_telegram_message(self):
        """test stage (submit) (sends real Telegram API request)"""
        self.client.get(
            reverse("authentik_flows:configure", kwargs={"stage_uuid": self.stage.stage_uuid}),
        )
        response = self.client.get(
            reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
        )
        self.assertStageResponse(
            response,
            self.flow,
            self.user,
            component="ak-stage-authenticator-telegram",
            code_required=False,
        )

        with Mocker() as mocker:
            mocker.post(
                f"https://api.telegram.org/bot{self.stage.bot_token}/sendMessage",
                json={},
            )
            response = self.client.post(
                reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
                data={
                    "component": "ak-stage-authenticator-telegram",
                    **self._make_valid_response(),
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(mocker.call_count, 1)
            self.assertEqual(mocker.request_history[0].method, "POST")
            device: TelegramDevice = self.get_flow_plan().context[PLAN_CONTEXT_TELEGRAM_DEVICE]
            self.assertEqual(
                mocker.request_history[0].json(),
                {
                    "chat_id": device.chat_id,
                    "text": f"Use this code to authenticate in authentik: `{device.token}`",
                },
            )
        self.assertStageResponse(
            response,
            self.flow,
            self.user,
            component="ak-stage-authenticator-telegram",
            response_errors={},
            code_required=True,
        )

    def test_stage_submit_full(self):
        """test stage (submit)"""
        self.client.get(
            reverse("authentik_flows:configure", kwargs={"stage_uuid": self.stage.stage_uuid}),
        )
        response = self.client.get(
            reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
        )
        self.assertStageResponse(
            response,
            self.flow,
            self.user,
            component="ak-stage-authenticator-telegram",
            code_required=False,
        )
        telegram_send_mock = MagicMock()
        with patch(
            "authentik.stages.authenticator_telegram.models.AuthenticatorTelegramStage.send",
            telegram_send_mock,
        ):
            response = self.client.post(
                reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
                data={
                    "component": "ak-stage-authenticator-telegram",
                    **self._make_valid_response(),
                },
            )
            self.assertEqual(response.status_code, 200)
            telegram_send_mock.assert_called_once()
        self.assertStageResponse(
            response,
            self.flow,
            self.user,
            component="ak-stage-authenticator-telegram",
            response_errors={},
            code_required=True,
        )
        with patch(
            "authentik.stages.authenticator_telegram.models.TelegramDevice.verify_token",
            MagicMock(return_value=True),
        ):
            response = self.client.post(
                reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
                data={"component": "ak-stage-authenticator-telegram", "code": "123456"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertStageRedirects(response, reverse("authentik_core:root-redirect"))
        device: TelegramDevice = TelegramDevice.objects.filter(user=self.user).first()
        self.assertEqual(device.telegram_username, "testuser")

    def test_stage_duplicate_chat_id(self):
        """test stage (chat_id already in use)"""
        TelegramDevice.objects.create(
            user=create_test_admin_user(),
            stage=self.stage,
            chat_id="123456789",
        )
        self.client.get(
            reverse("authentik_flows:configure", kwargs={"stage_uuid": self.stage.stage_uuid}),
        )
        response = self.client.get(
            reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
        )
        self.assertStageResponse(
            response,
            self.flow,
            self.user,
            component="ak-stage-authenticator-telegram",
            code_required=False,
        )
        response = self.client.post(
            reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
            data={"component": "ak-stage-authenticator-telegram", **self._make_valid_response()},
        )
        self.assertStageResponse(
            response,
            self.flow,
            self.user,
            component="ak-stage-authenticator-telegram",
            response_errors={
                "non_field_errors": [
                    {"code": "invalid", "string": "This Telegram account is already in use"}
                ]
            },
            code_required=True,
        )

    def test_stage_invalid_hash(self):
        """test stage (invalid hash)"""
        self.client.get(
            reverse("authentik_flows:configure", kwargs={"stage_uuid": self.stage.stage_uuid}),
        )
        response = self.client.get(
            reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
        )
        self.assertStageResponse(
            response,
            self.flow,
            self.user,
            component="ak-stage-authenticator-telegram",
            code_required=False,
        )
        resp = self._make_valid_response()
        resp["hash"] = "invalid_hash"
        response = self.client.post(
            reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
            data={"component": "ak-stage-authenticator-telegram", **resp},
        )
        self.assertStageResponse(
            response,
            self.flow,
            self.user,
            component="ak-stage-authenticator-telegram",
            response_errors={"non_field_errors": [{"code": "invalid", "string": "Invalid hash"}]},
            code_required=False,
        )

    def test_stage_wrong_code(self):
        """test stage (wrong code)"""
        self.client.get(
            reverse("authentik_flows:configure", kwargs={"stage_uuid": self.stage.stage_uuid}),
        )
        response = self.client.get(
            reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
        )
        self.assertStageResponse(
            response,
            self.flow,
            self.user,
            component="ak-stage-authenticator-telegram",
            code_required=False,
        )
        telegram_send_mock = MagicMock()
        with patch(
            "authentik.stages.authenticator_telegram.models.AuthenticatorTelegramStage.send",
            telegram_send_mock,
        ):
            response = self.client.post(
                reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
                data={
                    "component": "ak-stage-authenticator-telegram",
                    **self._make_valid_response(),
                },
            )
            self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("authentik_api:flow-executor", kwargs={"flow_slug": self.flow.slug}),
            data={"component": "ak-stage-authenticator-telegram", "code": "000000"},
        )
        self.assertStageResponse(
            response,
            self.flow,
            self.user,
            component="ak-stage-authenticator-telegram",
            response_errors={
                "non_field_errors": [{"code": "invalid", "string": "Code does not match"}]
            },
            code_required=True,
        )


class TestTelegramDeviceThrottling(ThrottlingTestMixin, TestCase):
    """Test ThrottlingMixin behavior on TelegramDevice.verify_token"""

    def setUp(self):
        super().setUp()
        user = create_test_admin_user()
        stage = AuthenticatorTelegramStage.objects.create(
            name="telegram-throttle",
            bot_username="test_bot",
            bot_token=generate_id(),
        )
        self.device = TelegramDevice.objects.create(
            user=user,
            stage=stage,
            chat_id="123456789",
        )
        self.device.generate_token()

    def valid_token(self):
        return self.device.token

    def invalid_token(self):
        return "000000" if self.device.token != "000000" else "111111"


class TestTelegramDeviceAPI(APITestCase):
    """Test Telegram device API"""

    def setUp(self) -> None:
        super().setUp()
        self.stage = AuthenticatorTelegramStage.objects.create(
            name="foo",
            bot_username="test_bot",
            bot_token=generate_id(),
        )
        self.user = create_test_user()
        self.client.force_login(self.user)

    def test_list(self):
        """Test Telegram device list"""
        device = TelegramDevice.objects.create(
            user=self.user,
            stage=self.stage,
            chat_id="123",
        )
        TelegramDevice.objects.create(
            user=create_test_user(),
            stage=self.stage,
            chat_id="456",
        )
        response = self.client.get(reverse("authentik_api:telegramdevice-list"))
        body = json.loads(response.content)
        self.assertEqual(len(body["results"]), 1)
        self.assertEqual(body["results"][0]["pk"], device.pk)

    def test_update_chat_id_read_only(self):
        """Test that chat_id cannot be changed"""
        device = TelegramDevice.objects.create(
            user=self.user,
            stage=self.stage,
            chat_id="123",
        )
        response = self.client.patch(
            reverse("authentik_api:telegramdevice-detail", kwargs={"pk": device.pk}),
            data={"name": "renamed", "chat_id": "000"},
        )
        self.assertEqual(response.status_code, 200)
        device.refresh_from_db()
        self.assertEqual(device.name, "renamed")
        self.assertEqual(device.chat_id, "123")

    def test_create_not_allowed(self):
        """
        Test that devices cannot be created by API.
        Users can only create devices by going through Telegram flow.
        """
        self.user.assign_perms_to_managed_role(
            "authentik_stages_authenticator_telegram.add_telegramdevice"
        )
        response = self.client.post(
            reverse("authentik_api:telegramdevice-list"),
            data={"name": "new", "chat_id": "789"},
        )
        self.assertEqual(response.status_code, 405)
