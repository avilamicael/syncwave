# contacts/admin.py
from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.db import models

from .models import Contact, Tag
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


# Registrar no admin
admin.site.register(Tag, TagAdmin)
admin.site.register(Contact, ContactAdmin)
