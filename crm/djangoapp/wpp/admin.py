# contacts/admin.py
from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.db import models

from .models import Contact, Tag, Campaign, Message, MessageLog
from accounts.models import Company


class TagAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cor_preview', 'company', 'created_at', 'updated_at']
    list_filter = ['company']
    search_fields = ['nome']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        ('Informações da Tag', {
            'fields': ('nome', 'cor', 'company'),
            'description': 'Definições principais da tag'
        }),
        ('Metadados', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def cor_preview(self, obj):
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px;">{}</span>',
            obj.cor,
            obj.cor
        )
    cor_preview.short_description = "Cor"

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('company')
        if not request.user.is_superuser and hasattr(request.user, 'company'):
            if not request.user.is_master_user():
                qs = qs.filter(company=request.user.company)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "company":
            if not request.user.is_superuser and hasattr(request.user, 'company'):
                if not request.user.is_master_user():
                    kwargs["queryset"] = Company.objects.filter(id=request.user.company.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ContactAdmin(admin.ModelAdmin):
    list_display = ['nome', 'telefone', 'email', 'ativo_badge', 'company_info', 'origem', 'created_at']
    list_filter = ['ativo', 'company', 'tags', 'origem', 'created_at']
    search_fields = ['nome', 'telefone', 'email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['nome']
    filter_horizontal = ('tags',)

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'telefone', 'email', 'ativo'),
            'description': 'Dados principais do contato'
        }),
        ('Detalhes', {
            'fields': ('origem', 'observacoes'),
            'classes': ('collapse',),
        }),
        ('Relacionamentos', {
            'fields': ('company', 'tags'),
        }),
        ('Metadados', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def ativo_badge(self, obj):
        if obj.ativo:
            return format_html('<span style="color: green; font-weight: bold;">✓ Ativo</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Inativo</span>')
    ativo_badge.short_description = "Status"
    ativo_badge.admin_order_field = "ativo"

    def company_info(self, obj):
        if obj.company:
            return format_html(
                '<div style="line-height: 1.2;">'
                '<strong>{}</strong><br>'
                '<small style="color: #666;">ID: {}</small>'
                '</div>',
                obj.company.name,
                obj.company.id
            )
        return "❌ Sem empresa"
    company_info.short_description = 'Empresa'
    company_info.admin_order_field = 'company__name'

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('company').prefetch_related('tags')
        if not request.user.is_superuser and hasattr(request.user, 'company'):
            if not request.user.is_master_user():
                qs = qs.filter(company=request.user.company)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "company":
            if not request.user.is_superuser and hasattr(request.user, 'company'):
                if not request.user.is_master_user():
                    kwargs["queryset"] = Company.objects.filter(id=request.user.company.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class CampaignAdmin(admin.ModelAdmin):
    list_display = ['nome', 'company_info', 'ativo_badge', 'total_envios', 'created_by', 'created_at']
    list_filter = ['ativo', 'company', 'created_at']
    search_fields = ['nome']
    readonly_fields = ['id', 'created_at', 'updated_at', 'created_by']
    ordering = ['-created_at']

    fieldsets = (
        ('Informações da Campanha', {
            'fields': ('nome', 'texto', 'ativo'),
            'description': 'Dados principais da campanha'
        }),
        ('Relacionamentos', {
            'fields': ('company',),
        }),
        ('Metadados', {
            'fields': ('id', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def ativo_badge(self, obj):
        if obj.ativo:
            return format_html('<span style="color: green; font-weight: bold;">✓ Ativo</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Inativo</span>')
    ativo_badge.short_description = "Status"
    ativo_badge.admin_order_field = "ativo"

    def company_info(self, obj):
        if obj.company:
            return format_html(
                '<div style="line-height: 1.2;">'
                '<strong>{}</strong><br>'
                '<small style="color: #666;">{}</small>'
                '</div>',
                obj.company.name,
                obj.company.slug
            )
        return "❌ Sem empresa"
    company_info.short_description = 'Empresa'
    company_info.admin_order_field = 'company__name'

    def total_envios(self, obj):
        count = obj.envios.count()
        if count > 0:
            return format_html('<span style="color: blue; font-weight: bold;">{} envios</span>', count)
        return format_html('<span style="color: #666;">Nenhum envio</span>')
    total_envios.short_description = 'Total de Envios'

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('company', 'created_by')
        if not request.user.is_superuser and hasattr(request.user, 'company'):
            if not request.user.is_master_user():
                qs = qs.filter(company=request.user.company)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "company":
            if not request.user.is_superuser and hasattr(request.user, 'company'):
                if not request.user.is_master_user():
                    kwargs["queryset"] = Company.objects.filter(id=request.user.company.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:  # Novo objeto
            obj.created_by = request.user
            obj.company = request.user.company
        super().save_model(request, obj, form, change)


class MessageLogInline(admin.TabularInline):
    model = MessageLog
    extra = 0
    readonly_fields = ['telefone', 'texto_enviado', 'status', 'response_api', 'erro_mensagem', 'created_at', 'enviado_em']
    can_delete = False


class MessageAdmin(admin.ModelAdmin):
    list_display = ['nome', 'campanha', 'status_badge', 'total_contatos', 'total_enviados', 'total_erros', 'created_by', 'created_at']
    list_filter = ['status', 'company', 'campanha', 'created_at']
    search_fields = ['nome', 'campanha__nome']
    readonly_fields = ['id', 'created_at', 'updated_at', 'created_by', 'total_contatos', 'total_enviados', 'total_erros']
    ordering = ['-created_at']
    filter_horizontal = ('contatos',)
    inlines = [MessageLogInline]

    fieldsets = (
        ('Informações do Envio', {
            'fields': ('nome', 'campanha', 'status'),
            'description': 'Dados principais do envio'
        }),
        ('Configurações de Envio', {
            'fields': ('timeout_envio', 'data_agendamento'),
        }),
        ('Seleção de Contatos', {
            'fields': ('contatos',),
            'classes': ('collapse',),
        }),
        ('Estatísticas', {
            'fields': ('total_contatos', 'total_enviados', 'total_erros'),
            'classes': ('collapse',),
        }),
        ('Relacionamentos', {
            'fields': ('company',),
        }),
        ('Metadados', {
            'fields': ('id', 'created_by', 'created_at', 'updated_at', 'data_envio_iniciado', 'data_envio_finalizado'),
            'classes': ('collapse',),
        }),
    )

    def status_badge(self, obj):
        colors = {
            'rascunho': '#6c757d',     # cinza
            'pendente': '#ffc107',     # amarelo
            'enviando': '#17a2b8',     # azul
            'enviada': '#28a745',      # verde
            'erro': '#dc3545',         # vermelho
            'cancelada': '#6f42c1',    # roxo
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('company', 'created_by', 'campanha')
        if not request.user.is_superuser and hasattr(request.user, 'company'):
            if not request.user.is_master_user():
                qs = qs.filter(company=request.user.company)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "company":
            if not request.user.is_superuser and hasattr(request.user, 'company'):
                if not request.user.is_master_user():
                    kwargs["queryset"] = Company.objects.filter(id=request.user.company.id)
        elif db_field.name == "campanha":
            if not request.user.is_superuser and hasattr(request.user, 'company'):
                if not request.user.is_master_user():
                    kwargs["queryset"] = Campaign.objects.filter(company=request.user.company)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "contatos":
            if not request.user.is_superuser and hasattr(request.user, 'company'):
                if not request.user.is_master_user():
                    kwargs["queryset"] = Contact.objects.filter(company=request.user.company)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:  # Novo objeto
            obj.created_by = request.user
            obj.company = request.user.company
        super().save_model(request, obj, form, change)


class MessageLogAdmin(admin.ModelAdmin):
    list_display = ['message_info', 'contato', 'telefone', 'status_badge', 'created_at', 'enviado_em']
    list_filter = ['status', 'created_at']
    search_fields = ['contato__nome', 'telefone', 'message__nome']
    readonly_fields = ['id', 'message', 'contato', 'telefone', 'texto_enviado', 'response_api', 'created_at', 'enviado_em']
    ordering = ['-created_at']

    fieldsets = (
        ('Informações do Envio', {
            'fields': ('message', 'contato', 'telefone', 'status'),
        }),
        ('Conteúdo', {
            'fields': ('texto_enviado',),
            'classes': ('collapse',),
        }),
        ('Resposta da API', {
            'fields': ('response_api', 'erro_mensagem'),
            'classes': ('collapse',),
        }),
        ('Metadados', {
            'fields': ('id', 'created_at', 'enviado_em'),
            'classes': ('collapse',),
        }),
    )

    def message_info(self, obj):
        return format_html(
            '<div style="line-height: 1.2;">'
            '<strong>{}</strong><br>'
            '<small style="color: #666;">{}</small>'
            '</div>',
            obj.message.nome,
            obj.message.campanha.nome
        )
    message_info.short_description = 'Mensagem'
    message_info.admin_order_field = 'message__nome'

    def status_badge(self, obj):
        colors = {
            'pendente': '#ffc107',     # amarelo
            'enviado': '#28a745',      # verde
            'erro': '#dc3545',         # vermelho
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('message__company', 'contato')
        if not request.user.is_superuser and hasattr(request.user, 'company'):
            if not request.user.is_master_user():
                qs = qs.filter(message__company=request.user.company)
        return qs

    def has_add_permission(self, request):
        return False  # Logs são criados automaticamente


# Registrar no admin
admin.site.register(Tag, TagAdmin)
admin.site.register(Contact, ContactAdmin)
admin.site.register(Campaign, CampaignAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(MessageLog, MessageLogAdmin)
