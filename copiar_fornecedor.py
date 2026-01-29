import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import Fornecedor
from empresas.models import Empresa

# Buscar o fornecedor TUBOTECNICO
fornecedor_original = Fornecedor.objects.get(id=4)

print(f"\nFornecedor encontrado:")
print(f"  Nome: {fornecedor_original.nome}")
print(f"  Empresa atual: {fornecedor_original.empresa.nome}")
print(f"  CNPJ: {fornecedor_original.cnpj_cpf}")

# Buscar empresa destino
empresa_destino = Empresa.objects.get(id=1)  # Agricola Salutaris S.A

# Verificar se já existe na empresa destino
ja_existe = Fornecedor.objects.filter(
    empresa=empresa_destino,
    cnpj_cpf=fornecedor_original.cnpj_cpf
).exists()

if ja_existe:
    print(f"\n❌ Este fornecedor já existe na empresa '{empresa_destino.nome}'")
else:
    # Criar cópia do fornecedor na empresa destino
    novo_fornecedor = Fornecedor(
        empresa=empresa_destino,
        nome=fornecedor_original.nome,
        nome_fantasia=fornecedor_original.nome_fantasia,
        cnpj_cpf=fornecedor_original.cnpj_cpf,
        inscricao_estadual=fornecedor_original.inscricao_estadual,
        telefone=fornecedor_original.telefone,
        celular=fornecedor_original.celular,
        email=fornecedor_original.email,
        cep=fornecedor_original.cep,
        endereco=fornecedor_original.endereco,
        numero=fornecedor_original.numero,
        complemento=fornecedor_original.complemento,
        bairro=fornecedor_original.bairro,
        cidade=fornecedor_original.cidade,
        uf=fornecedor_original.uf,
        pais=fornecedor_original.pais,
        website=fornecedor_original.website,
        ativa=fornecedor_original.ativa,
    )
    novo_fornecedor.save()
    
    print(f"\n✓ Fornecedor copiado com sucesso!")
    print(f"  ID novo: {novo_fornecedor.id}")
    print(f"  Empresa: {empresa_destino.nome}")
    print(f"\nAgora a empresa 'Agricola Salutaris S.A' tem {Fornecedor.objects.filter(empresa=empresa_destino).count()} fornecedores.")
