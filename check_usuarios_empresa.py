"""Script para verificar usuários e suas empresas"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuarios.models import Usuario
from empresas.models import Empresa

print("=" * 60)
print("VERIFICAÇÃO DE USUÁRIOS E EMPRESAS")
print("=" * 60)

usuarios = Usuario.objects.select_related('empresa').all()
print(f"\nTotal de usuários: {usuarios.count()}")

empresas = Empresa.objects.all()
print(f"Total de empresas: {empresas.count()}\n")

print("Lista de empresas:")
for emp in empresas:
    print(f"  - ID: {emp.id}, Nome: {emp.nome}")

print("\n" + "=" * 60)
print("USUÁRIOS E SUAS EMPRESAS:")
print("=" * 60)

for u in usuarios[:20]:
    if u.empresa:
        print(f"ID: {u.id:3d} | User: {u.username:20s} | Empresa: {u.empresa.nome}")
    else:
        print(f"ID: {u.id:3d} | User: {u.username:20s} | Empresa: *** SEM EMPRESA ***")

print("\n" + "=" * 60)
sem_empresa = usuarios.filter(empresa__isnull=True).count()
print(f"Usuários SEM empresa: {sem_empresa}")
print(f"Usuários COM empresa: {usuarios.filter(empresa__isnull=False).count()}")
print("=" * 60)
