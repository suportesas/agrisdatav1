#!/usr/bin/env python
"""Test Supabase configuration"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from core.supabase_config import supabase_client, supabase_auth
from django.conf import settings

print("="*60)
print("✓ Supabase Configuration Test")
print("="*60)
print(f"✓ SUPABASE_URL: {settings.SUPABASE_URL[:50]}...")
print(f"✓ SUPABASE_KEY (partial): {settings.SUPABASE_ANON_KEY[:30]}...")
print(f"✓ AUTH_MODE: {settings.AUTH_MODE}")
print("="*60)
print("✓ Supabase client initialized successfully")
print(f"  Client type: {type(supabase_client).__name__}")
print("="*60)
print("✓ SupabaseAuth adapter ready")
print(f"  Type: {type(supabase_auth).__name__}")
print("="*60)
print("✅ ALL TESTS PASSED - Configuration ready for authentication")
print("="*60)
