from django.urls import path
from . import views

app_name = 'surveys'

urlpatterns = [
    path('formularios/', views.FormListView.as_view(), name='form_list'),
    path('formularios/<str:code>/llenar/', views.FormFillView.as_view(), name='form_fill'),
    path('formularios/respuestas/', views.SubmissionListView.as_view(), name='submission_list'),
    path('formularios/respuestas/<uuid:pk>/', views.SubmissionDetailView.as_view(), name='submission_detail'),
    path('api/pharmacy-context/<uuid:pharmacy_id>/', views.PharmacyContextView.as_view(), name='pharmacy_context'),
]
