from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Warning, register, Tags

from .main import _register_models


def check_my_custom_setting(**kwargs):
    errors = []
    if not hasattr(settings, 'FAST_MODELADMIN'):
        errors.append(
            Warning(
                'FAST_MODELADMIN setting is missing.',
                hint='Add "FAST_MODELADMIN = ()" to settings.py',
                obj='fast_modeladmin'
            )
        )
    return errors


class CustomAdminAppConfig(AppConfig):
    name = 'fast_modeladmin'

    def ready(self):
        register(check_my_custom_setting, Tags.compatibility)
        _register_models(admin_model=getattr(settings, 'FAST_MODELADMIN', None),
                                         register_all=getattr(settings, 'FAST_MODELADMIN_REGISTER_ALL', None),
                                         files=getattr(settings, 'FAST_MODELADMIN_MODULES', {}))
