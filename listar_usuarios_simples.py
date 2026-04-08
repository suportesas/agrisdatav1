import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model

Usuario = get_user_model()
usuarios = Usuario.objects.filter(is_active=True)
total = usuarios.count()

print(f"Total de usuarios ativos: {total}")
if total > 0:
    print("\nUsuarios:")
    for u in usuarios:
        print(f"  {u.username} ({u.email})")
else:
    print("Nenhum usuario encontrado")
