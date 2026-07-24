import json

from django import forms


class Select2AjaxWidget(forms.Select):
    """<select> widget for a ModelChoiceField backed by the unified Select2 AJAX
    combobox (see static/js/select2-ajax.js): opens showing the first page of
    records with nothing typed, refines via search-as-you-type, loads more in
    batches of 10 on scroll.

    Renders only the currently selected option (if any) instead of the whole
    queryset, so large tables (produtos, clientes, NCM...) never dump
    thousands of <option> tags into the page. Server-side validation is
    unaffected — ModelChoiceField.clean() looks the submitted pk up directly
    in the field's queryset, it doesn't depend on what the widget rendered.
    """

    def __init__(self, attrs=None, ajax_url=None, extra_params=None, placeholder='Buscar...'):
        base_attrs = {'class': 'form-select select2-ajax'}
        if ajax_url is not None:
            # ajax_url is typically a reverse_lazy() proxy so forms.py can
            # reference a URL name at class-body (import) time, before the
            # urlconf has finished loading — a truthy-check (`if ajax_url:`)
            # would force it to resolve immediately and blow up with a
            # circular-import error, so compare identity instead.
            base_attrs['data-ajax-url'] = ajax_url
        if extra_params:
            base_attrs['data-extra-params'] = json.dumps(extra_params)
        base_attrs['data-placeholder'] = placeholder
        if attrs:
            base_attrs['class'] = (base_attrs['class'] + ' ' + attrs.get('class', '')).strip()
            merged = {**base_attrs, **{k: v for k, v in attrs.items() if k != 'class'}}
        else:
            merged = base_attrs
        super().__init__(attrs=merged)

    @property
    def choices(self):
        return self._choices

    @choices.setter
    def choices(self, value):
        # ModelChoiceField assigns its ModelChoiceIterator here on every
        # queryset set. The base ChoiceWidget setter does list(value), which
        # eagerly evaluates the *entire* queryset — exactly the cost this
        # widget exists to avoid. Keep the iterator (and its lazy .queryset)
        # as-is; optgroups() below only ever needs a targeted pk__in lookup.
        self._choices = value

    def optgroups(self, name, value, attrs=None):
        selected = [v for v in value if v not in (None, '')]
        groups = [(None, [self.create_option(name, '', '', False, 0)], 0)]
        queryset = getattr(self.choices, 'queryset', None)
        if selected and queryset is not None:
            for obj in queryset.filter(pk__in=selected):
                groups.append((None, [self.create_option(
                    name, str(obj.pk), str(obj), True, len(groups)
                )], len(groups)))
        return groups


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


class DecimalBRInput(forms.TextInput):
    """Input de texto para valores decimais com máscara BR (1.234,5678) via static/js/money-mask.js.

    Igual ao MoneyBRInput, mas com número de casas decimais configurável — usado
    para quantidades, preços unitários, taxas de câmbio e alíquotas com 3-4 casas.
    O valor é armazenado/enviado ao servidor como decimal simples (ex: "1234.5678").
    """

    def __init__(self, attrs=None, decimals=2):
        placeholder = '0,' + '0' * decimals if decimals > 0 else '0'
        base_attrs = {
            'class': 'form-control money-mask-input',
            'inputmode': 'decimal',
            'placeholder': placeholder,
            'autocomplete': 'off',
            'data-decimals': str(decimals),
        }
        if attrs:
            base_attrs['class'] = (base_attrs['class'] + ' ' + attrs.get('class', '')).strip()
            merged = {**base_attrs, **{k: v for k, v in attrs.items() if k != 'class'}}
        else:
            merged = base_attrs
        super().__init__(attrs=merged)
