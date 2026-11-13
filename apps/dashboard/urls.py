from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('operador/', views.pantalla_operador, name='pantalla_operador'),
    path('jefe/', views.pantalla_jefe, name='pantalla_jefe'),
    path('gerente/', views.pantalla_gerente, name='pantalla_gerente'),
    path('gerente/bono/<int:empleado_id>/', views.detalle_elegible_bono, name='detalle_elegible_bono'),
]