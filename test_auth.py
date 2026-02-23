#!/usr/bin/env python
import os
import django
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuarios.models import Usuario
from django.contrib.auth.models import User

# Get admin user from both models
try:
    admin_usuario = Usuario.objects.get(username='admin')
    print(f"✅ Usuario model - admin encontrado")
    print(f"   is_superuser: {admin_usuario.is_superuser}")
    print(f"   is_staff: {admin_usuario.is_staff}")
except:
    print("❌ Usuario model - admin não encontrado")
    admin_usuario = None

try:
    admin_user = User.objects.get(username='admin')
    print(f"\n✅ Django User model - admin encontrado")
    print(f"   is_superuser: {admin_user.is_superuser}")
    print(f"   is_staff: {admin_user.is_staff}")
except:
    print("\n❌ Django User model - admin não encontrado")
    admin_user = None

# Create test client and login
print("\n\n🔍 Testando login via client:\n")
client = Client()

# Try logging in
login_response = client.post('/login/', {
    'username': 'admin',
    'password': 'admin',  # Assume password is 'admin'
}, follow=True)

print(f"✅ Login response status: {login_response.status_code}")

# Check if user is authenticated in session
dashboard_response = client.get('/dashboard/')
print(f"✅ Dashboard response status: {dashboard_response.status_code}")

# Check session
if hasattr(dashboard_response, 'wsgi_request'):
    request = dashboard_response.wsgi_request
    print(f"\n✅ User in request: {request.user}")
    print(f"   is_authenticated: {request.user.is_authenticated}")
    print(f"   is_superuser: {request.user.is_superuser}")
    print(f"   username: {request.user.username}")
    print(f"   Model: {request.user.__class__.__name__}")
