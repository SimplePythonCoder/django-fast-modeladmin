class BaseFastAdminException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class ImproperlyConfigured(BaseFastAdminException):
    pass


class CustomSyntaxError(BaseFastAdminException):
    def __init__(self, message, model=None):
        if model:
            message = f'{model.__name__} Model: {message}'
        super().__init__(message)


class ModuleError(CustomSyntaxError):
    pass


class ClassError(CustomSyntaxError):
    pass


class DecoratorError(CustomSyntaxError):
    def __init__(self, function, decorator, model=None):
        super().__init__(message=f'action "{function}" does not use the "{decorator}" decorator', model=model)


class ValueTypeError(CustomSyntaxError):
    @staticmethod
    def get_str_type(types):
        match types:
            case list():
                return ' or '.join([t.__name__ if t is not None else "None" for t in types])
            case type():
                return types.__name__
            case None:
                return 'None'
            case _:
                return type(types).__name__

    def __init__(self, value, types, kind, model=None):
        if type(value) is str:
            value = f'"{value}"'
        super().__init__(model=model,
                         message=f'{kind} type is {self.get_str_type(value)} instead of '
                                 f'{self.get_str_type(types)}' +
                                 (f' [{kind}: {value}]' if model else '')
                         )


class OptionError(CustomSyntaxError):
    pass


class ModelNotFound(BaseFastAdminException):
    def __init__(self, model):
        if hasattr(model, '__name__'):
            model = model.__name__
        super().__init__(f'Model "{model}" not found')


class ModelFieldError(BaseFastAdminException):
    def __init__(self, model, field=None, message=None):
        if type(field) is str:
            super().__init__(f'field "{field}" not found in {model.__name__} model')
        elif type(message) is str:
            super().__init__(message)

def _raise(error_type, *args, **kwargs):
    raise error_type(*args, **kwargs) from None
