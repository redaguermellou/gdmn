from django.urls import path,include
from . import views
from django.views.generic.base import RedirectView

urlpatterns = [
    path('dossier/<int:dossier_id>/edit/', views.edit_dossier, name='edit_dossier'),
    path('dossier/<int:pk>/delete/', views.dossier_delete, name='dossier_delete'),

    path('dossier/<int:dossier_id>/approve/', views.approve_dossier, name='approve_dossier'),
    path('dossier/<int:dossier_id>/reject/', views.reject_dossier, name='reject_dossier'),
    path('redirect-home/', views.redirect_home, name='redirect_home'),
    path('dossier/<int:dossier_id>/upload/', views.upload_document, name='upload_document'),
    path('user/dossiers/create/dossier_list', RedirectView.as_view(pattern_name='dossier_list', permanent=False)),
    path('', views.dossier_list, name='dossier_list'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('<int:dossier_id>/', views.dossier_detail, name='dossier_detail'),
    path('<int:dossier_id>/download_all/', views.download_all, name='download_all'),
    path('<int:dossier_id>/approve/', views.approve_dossier, name='dossier_approve'),
    path('<int:dossier_id>/reject/', views.reject_dossier, name='dossier_reject'),
    path('<int:dossier_id>/report/', views.generate_report, name='generate_report'),
    path('dossiers/create/', views.create_dossier, name='create_dossier'),
    path('audit-log/', views.audit_log, name='audit_log'),
    path('global-report/', views.global_report, name='global_report'),
    
    # Prise en Charge
    path('pec/', views.pec_list, name='pec_list'),
    path('pec/create/', views.pec_create, name='pec_create'),
    path('pec/<int:pec_id>/', views.pec_detail, name='pec_detail'),
    path('pec/<int:pec_id>/approve/', views.pec_approve, name='pec_approve'),
    path('pec/<int:pec_id>/reject/', views.pec_reject, name='pec_reject'),
    path('pec/<int:pec_id>/delete/', views.pec_delete, name='pec_delete'),
]