from django.urls import path
from . import views

app_name = 'media_handling_app'  # Set the namespace for the app

urlpatterns = [
    path('search/', views.search, name='search'),
]
