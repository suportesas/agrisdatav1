import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import ArmadorEndereco

print("=" * 80)
print("DETALHES COMPLETOS DOS ENDEREÇOS")
print("=" * 80)

enderecos = ArmadorEndereco.objects.all().order_by('-id')

for e in enderecos:
    print(f"\nID: {e.id} | Armador: {e.armador.nome}")
    print(f"  Logradouro: '{e.logradouro}'")
    print(f"  Número: '{e.numero}'")
    print(f"  Complemento: '{e.complemento}'")
    print(f"  Bairro: '{e.bairro}'")
    print(f"  Cidade: '{e.cidade}'")
    print(f"  UF: '{e.uf}'")
    print(f"  CEP: '{e.cep}'")
    print(f"  País: '{e.pais}'")
    print(f"  Padrão: {e.padrao}")

print("\n" + "=" * 80)
