from django.urls import path

from users import views

app_name = 'users'

urlpatterns = [
    path('', views.register, name='register'),
    path('login/', views.login_view, name='login'),
]