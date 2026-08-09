"""Telegram"""

from authentik.blueprints.apps import ManagedAppConfig


class AuthentikStageAuthenticatorTelegramConfig(ManagedAppConfig):
    """Telegram App config"""

    name = "authentik.stages.authenticator_telegram"
    label = "authentik_stages_authenticator_telegram"
    verbose_name = "authentik Stages.Authenticator.Telegram"
    default = True
