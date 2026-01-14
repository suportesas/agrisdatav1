from .settings import *

# Use fast password hasher for tests to speed up auth operations
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Optional: reduce password hashing iterations for PBKDF2 in case it leaks in other code
# but MD5 above should be sufficient for test speed.
