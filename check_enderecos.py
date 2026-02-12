import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import ArmadorEndereco, Armador

print("=" * 60)
print("VERIFICANDO ENDEREÇOS DO ARMADOR NO BANCO DE DADOS")
print("=" * 60)

# Listar todos os armadores
armadores = Armador.objects.all()
print(f"\nTotal de Armadores: {armadores.count()}\n")

for armador in armadores:
    enderecos = ArmadorEndereco.objects.filter(armador=armador)
    print(f"Armador: {armador.nome} (ID: {armador.id})")
    print(f"  Endereços: {enderecos.count()}")
    
    if enderecos.exists():
        for e in enderecos:
            print(f"    - {e.logradouro}, {e.numero} - {e.cidade}/{e.uf} (CEP: {e.cep})")
    else:
        print(f"    ⚠️  SEM ENDEREÇOS CADASTRADOS")
    print()

print("=" * 60)
