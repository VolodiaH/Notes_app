from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from notes.forms import LoginForm
from django.urls import include, path

urlpatterns = [
    path('accounts/login/', LoginView.as_view(template_name='registration/login.html', authentication_form=LoginForm), name='login'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('', include('notes.urls')),
    path('admin/', admin.site.urls),
]
