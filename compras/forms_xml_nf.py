from django import forms

class XMLNFeUploadForm(forms.Form):
    xml_file = forms.FileField(label='Arquivo XML da NF-e', required=True)
