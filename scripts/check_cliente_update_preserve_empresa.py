import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuarios.models import Usuario
from empresas.models import Empresa
from cadastros.models import Cliente
from cadastros.forms import ClienteForm

# Create empresa and user
emp = Empresa.objects.create(nome='Empresa Script')
user = Usuario.objects.create_user(username='script', password='script')
user.empresa = emp
user.save()

# Create cliente
c = Cliente.objects.create(empresa=emp, razao_social='Original', cnpj_cpf='12345678901234')

# Prepare POST-like data without 'empresa'
data = {
    'razao_social': 'Updated from script',
    'cnpj_cpf': c.cnpj_cpf,
    'tipo_cliente': c.tipo_cliente,
    'tipo_pessoa': c.tipo_pessoa,
}

form = ClienteForm(data, instance=c, empresa=user.empresa, usuario=user)
print('Form valid?', form.is_valid())
print('Form errors:', form.errors)
cliente = form.save()
print('Cliente saved. Empresa:', cliente.empresa, 'Razao:', cliente.razao_social)
