from django.urls import path
from . import views

app_name = 'user_app'  # Set the namespace for the app

urlpatterns = [
        path('login/', views.login, name='login'),
        path('logout/', views.logout_view, name='logout'),
        path('register/', views.register, name='register'),
        path('pricing/', views.pricing, name='pricing'),
        path('features/', views.features, name='features'),
        path('contact/', views.contact, name='contact'),
        path('try_free/', views.try_free, name='try_free'),
        path('terms/', views.terms, name='terms'),
        path('privacy_policy/', views.privacy_policy, name='privacy_policy'),
        path('user_dashboard/', views.user_dashboard, name='user_dashboard'),
        path('history/', views.history, name='history'),
        path('user_profile/', views.user_profile, name='user_profile'),
        path('edit_profile/', views.edit_profile, name='edit_profile'),
        path('settings/', views.settings, name='settings'),
        path('feedback/', views.feedback, name='feedback'),
]
