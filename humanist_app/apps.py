from django.apps import AppConfig


class HumanistAppConfig(AppConfig):
    name = 'humanist_app'

    def ready(self):
        import humanist_app.signals.handlers  # noqa