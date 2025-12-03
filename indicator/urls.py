# indicator/urls.py
from django.urls import path
from . import views

app_name = 'indicator'

urlpatterns = [
    path('', views.index, name='index'),
    path('process/', views.process_and_render, name='process'),
    path('results/', views.results, name='results'),
    path('download/', views.download_processed, name='download'),
]
