from django.contrib.auth import get_user_model

Usuario = get_user_model()
total = Usuario.objects.filter(is_active=True).count()
print(f'Usuarios ativos: {total}')
for u in Usuario.objects.filter(is_active=True):
    print(f'  - {u.username} ({u.email})')
