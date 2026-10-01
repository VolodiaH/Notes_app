from django.urls import path

from . import views

app_name = 'notes'

urlpatterns = [
    path('', views.index, name='index'),
    path('notes/new/', views.create, name='create'),
    path('notes/<int:pk>/', views.detail, name='detail'),
    path('notes/<int:pk>/delete/', views.delete, name='delete'),
]
