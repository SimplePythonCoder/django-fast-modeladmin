from typing import cast

from django.apps import apps
from django.contrib import admin
import re
from importlib import import_module
from django.contrib.admin import ShowFacets
from django.db import models

from .exceptions import (ModelFieldError, OptionError, ModelNotFound, ValueTypeError,
                         CustomSyntaxError, ModuleError, ClassError,
                         _raise)

from .form import template_model_form


def _get_import(model, field_list: list, index=0):
    if index < len(field_list):
        if getattr(model, field_list[index], None) is not None:
            match getattr(model, field_list[index]).__class__.__name__:
                case 'ForwardManyToOneDescriptor' | 'ForwardOneToOneDescriptor':
                    return _get_import(getattr(model, field_list[index]).field.remote_field.model, field_list,
                                            index + 1)
                case 'DeferredAttribute':
                    if getattr(getattr(model, field_list[index]), 'field', None) is not None:
                        return _get_import(getattr(getattr(model, field_list[index]), 'field'), field_list,
                                                index + 1)
                    else:
                        _raise(model=model.__name__, error_type=ModelFieldError, field=field_list[index])
        else:
            _raise(model=model.__name__, error_type=ModelFieldError, message=f'field "{field_list[index]}" in {"__".join(field_list)} '
                                                       f'cannot be found')
    return model


def get_dict(model=None, columns=None, parts=None,
             actions=None, form=None, read_only_fields=None,
             sort=None, search=None, editables=None, links=None,
             filters=None):
    """
    This function builds a dictionary to be used in the FAST_MODELADMIN setting

    :param model:                   app and model name (app_name.ModelName)
    :type model:                    str
    :param columns:                 list of fields to be columns of list page
    :type columns:                  list[str]
    :param parts:                   parts and fields to render on entry page
    :type parts:                    dict [(str, str), (str, list)]
    :param actions:                 list of function names in the admin module
    :type actions:                  list[str]
    :param form:                    list of class names in the forms module
    :type form:                     str
    :param read_only_fields:        list of fields to be non-editables in the form page
    :type read_only_fields:         list[str]
    :param sort:                    name of field to sort by
    :type sort:                     list[str]
    :param search:                  list of fields and sub-fields to search in
    :type search:                   list[str]
    :param editables:               list of column fields to be editable on the list page
    :type editables:                list[str]
    :param links:                   list of column fields to be clickable on the list page
    :type links:                    list[str]
    :param filters:                 dict with list of fields in 'fields' and 'show_count' that is either 'show',
                                    'hide' or 'disable'.
    :type filters:                  dict[str, list] | dict[str, str]
    :return:                        dict to be used in settings for CUSTOM_MODELADMIN variable
    :rtype:                         dict
    """
    return {'model': model,
            'columns': columns,
            'parts': parts,
            'actions': actions,
            'form': form,
            'read_only_fields': read_only_fields,
            'sort': sort,
            'search': search,
            'editables': editables,
            'links': links,
            'filters': filters}


def _part_creator(**kwargs):
    match kwargs.get('classes'):
        case None:
            return kwargs['label'], {'fields': kwargs['fields']}
        case list() | tuple():
            return kwargs['label'], {'fields': kwargs['fields'], 'classes': kwargs['classes']}

    return None

def _get_app(app_model):
    if type(app_model) is str:
        if not re.match(pattern=r'.+\..+', string=app_model):
            _raise(error_type=OptionError, message='model pattern must be app_label.ModelName')
        app_model = {'app_label': app_model.split('.')[0], 'model_name': app_model.split('.')[1]}
    try:
        return apps.get_model(**app_model)
    except LookupError:
        _raise(model=f'{app_model["app_label"]}.{app_model["model_name"]}', error_type=ModelNotFound)


def _is_type(model, value, types, kind):
    match types:
        case list():
            if type(value) not in types:
                _raise(model=model, error_type=ValueTypeError, kind=kind, value=value, types=types)
        case type():
            if type(value) is not types:
                _raise(model=model, error_type=ValueTypeError, kind=kind, value=value, types=types)


