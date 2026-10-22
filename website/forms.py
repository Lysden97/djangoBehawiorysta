from datetime import timedelta

from django import forms
from django.utils import timezone

from .catalog import SERVICES, service_label


class ContactForm(forms.Form):
    name = forms.CharField(label="Imię", max_length=80)
    last_name = forms.CharField(label="Nazwisko", max_length=100)
    email = forms.EmailField(label="E-mail", max_length=254)
    phone = forms.RegexField(label="Telefon", regex=r"^\+?[0-9 ()-]{9,25}$", max_length=25)
    address = forms.CharField(
        label="Dzielnica / miejscowość (opcjonalnie)", max_length=200, required=False
    )
    preferred_date = forms.DateField(
        label="Preferowany termin",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    animal_info = forms.CharField(label="Imię i wiek zwierzęcia", max_length=150)
    animal_breed = forms.CharField(label="Gatunek i rasa", max_length=150)
    gender = forms.ChoiceField(
        label="Płeć zwierzęcia",
        choices=[("", "Wybierz")]
        + [
            (v, v)
            for v in (
                "Samiec - niekastrowany",
                "Samiec - kastrowany/sterylizowany",
                "Samica - niekastrowana",
                "Samica - kastrowana/sterylizowana",
            )
        ],
    )
    appointment_type = forms.ChoiceField(
        label="Typ wizyty",
        choices=[("", "Wybierz")] + [(s["id"], service_label(s)) for s in SERVICES],
    )
    message = forms.CharField(
        label="Opis problemu",
        min_length=10,
        max_length=4000,
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    terms = forms.BooleanField(
        label="Wyrażam zgodę na przetwarzanie danych w celu obsługi zgłoszenia."
    )
    privacy_policy = forms.BooleanField(label="Potwierdzam zapoznanie się z polityką prywatności.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

    def clean_preferred_date(self):
        date = self.cleaned_data["preferred_date"]
        today = timezone.localdate()
        if not today <= date <= today + timedelta(days=90):
            raise forms.ValidationError("Wybierz datę od dziś do 90 dni naprzód.")
        return date

    def clean_phone(self):
        value = self.cleaned_data["phone"]
        if not 9 <= sum(c.isdigit() for c in value) <= 15:
            raise forms.ValidationError("Podaj od 9 do 15 cyfr numeru telefonu.")
        return value
