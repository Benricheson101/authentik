"""API URLs"""

from authentik.stages.authenticator_telegram.api import (
    AuthenticatorTelegramStageViewSet,
    TelegramAdminDeviceViewSet,
    TelegramDeviceViewSet,
)

api_urlpatterns = [
    ("authenticators/telegram", TelegramDeviceViewSet),
    ("authenticators/admin/telegram", TelegramAdminDeviceViewSet, "admin-telegramdevice"),
    ("stages/authenticator/telegram", AuthenticatorTelegramStageViewSet),
]
