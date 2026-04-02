from django import forms

class XMLNFeUploadForm(forms.Form):
    xml_file = forms.FileField(
        label='Arquivo XML da NF-e',
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xml'}),
    )

    def clean_xml_file(self):
        xml_file = self.cleaned_data['xml_file']
        if not xml_file.name.lower().endswith('.xml'):
            raise forms.ValidationError('Selecione um arquivo XML valido.')
        if xml_file.size > 2 * 1024 * 1024:
            raise forms.ValidationError('O arquivo XML nao pode exceder 2 MB.')
        return xml_file
