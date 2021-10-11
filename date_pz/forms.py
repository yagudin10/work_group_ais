from django import forms
from django.forms import ModelForm, Form, DateField, ChoiceField, Select
from django import forms
from .models import MFC

URM_choices = (
        ("1", "Филиалам"),
        ("2", "УРМам"),
)

class MFCForm(ModelForm):

    class Meta:
        model = MFC
        fields = ['name']

class DateInput(forms.DateInput):
    input_type = 'date'
class DateForm(Form):
    date_field = DateField(widget=DateInput)

class DateFormAppointment(Form):
    date1_field = DateField(widget=DateInput)
    date2_field = DateField(widget=DateInput)

class DateFormMRS(Form):
    date1_field = DateField(widget=DateInput)
    date2_field = DateField(widget=DateInput)
    urm_field = ChoiceField(choices=URM_choices)
