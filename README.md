# django-fast-modeladmin

[![downloads](https://static.pepy.tech/badge/django-fast-modeladmin)](https://www.pepy.tech/projects/django-fast-modeladmin) [![changelog](https://raw.githubusercontent.com/SimplePythonCoder/zipmanager/main/images/Changelog.svg)](https://github.com/SimplePythonCoder/django-fast-modeladmin/blob/main/CHANGELOG.md) [![wiki](https://raw.githubusercontent.com/SimplePythonCoder/zipmanager/main/images/Wiki.svg)](https://github.com/SimplePythonCoder/django-fast-modeladmin/wiki)


A fast way to customize your django admin site.

### Installation & Usage

```
pip install django-fast-modeladmin
```

Add fast_modeladmin to INSTALLED_APPS:
```python
# settings.py
INSTALLED_APPS = [
    ...,
    'fast_modeladmin'
]

...

FAST_MODELADMIN = (...)
```

## Features

Allows you to control many of the Django admin sited functionalities with a dict for each model instead of creating many classes.

Including:
- edit columns shown in the model table page
- a search box for specific fields (including foreign keys)
- select which fields are editable or not

and many more.

The package also include an error system for easier readability.

more info at the [wiki](https://github.com/SimplePythonCoder/django-fast-modeladmin/wiki).