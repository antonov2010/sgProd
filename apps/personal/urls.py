from django.urls import path

from . import views

app_name = "personal"

urlpatterns = [
    path("login/", views.login_empleado, name="login"),
    path("logout/", views.logout_empleado, name="logout"),
]

urlpatterns = [
    path("login/", views.login_empleado, name="login"),
    path("logout/", views.logout_empleado, name="logout"),
    # AGREGAMOS ESTA LÍNEA PARA LA MATRIZ:
    path("matriz/", views.matriz_competencias, name="matriz_competencias"),
]