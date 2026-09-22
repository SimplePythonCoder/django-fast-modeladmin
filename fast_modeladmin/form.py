from django import forms

def template_model_form(model_to_render, fields_to_render: list | None = None):
    class GenericModelForm(forms.ModelForm):
        class Meta:
            model = model_to_render
            fields = fields_to_render if fields_to_render else '__all__'

    return GenericModelForm