def _interpreter(values, files, model):
    model_fields = [field for field in model.__dict__.keys() if not field.startswith('_')]
    non_editable_fields = [field.name for field in getattr(model, '_meta').fields if not field.editable]

    if values.get('columns') is not None:
        _is_type(model, value=values['columns'], types=[list, tuple], kind='columns')
        for field in values['columns']:
            _is_type(model, value=field, types=str, kind='columns field')
            if field not in model_fields and field != 'pk':
                _raise(model=model, error_type=ModelFieldError, field=field)
    if values.get('read_only_fields') is not None:
        _is_type(model, value=values['read_only_fields'], types=[list, tuple], kind='read only fields')
        for field in values['read_only_fields']:
            _is_type(model, value=field, types=str, kind='read only field')
            if field not in model_fields and field != 'pk':
                _raise(model=model, error_type=ModelFieldError, field=field)
    if values.get('parts') is not None:
        _is_type(model, value=values.get('parts'), types=[list, tuple], kind='parts')
        field_list = []
        for index, part in enumerate(values['parts']):
            _is_type(model, value=part, types=dict, kind='parts')
            if part.get('label') is None:
                _raise(model=model, error_type=OptionError, message=f'missing label in parts[{index}]')
            _is_type(model, value=part.get('label'), types=str, kind='label')
            if part.get('fields') is None:
                _raise(model=model, error_type=OptionError, message=f'missing fields in parts[{index}]')
            _is_type(model, value=part.get('fields'), types=[list, tuple], kind='part fields')
            _is_type(model, value=part.get('classes'), types=[list, tuple, type(None)], kind='classes')
            for field in part['fields']:
                _is_type(model, value=field, types=str, kind='field')
                if field not in model_fields:
                    _raise(model=model, error_type=ModelFieldError, field=field)
                if field in non_editable_fields and field not in values.get('read_only_fields'):
                    _raise(model=model, error_type=OptionError,
                           message=f'cannot use non-editable field "{field}" in parts.'
                                   f'\nHINT: you can add it to the "read_only_fields" to avoid this error.')
                if field in field_list:
                    _raise(model=model, error_type=OptionError,
                           message=f'cannot use field "{field}" more than once in "parts"')
                field_list.append(field)
            values['parts'][index] = _part_creator(**part)
        del field_list
    if values.get('sort') is not None:
        _is_type(model, value=values['sort'], types=[list, tuple], kind='sort')
        for sort in values['sort']:
            _is_type(model, value=sort, types=str, kind='sort field')
            if not re.match(pattern=r'-?\w+', string=sort):
                _raise(model=model, error_type=CustomSyntaxError,
                          message=f'sort pattern must be "field_name" or "-field_name"')
            _get_import(model, sort[1:].split('__') if sort[0] == '-' else sort.split('__'))
    if values.get('actions') is not None:
        _is_type(model, value=values['actions'], types=[list, tuple], kind='actions')
        try:
            admin_module = import_module(values['model'].split('.')[0] + '.' +
                                         (files['ADMIN'].replace('.py', '') if files.get('ADMIN') else 'admin'))
        except ModuleNotFoundError:
            _raise(model=model, error_type=CustomSyntaxError,
                      message=f'could not find "{files.get("ADMIN")}" admin module')
            return None
        for index, action in enumerate(values['actions']):
            _is_type(model, value=action, types=str, kind='action')
            values['actions'][index] = getattr(admin_module, action, None)
            if not callable(values['actions'][index]):
                _raise(model=model, error_type=ModuleError,
                          message=f'action "{action}" was not found in {values["model"].split(".")[0]}.admin')
    if values.get('form') is not None:
        _is_type(model, value=values['form'], types=str, kind='form')
        try:
            values['form'] = getattr(import_module(values['model'].split('.')[0] + '.' +
                                                   (files['FORMS'].replace('.py', '')
                                                    if files.get('FORMS') else 'forms')),
                                     values['form'])
        except ModuleNotFoundError:
            _raise(model=model, error_type=CustomSyntaxError, message=f'could not find "{files.get("FORMS")}" forms module')
        except AttributeError:
            _raise(model=model, error_type=ModuleError,
                   message=f'form "{values["form"]}" not found in {values["model"].split(".")[0]}.forms')
        if not callable(values['form']):
            _is_type(model=model, value=values['form'], types=str, kind='form')
        if values['form'].__class__.__name__ != 'ModelFormMetaclass':
            _raise(model=model, error_type=ClassError,
                      message='form must inherit from forms.ModelForm (including multilevel inheritance)')
    if values.get('search') is not None:
        _is_type(model, value=values['search'], types=[list, tuple], kind='search')
        for field in values['search']:
            _is_type(model, value=field, types=str, kind='search field')
            if (error_field:=field.split('__')[0]) not in model_fields:
                _raise(model=model, error_type=ModelFieldError, field=error_field)
            del error_field
            _get_import(model, field.split('__'))
    if values.get('editables') is not None:
        _is_type(model, value=values['editables'], types=[list, tuple], kind='editables')
        if not values.get('columns'):
            _raise(model=model, error_type=CustomSyntaxError,
                      message='cannot use editables without columns')
        for editable in values['editables']:
            if editable not in model_fields:
                _raise(model=model, error_type=ModelFieldError,
                          field=editable)
            if editable not in values['columns']:
                _raise(model=model, error_type=ModelFieldError,
                          message=f'editable field "{editable}" must be one of the columns')
            if editable in values['columns'][0]:
                _raise(model=model, error_type=ModelFieldError,
                          message=f'editable field "{editable}" cannot be the first column')
            if values.get('links') and editable in values['links']:
                _raise(model=model, error_type=ModelFieldError,
                          message=f'field "{editable}" cannot be in both editables and links')
    if values.get('filters') is not None:
        _is_type(model, value=values['filters'], types=dict, kind='filter')
        _is_type(model, value=values['filters'].get('fields'), types=[list, tuple], kind='filter fields')
        for filter_name in values['filters']['fields']:
            _is_type(model, value=filter_name, types=str, kind='filter field')
            _get_import(model=model, field_list=filter_name.split('__'))
        if values['filters'].get('show_count'):
            _is_type(model, value=values['filters']['show_count'], types=str, kind='filter show count')
            match values['filters']['show_count']:
                case 'show':
                    values['filters']['show_count'] = ShowFacets.ALWAYS
                case 'hide':
                    values['filters']['show_count'] = ShowFacets.ALLOW
                case 'disable':
                    values['filters']['show_count'] = ShowFacets.NEVER
                case _:
                    _raise(model=model, error_type=CustomSyntaxError,
                           message='show_count must be "show", "hide" or "disable"')
    if values.get('search_text') is not None:
        if not values.get('search'):
            _raise(model=model, error_type=CustomSyntaxError,
                      message='cannot use search text without search')
        _is_type(model, value=values['search text'], types=str, kind='search text')
    if values.get('links') is not None:
        if not values.get('columns'):
            _raise(model=model, error_type=CustomSyntaxError,
                      message='cannot use links without columns')
        _is_type(model, value=values['links'], types=[list, tuple], kind='links')
        for link in values['links']:
            _is_type(model, value=link, types=str, kind='link')
            if link not in values['columns']:
                _raise(model=model, error_type=ModelFieldError,
                          message=f'link "{link}" must be one of {values["model"]}\'s current columns')

    return values


