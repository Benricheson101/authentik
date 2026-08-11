from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from authentik.core.api.groups import PartialUserSerializer
from authentik.core.api.used_by import UsedByMixin
from authentik.core.api.utils import ModelSerializer
from authentik.flows.api.stages import StageSerializer
from authentik.stages.authenticator_telegram.models import (
    AuthenticatorTelegramStage,
    TelegramDevice,
)


class AuthenticatorTelegramStageSerializer(StageSerializer):
    """AuthenticatorTelegramStage Serializer"""

    class Meta:
        model = AuthenticatorTelegramStage
        fields = StageSerializer.Meta.fields + [
            "configure_flow",
            "friendly_name",
            "bot_username",
            "bot_token",
            "mapping",
        ]

        extra_kwargs = {
            "bot_token": {"write_only": True},
        }


class TelegramDeviceSerializer(ModelSerializer):
    """Serializer for Telegram authenticator devices"""

    user = PartialUserSerializer(read_only=True)

    class Meta:
        model = TelegramDevice
        fields = ["name", "pk", "user", "chat_id"]
        depth = 2
        extra_kwargs = {
            "chat_id": {"read_only": True},
        }


class AuthenticatorTelegramStageViewSet(UsedByMixin, ModelViewSet):
    """AuthenticatorTelegramStage Viewset"""

    queryset = AuthenticatorTelegramStage.objects.all()
    serializer_class = AuthenticatorTelegramStageSerializer
    filterset_fields = "__all__"
    ordering = ["name"]
    search_fields = ["name"]


class TelegramDeviceViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    UsedByMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    """Viewset for Telegram authenticator devices"""

    queryset = TelegramDevice.objects.all()
    serializer_class = TelegramDeviceSerializer
    search_fields = ["name"]
    filterset_fields = ["name"]
    ordering = ["name"]
    owner_field = "user"


class TelegramAdminDeviceViewSet(ModelViewSet):
    """Viewset for Telegram authenticator devices (for admins)"""

    queryset = TelegramDevice.objects.all()
    serializer_class = TelegramDeviceSerializer
    search_fields = ["name"]
    filterset_fields = ["name"]
    ordering = ["name"]
