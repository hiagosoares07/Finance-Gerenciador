from django.urls import path

from users import financial_views

app_name = 'finance'

urlpatterns = [
    path('<slug:entity>/', financial_views.entity_list, name='entity_list'),
    path('<slug:entity>/novo/', financial_views.entity_create, name='entity_create'),
    path('<slug:entity>/<int:pk>/editar/', financial_views.entity_update, name='entity_update'),
    path('<slug:entity>/<int:pk>/excluir/', financial_views.entity_delete, name='entity_delete'),
]
