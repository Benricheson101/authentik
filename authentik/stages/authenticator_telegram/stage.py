"""Telegram Setup stage"""

from django.http import HttpRequest, HttpResponse
from django.http.request import QueryDict
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.fields import BooleanField, CharField

from authentik.flows.challenge import Challenge, ChallengeResponse, WithUserInfoChallenge
from authentik.flows.stage import ChallengeStageView
from authentik.sources.telegram.api.source import TelegramAuthSerializer
from authentik.stages.authenticator_telegram.models import (
    AuthenticatorTelegramStage,
    TelegramDevice,
)

PLAN_CONTEXT_TELEGRAM_DEVICE = "goauthentik.io/stages/authenticator_telegram/telegram_device"


class AuthenticatorTelegramChallenge(WithUserInfoChallenge):
    """Telegram Setup challenge"""

    code_required = BooleanField(default=False)
    bot_username = CharField()
    component = CharField(default="ak-stage-authenticator-telegram")


class AuthenticatorTelegramChallengeResponse(ChallengeResponse):
    """Telegram Challenge response, device is set by get_response_instance"""

    device: TelegramDevice
    code = CharField(required=False)
    component = CharField(default="ak-stage-authenticator-telegram")

    def validate(self, attrs: dict) -> dict:
        if "code" not in attrs:
            widget_auth = TelegramAuthSerializer(
                bot_token=self.stage.executor.current_stage.bot_token, data=self.initial_data
            )

            widget_auth.is_valid(raise_exception=True)
            validated = widget_auth.validated_data

            chat_id = str(validated["id"])
            self.device.chat_id = chat_id
            self.stage.validate_and_send(chat_id)
            self.device.telegram_username = validated.get("username", "")
            return attrs
        if not self.device.verify_token(str(attrs["code"])):
            raise ValidationError(_("Code does not match"))
        self.device.confirmed = True
        return attrs


class AuthenticatorTelegramStageView(ChallengeStageView):
    """Telegram Setup stage"""

    response_class = AuthenticatorTelegramChallengeResponse

    def validate_and_send(self, chat_id: str):
        """Validate chat_id and send the code"""

        stage: AuthenticatorTelegramStage = self.executor.current_stage
        if TelegramDevice.objects.filter(chat_id=chat_id, stage=stage.pk).exists():
            raise ValidationError(_("This Telegram account is already in use"))
        device: TelegramDevice = self.executor.plan.context[PLAN_CONTEXT_TELEGRAM_DEVICE]
        stage.send(self.request, device.token, device)

    def get_challenge(self, *args, **kwargs) -> Challenge:
        device: TelegramDevice = self.executor.plan.context[PLAN_CONTEXT_TELEGRAM_DEVICE]
        stage: AuthenticatorTelegramStage = self.executor.current_stage
        return AuthenticatorTelegramChallenge(
            data={
                "code_required": device.chat_id != "",
                "bot_username": stage.bot_username,
            }
        )

    def get_response_instance(self, data: QueryDict) -> ChallengeResponse:
        response = super().get_response_instance(data)
        response.device = self.executor.plan.context[PLAN_CONTEXT_TELEGRAM_DEVICE]
        return response

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        user = self.get_pending_user()

        stage: AuthenticatorTelegramStage = self.executor.current_stage

        if PLAN_CONTEXT_TELEGRAM_DEVICE not in self.executor.plan.context:
            device = TelegramDevice(
                user=user,
                confirmed=False,
                stage=stage,
                name="Telegram Device",
                chat_id="",
            )
            device.generate_token(commit=False)
            self.executor.plan.context[PLAN_CONTEXT_TELEGRAM_DEVICE] = device
        return super().get(request, *args, **kwargs)

    def challenge_valid(self, response: ChallengeResponse) -> HttpResponse:
        """Telegram code is validated by challenge"""

        device: TelegramDevice = self.executor.plan.context[PLAN_CONTEXT_TELEGRAM_DEVICE]
        if not device.confirmed:
            return self.challenge_invalid(response)
        device.save()
        del self.executor.plan.context[PLAN_CONTEXT_TELEGRAM_DEVICE]
        return self.executor.stage_ok()
