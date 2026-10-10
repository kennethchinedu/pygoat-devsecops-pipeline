import os

# ruleid: hardcoded-django-secret-key
SECRET_KEY = "django-insecure-test-key-123"

# ok: hardcoded-django-secret-key
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
