from django.urls import path
from . import views

app_name = 'wpp'

urlpatterns = [
    # Tags URLs
    path('wpp/tags/', views.TagListView.as_view(), name='tag_list'),
    path('wpp/tags/criar/', views.TagCreateView.as_view(), name='tag_create'),
    path('wpp/tags/<uuid:pk>/editar/', views.TagUpdateView.as_view(), name='tag_update'),
    path('wpp/tags/<uuid:pk>/deletar/', views.TagDeleteView.as_view(), name='tag_delete'),
    
    # Contacts URLs
    path('wpp/contatos/', views.ContactListView.as_view(), name='contact_list'),
    path('wpp/contatos/criar/', views.ContactCreateView.as_view(), name='contact_create'),
    path('wpp/contatos/<uuid:pk>/editar/', views.ContactUpdateView.as_view(), name='contact_update'),
    path('wpp/contatos/<uuid:pk>/deletar/', views.ContactDeleteView.as_view(), name='contact_delete'),
    path('wpp/contatos/<uuid:pk>/', views.ContactDetailView.as_view(), name='contact_detail'),
    
    # Import CSV
    path('wpp/contatos/importar/', views.ContactImportView.as_view(), name='contact_import'),
    path('wpp/contatos/exportar/', views.ContactExportView.as_view(), name='contact_export'),
    
    # AJAX URLs
    path('ajax/contacts-list/', views.AjaxContactsListView.as_view(), name='ajax_contacts_list'),
    path('ajax/tags-list/', views.AjaxTagsListView.as_view(), name='ajax_tags_list'),
    path('ajax/contact-form/', views.AjaxContactFormView.as_view(), name='ajax_contact_form'),
    path('ajax/contact-form/<uuid:pk>/', views.AjaxContactFormView.as_view(), name='ajax_contact_form_edit'),
    path('ajax/contact-save/', views.AjaxContactSaveView.as_view(), name='ajax_contact_save'),
    path('ajax/tag-form/', views.AjaxTagFormView.as_view(), name='ajax_tag_form'),
    path('ajax/tag-form/<uuid:pk>/', views.AjaxTagFormView.as_view(), name='ajax_tag_form_edit'),
    path('ajax/tag-save/', views.AjaxTagSaveView.as_view(), name='ajax_tag_save'),
    path('ajax/import-form/', views.AjaxImportFormView.as_view(), name='ajax_import_form'),
    path('ajax/import-contacts/', views.AjaxImportContactsView.as_view(), name='ajax_import_contacts'),
    path('ajax/contact-delete/<uuid:pk>/', views.AjaxContactDeleteView.as_view(), name='ajax_contact_delete'),
    path('ajax/tag-delete/<uuid:pk>/', views.AjaxTagDeleteView.as_view(), name='ajax_tag_delete'),
    path('ajax/stats/', views.AjaxStatsView.as_view(), name='ajax_stats'),
    
    # Dashboard
    path('wpp/dashboard', views.DashboardView.as_view(), name='dashboard'),
]