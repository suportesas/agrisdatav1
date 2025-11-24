from django.urls import path
from . import views

app_name = 'dashboard'  # ← ESSENCIAL!

urlpatterns = [
    path('', views.index, name='index'),
]
