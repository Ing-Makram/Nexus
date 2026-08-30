from .base import *

DEBUG = False

# ALLOWED_HOSTS is read from the ALLOWED_HOSTS environment variable in base.py.
# It MUST be set explicitly (comma-separated) in every production environment;
# the development default of "localhost,127.0.0.1" is not valid for production.
#
# Additional production hardening (HTTPS redirects, secure cookies, HSTS,
# static file serving) will be added in the security-hardening roadmap phase.
