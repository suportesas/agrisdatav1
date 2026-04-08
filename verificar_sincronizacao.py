import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuarios.models_supabase import SupabaseUsuarioSync

registros = SupabaseUsuarioSync.objects.all()
print(f"Total de registros na tabela SupabaseUsuarioSync: {registros.count()}\n")
print("Registros:")
for reg in registros:
    print(f"  - {reg.usuario.email}")
    print(f"    UID: {reg.supabase_uid}")
    print(f"    Sincronizado: {reg.sincronizado}")
    print(f"    Data: {reg.ultima_sincronizacao}\n")
