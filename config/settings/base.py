"""
Ajustes comunes de SG-Prod (guía §8.6).

Los valores sensibles se leen del .env de la raíz; nunca se escriben aquí.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # API REST + generación del esquema OpenAPI (Swagger)
    "rest_framework",
    "drf_spectacular",
    "django_extensions",
    "apps.core",
    "apps.personal",
    "apps.calidad",
    "apps.dashboard",
    "apps.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # paquete de diseño de Martha
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database: PostgreSQL local del contenedor (postgresql/docker-compose.yml)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT", default="5432"),
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internacionalización

LANGUAGE_CODE = "es-mx"
TIME_ZONE = env("TZ", default="America/Tijuana")
USE_I18N = True
USE_TZ = True


# Archivos estáticos

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]  # paquete de diseño de Martha

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# API REST y documentación Swagger / OpenAPI
# Guía de uso: docs/03_guia_api_swagger.md

REST_FRAMEWORK = {
    # drf-spectacular genera el esquema OpenAPI 3 a partir de las vistas DRF.
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # La API expone datos de personal: solo usuarios de Django autenticados.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Sesión de Django (la misma del Admin). DRF exige CSRF en este modo.
        "rest_framework.authentication.SessionAuthentication",
        # HTTP Basic, cómodo para curl/Postman y para Swagger "Authorize".
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SG-Prod API",
    "DESCRIPTION": (
        "API REST de SG-Prod (Django 5.2 + DRF). Documenta el catálogo de "
        "personal, la matriz de habilidades y los registros de calidad.\n\n"
        "**Autenticación:** sesión de Django (entra primero a `/admin/`) o HTTP "
        "Basic. En Swagger usa el botón *Authorize*."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SCHEMA_PATH_PREFIX": "/api",
    # Fija la versión de Swagger UI para que un cambio del CDN no rompa la UI.
    "SWAGGER_UI_DIST": "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5",
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": False,
        "filter": True,
    },
    "TAGS": [
        {"name": "personal", "description": "Empleados, roles, líneas y estaciones."},
        {"name": "matriz", "description": "Matriz de habilidades (skill matrix)."},
        {"name": "calidad", "description": "Defectos, asignaciones y registros horarios."},
        {"name": "dashboard", "description": "Metas, bonos y alertas de capacitación."},
    ],
}

