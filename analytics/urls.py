from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_edit'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/ventas/', views.SalesDashboardView.as_view(), name='sales_dashboard'),
    path('dashboard/operaciones/', views.OpsDashboardView.as_view(), name='ops_dashboard'),
    path('farmacias/', views.PharmacyListView.as_view(), name='pharmacy_list'),
    path('productos/', views.ProductListView.as_view(), name='product_list'),
    path('reportes/detallado/', views.OrderMasterListView.as_view(), name='order_master_list'),
    # Form URLs moved to surveys app

    path('configuracion/perfil/', views.UserProfileView.as_view(), name='profile'),
]
