"""Rutas de la API de análisis (montadas en /api/)."""

from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("analizar/", views.api_analizar, name="analizar"),
    path("foto/", views.api_foto, name="foto"),
    path("practica/", views.api_practica, name="practica"),
]
