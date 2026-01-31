from django.urls import path
from . import views

app_name = "pages"

urlpatterns = [
    path("", views.ph360, name="ph360"),
]
