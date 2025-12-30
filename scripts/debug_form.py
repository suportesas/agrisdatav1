from empresas.models import Plano, Empresa
from django.contrib.auth import get_user_model
from cadastros.forms import FornecedorForm, FornecedorContatoForm, FornecedorDadoBancarioForm

# setup minimal objects
plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
empresa = Empresa.objects.create(nome='E', plano=plano)
User = get_user_model()
user = User.objects.create_user(username='u', password='pass')

# Test FornecedorForm
form = FornecedorForm(data={'nome':'Novo Fornecedor','cnpj_cpf':'22.222.222/2222-22'}, empresa=empresa, usuario=user)
print('FornecedorForm valid?', form.is_valid())
print('errors', form.errors)

# Test Contato form
cont_form = FornecedorContatoForm(data={'nome':'João','telefone':'1111'},)
print('ContatoForm valid?', cont_form.is_valid())
print('errors', cont_form.errors)

# Test Conta form
conta_form = FornecedorDadoBancarioForm(data={'banco':'Banco X','conta':'123','conta_digito':'5'})
print('ContaForm valid?', conta_form.is_valid())
print('errors', conta_form.errors)
