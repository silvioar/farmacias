from django.urls import path
from .views import optimized_route_view, toggle_visitado

app_name = 'routes'

urlpatterns = [
    path("ruta/", optimized_route_view, name="optimized_route"),
    path("toggle-visit/", toggle_visitado, name="toggle_visitado"),
]
