"""Rutas principales del proyecto EmoSense."""

from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("detector/", include("detector.urls")),
    path("api/", include("detector.urls_api")),
    path("admin/", admin.site.urls),
]