def _create_modeladmin(**kwargs: dict):
    class FastModelAdminClass(admin.ModelAdmin):
        list_display = kwargs.get('columns', ['__str__'])
        fieldsets = kwargs.get('parts', [])
        form = kwargs.get('form', template_model_form(_get_app(kwargs['model'])))
        actions = kwargs.get('actions', [])
        search_fields = kwargs.get('search', [])
        readonly_fields = kwargs.get('read_only_fields', [])
        list_filter = kwargs.get('filters', {}).get('fields', [])
        show_facets = kwargs.get('filters', {}).get('show_count', ShowFacets.NEVER)
        list_editable = kwargs.get('editables', [])
        ordering = kwargs.get('sort', [])
        search_help_text = kwargs.get('search_text')
        list_display_links = kwargs.get('links', [])

    return FastModelAdminClass


def _register_models(admin_model, register_all, files=None):
    if type(files) is not dict:
        _raise(error_type=ValueTypeError, kind='FAST_MODELADMIN_MODULES', value=files, types=dict)
    match admin_model:
        case list() | tuple():
            for values in admin_model:
                if type(values) is not dict:
                    _raise(error_type=OptionError, message='FAST_MODELADMIN elements must be dict')
                if type(values.get('model')) is not str:
                    _raise(error_type=ValueTypeError, kind='model', value=values.get('model'), types=str)
                model = cast(type[models.Model], _get_app(values['model']))
                if admin.site.is_registered(model):
                    _raise(error_type=OptionError, message=f'Model {values["model"]} cannot be registered again.')
                admin.site.register(model, _create_modeladmin(**_interpreter(values, files, model=model) or {}))
        case None:
            pass
        case _:
            _raise(error_type=ValueTypeError, kind='FAST_MODELADMIN', value=type(admin_model), types=[list, tuple])
    if register_all:
        for model in apps.get_models():
            if not admin.site.is_registered(model) and 'django' not in model.__module__:
                admin.site.register(model)
