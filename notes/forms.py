from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group

from .models import Category, Note


class ReminderInput(forms.DateTimeInput):
    input_type = 'datetime-local'

    def __init__(self, **kwargs):
        super().__init__(format='%Y-%m-%dT%H:%M', **kwargs)


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css_class = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            if self.is_bound and name in self.errors:
                css_class += ' is-invalid'
            field.widget.attrs['class'] = css_class


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


class NoteForm(BootstrapFormMixin, forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['group'].queryset = user.groups.all() if user else Group.objects.none()
        if user is not None and not self.instance.pk:
            self.instance.owner = user

    def full_clean(self):
        self.fields['group'].queryset = self.user.groups.all() if self.user else Group.objects.none()
        super().full_clean()

    class Meta:
        model = Note
        fields = ['title', 'text', 'reminder', 'category', 'group']
        labels = {
            'title': 'Назва', 'text': 'Текст',
            'reminder': 'Нагадування', 'category': 'Категорія', 'group': 'Група',
        }
        widgets = {'reminder': ReminderInput(), 'text': forms.Textarea(attrs={'rows': 8})}
        help_texts = {'reminder': 'Необов’язково. Час за Києвом.', 'group': 'Залиште порожнім для персональної нотатки.'}


class NoteFilterForm(BootstrapFormMixin, forms.Form):
    q = forms.CharField(label='Пошук за назвою', required=False, max_length=200)
    category = forms.ModelChoiceField(
        label='Категорія', queryset=Category.objects.order_by('title'),
        required=False, empty_label='Усі категорії',
    )
    reminder_from = forms.DateTimeField(
        label='Нагадування від', required=False, widget=ReminderInput(),
    )
    reminder_to = forms.DateTimeField(
        label='Нагадування до', required=False, widget=ReminderInput(),
    )

    def clean(self):
        data = super().clean()
        start, end = data.get('reminder_from'), data.get('reminder_to')
        if start and end and start > end:
            self.add_error('reminder_to', 'Кінець періоду має бути не раніше початку.')
        return data
