from django.contrib.auth import get_user_model
from django.db import models
from django.http import HttpRequest, HttpResponseBadRequest
from django.utils.translation import gettext_lazy as _
from django.views import View
from requests.exceptions import RequestException
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import BaseSerializer
from structlog.stdlib import get_logger

from authentik.core.types import UserSettingSerializer
from authentik.events.models import Event, EventAction, NotificationWebhookMapping
from authentik.events.utils import sanitize_item
from authentik.flows.models import ConfigurableStage, FriendlyNamedStage, Stage
from authentik.lib.models import SerializerModel
from authentik.lib.utils.http import get_http_session
from authentik.stages.authenticator.models import SideChannelDevice, ThrottlingMixin

LOGGER = get_logger()

TELEGRAM_API_BASE = "https://api.telegram.org"


class AuthenticatorTelegramStage(ConfigurableStage, FriendlyNamedStage, Stage):
    """Use Telegram-based TOTP instead of authenticator-based."""

    bot_username = models.TextField(help_text=_("Telegram bot username"))
    bot_token = models.TextField(help_text=_("Telegram bot token"))

    mapping = models.ForeignKey(
        NotificationWebhookMapping,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        help_text=_("Optionally modify the payload being sent to Telegram."),
    )

    def get_message(self, token: str) -> str:
        """Get Telegram message"""
        return _(
            "Use this code to authenticate in authentik: `{token}`".format_map({"token": token})
        )

    def send(self, request: HttpRequest, token: str, device: TelegramDevice):
        """Send message via Telegram bot API"""

        message_text = str(self.get_message(token))
        payload = {
            "chat_id": device.chat_id,
            "text": message_text,
        }

        if self.mapping:
            payload = sanitize_item(
                self.mapping.evaluate(
                    user=device.user,
                    request=request,
                    device=device,
                    token=token,
                    stage=self,
                ),
            )

        response = get_http_session().post(
            f"{TELEGRAM_API_BASE}/bot{self.bot_token}/sendMessage",
            json=payload,
        )

        LOGGER.debug("Sent Telegram message", to=device.chat_id)
        try:
            response.raise_for_status()
        except RequestException as exc:
            LOGGER.warning(
                "Error sending token by Telegram",
                exc=exc,
                status=response.status_code,
                body=response.text[:100],
            )
            Event.new(
                EventAction.CONFIGURATION_ERROR,
                message="Error sending Telegram message",
                status_code=response.status_code,
                body=response.text,
            ).with_exception(exc).set_user(device.user).save()
            if response.status_code >= HttpResponseBadRequest.status_code:
                raise ValidationError(response.text) from None
            raise

    @property
    def serializer(self) -> type[BaseSerializer]:
        from authentik.stages.authenticator_telegram.api import AuthenticatorTelegramStageSerializer

        return AuthenticatorTelegramStageSerializer

    @property
    def view(self) -> type[View]:
        from authentik.stages.authenticator_telegram.stage import AuthenticatorTelegramStageView

        return AuthenticatorTelegramStageView

    @property
    def component(self) -> str:
        return "ak-stage-authenticator-telegram-form"

    def ui_user_settings(self) -> UserSettingSerializer | None:
        return UserSettingSerializer(
            data={
                "title": self.friendly_name or str(self._meta.verbose_name),
                "component": "ak-user-settings-authenticator-telegram",
            },
        )

    def __str__(self) -> str:
        return f"Telegram Authenticator Setup Stage {self.name}"

    class Meta:
        verbose_name = _("Telegram Authenticator Setup Stage")
        verbose_name_plural = _("Telegram Authenticator Setup Stages")


class TelegramDevice(SerializerModel, ThrottlingMixin, SideChannelDevice):
    """Telegram Device"""

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    stage = models.ForeignKey(AuthenticatorTelegramStage, on_delete=models.PROTECT)

    chat_id = models.TextField()
    telegram_username = models.TextField(blank=True, default="")
    last_t = models.DateTimeField(auto_now=True)

    @property
    def serializer(self) -> type[BaseSerializer]:
        from authentik.stages.authenticator_telegram.api import TelegramDeviceSerializer

        return TelegramDeviceSerializer

    def verify_token(self, token):
        verify_allowed, _ = self.verify_is_allowed()
        if verify_allowed:
            verified = super().verify_token(token)
            if verified:
                self.throttle_reset()
            else:
                self.throttle_increment()
        else:
            verified = False

        return verified

    def __str__(self) -> str:
        return str(self.name) or str(self.user_id)

    class Meta:
        verbose_name = _("Telegram Device")
        verbose_name_plural = _("Telegram Devices")
        unique_together = ("stage", "chat_id")
