from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/register/', views.register_view, name='register'),
    path('api/auth/login/', views.login_view, name='login'),
    path('api/auth/logout/', views.logout_view, name='logout'),
    path('api/auth/user/', views.current_user_view, name='current_user'),
    path('api/auth/users/', views.users_list_view, name='users_list'),
    
    path('api/materials/', views.list_materials, name='list_materials'),
    path('api/materials/create/', views.create_material, name='create_material'),
    path('api/materials/<int:material_id>/', views.material_detail, name='material_detail'),
    
    path('api/groups/', views.list_groups, name='list_groups'),
    path('api/groups/create/', views.create_group, name='create_group'),
    path('api/groups/<int:group_id>/', views.group_detail, name='group_detail'),
    path('api/groups/<int:group_id>/members/', views.manage_group_members, name='manage_group_members'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) \
  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
