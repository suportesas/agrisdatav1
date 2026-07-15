from django import forms


class MoneyBRInput(forms.TextInput):
    """Input de texto para valores monetários com máscara BR (1.234,56) via static/js/money-mask.js.

    O valor é armazenado/enviado ao servidor como decimal simples (ex: "1234.56"),
    a máscara cuida apenas da exibição/digitação.
    """

    def __init__(self, attrs=None):
        base_attrs = {'class': 'form-control money-mask-input', 'inputmode': 'decimal', 'placeholder': '0,00', 'autocomplete': 'off'}
        if attrs:
            base_attrs['class'] = (base_attrs['class'] + ' ' + attrs.get('class', '')).strip()
            merged = {**base_attrs, **{k: v for k, v in attrs.items() if k != 'class'}}
        else:
            merged = base_attrs
        super().__init__(attrs=merged)
