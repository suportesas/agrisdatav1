from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import Client
from empresas.models import Empresa, Role
from django.contrib.auth.models import Permission

class Command(BaseCommand):
    help = 'Debug permissions endpoint and sample data'

    def handle(self, *args, **options):
        User = get_user_model()
        emp, created = Empresa.objects.get_or_create(nome='Debug Empresa CMD')
        user, _ucreated = User.objects.get_or_create(username='debugusercmd')
        if _ucreated:
            user.set_password('pass')
            user.save()
        user.empresa = emp
        user.save()

        role, _ = Role.objects.get_or_create(empresa=emp, name='DebugRoleCMD')

        c = Client()
        logged = c.login(username='debugusercmd', password='pass')
        print('Logged in:', logged)

        url = f'/empresas/roles/{role.id}/permissions/'
        resp = c.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        print('AJAX status:', resp.status_code)
        try:
            data = resp.json()
            print('AJAX keys:', list(data.keys()))
            print('Permissions count:', len(data.get('permissions', [])))
            if len(data.get('permissions', []))>0:
                print('First item sample:', data['permissions'][0])
        except Exception as e:
            print('AJAX response content (truncated):', resp.content[:200])

        # Also test role page render
        resp2 = c.get(url)
        print('Page status:', resp2.status_code)
        print('Page content head:', resp2.content[:200])

        print('Total system permissions:', Permission.objects.count())
        print('Sample permissions:', list(Permission.objects.values_list('codename', flat=True)[:10]))
