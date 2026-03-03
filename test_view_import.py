#!/usr/bin/env python
"""Test if parcela_criar view loads without NameError"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, r'C:\erp_agricola')

django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.filter(username='admin').first()

if user:
    print(f"✅ Admin user found: {user.username}")
    client = Client()
    login_ok = client.login(username='admin', password='admin')
    print(f"✅ Login: {login_ok}")
    
    try:
        response = client.get('/financeiro/contas/1/parcelas/criar/')
        print(f"✅ Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Page loaded successfully!")
            print(f"✅ Context keys: {list(response.context.keys())}")
        elif response.status_code == 302:
            print(f"⚠️  Redirect to: {response.url}")
        else:
            print(f"❌ Error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
else:
    print("❌ Admin user not found")
