from django import forms

class CFOPImportForm(forms.Form):
    arquivo = forms.FileField(label='Arquivo CSV', help_text='CSV com colunas de codigo,nome,descricao')
    replace = forms.BooleanField(required=False, initial=False, label='Substituir templates existentes')
    apply_to_all = forms.BooleanField(required=False, initial=False, label='Criar EmpresaCFOP para todas as empresas')
    dry_run = forms.BooleanField(required=False, initial=True, label='Somente simular (dry-run)')
