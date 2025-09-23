# accounts/admin.py
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.db import models
from .models import Company, CustomUser, CompanyPermission


class CustomUserCreationForm(UserCreationForm):
    """Formulário customizado para criação de usuários"""
    
    # Campos obrigatórios para o cadastro
    first_name = forms.CharField(max_length=150, required=True, label="Nome")
    last_name = forms.CharField(max_length=150, required=True, label="Sobrenome")
    email = forms.EmailField(required=True, label="E-mail")
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(is_active=True),
        required=True,
        label="Empresa",
        help_text="Selecione a empresa à qual o usuário pertencerá"
    )
    role = forms.ChoiceField(
        choices=CustomUser.USER_ROLES,
        required=True,
        initial='employee',
        label="Cargo/Função"
    )
    department = forms.CharField(
        max_length=100, 
        required=False, 
        label="Departamento",
        help_text="Ex: Vendas, Financeiro, TI, etc."
    )
    phone = forms.CharField(
        max_length=20, 
        required=False, 
        label="Telefone",
        help_text="Ex: (48) 99999-9999"
    )
    
    # Permissões especiais
    is_staff = forms.BooleanField(
        required=False,
        label="Acesso à administração",
        help_text="Permite que o usuário acesse o painel administrativo"
    )
    
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'company', 
                 'role', 'department', 'phone', 'is_staff')
    
    def __init__(self, *args, **kwargs):
        # Pega o request do contexto se disponível
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Filtra empresas baseado no usuário logado
        if self.request and hasattr(self.request.user, 'company'):
            if not self.request.user.is_superuser and not self.request.user.is_master_user():
                # Usuários não-master só podem criar usuários na própria empresa
                self.fields['company'].queryset = Company.objects.filter(
                    id=self.request.user.company.id
                )
                self.fields['company'].initial = self.request.user.company
                self.fields['company'].widget.attrs['readonly'] = True
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Já existe um usuário com este e-mail.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.company = self.cleaned_data['company']
        user.role = self.cleaned_data['role']
        user.department = self.cleaned_data.get('department', '')
        user.phone = self.cleaned_data.get('phone', '')
        
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """Formulário customizado para edição de usuários"""
    
    class Meta:
        model = CustomUser
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Filtra empresas baseado no usuário logado
        if self.request and hasattr(self.request.user, 'company'):
            if not self.request.user.is_superuser and not self.request.user.is_master_user():
                self.fields['company'].queryset = Company.objects.filter(
                    id=self.request.user.company.id
                )


class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'company_type', 'is_active', 'users_count', 'created_at']
    list_filter = ['company_type', 'is_active', 'created_at']
    search_fields = ['name', 'slug', 'cnpj', 'email']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'slug', 'company_type', 'is_active'),
            'description': 'Informações principais da empresa'
        }),
        ('Contato', {
            'fields': ('email', 'phone', 'cnpj'),
            'description': 'Dados de contato e identificação'
        }),
        ('Endereço', {
            'fields': ('address', 'city', 'state', 'zip_code'),
            'classes': ('collapse',),
            'description': 'Endereço completo da empresa'
        }),
        ('Metadados', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def users_count(self, obj):
        count = obj.users.count()
        url = f'/admin/accounts/customuser/?company__id__exact={obj.id}'
        return format_html(
            '<a href="{}" style="color: {}; text-decoration: none;">'
            '<strong>{} usuário{}</strong></a>',
            url,
            'green' if count > 0 else 'red',
            count,
            's' if count != 1 else ''
        )
    users_count.short_description = 'Usuários'
    users_count.admin_order_field = 'users__count'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Filtra empresas baseado no usuário logado
        if not request.user.is_superuser and hasattr(request.user, 'company'):
            if not request.user.is_master_user():
                qs = qs.filter(id=request.user.company.id)
        return qs.annotate(users_count=models.Count('users'))
    
    def has_add_permission(self, request):
        # Apenas usuários master ou superuser podem criar empresas
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'company') and request.user.is_master_user():
            return True
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Apenas usuários master ou superuser podem deletar empresas
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'company') and request.user.is_master_user():
            # Não pode deletar a própria empresa master
            if obj and obj.company_type == 'master':
                return False
            return True
        return False


class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = [
        'username', 'get_full_name', 'email', 'company_info', 
        'role_badge', 'is_active_badge', 'is_staff', 'last_login'
    ]
    list_display_links = ['username', 'get_full_name']
    list_filter = [
        'is_active', 'is_staff', 'is_superuser', 'company__company_type', 
        'role', 'can_access_all_companies', 'date_joined'
    ]
    search_fields = ['username', 'email', 'first_name', 'last_name', 'company__name']
    ordering = ['-created_at']
    list_per_page = 25
    
    # Fieldsets para edição
    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('username', 'first_name', 'last_name', 'email', 'phone'),
            'description': 'Dados pessoais do usuário'
        }),
        ('Informações da Empresa', {
            'fields': ('company', 'role', 'department'),
            'description': 'Vinculação com a empresa e cargo'
        }),
        ('Permissões Básicas', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
            'description': 'Controle básico de acesso'
        }),
        ('Permissões Avançadas', {
            'fields': ('can_access_all_companies', 'groups', 'user_permissions'),
            'classes': ('collapse',),
            'description': 'Permissões especiais e grupos'
        }),
        ('Datas Importantes', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Fieldsets para criação (mais simples)
    add_fieldsets = (
        ('Dados de Acesso', {
            'fields': ('username', 'password1', 'password2'),
            'description': 'Defina o nome de usuário e senha'
        }),
        ('Informações Pessoais', {
            'fields': ('first_name', 'last_name', 'email', 'phone'),
            'description': 'Dados pessoais obrigatórios'
        }),
        ('Vinculação com Empresa', {
            'fields': ('company', 'role', 'department'),
            'description': 'Selecione a empresa e cargo do usuário'
        }),
        ('Permissões', {
            'fields': ('is_staff',),
            'description': 'Marque se o usuário deve ter acesso ao admin'
        }),
    )
    
    readonly_fields = ['last_login', 'date_joined', 'created_at', 'updated_at']
    
    def company_info(self, obj):
        if obj.company:
            company_type = "🏢 Master" if obj.company.company_type == 'master' else "🏪 Cliente"
            return format_html(
                '<div style="line-height: 1.2;">'
                '<strong>{}</strong><br>'
                '<small style="color: #666;">{}</small>'
                '</div>',
                obj.company.name,
                company_type
            )
        return "❌ Sem empresa"
    company_info.short_description = 'Empresa'
    company_info.admin_order_field = 'company__name'
    
    def role_badge(self, obj):
        colors = {
            'admin': '#dc3545',      # vermelho
            'manager': '#fd7e14',    # laranja  
            'employee': '#28a745',   # verde
            'viewer': '#6c757d',     # cinza
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_role_display()
        )
    role_badge.short_description = 'Cargo'
    role_badge.admin_order_field = 'role'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Ativo</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Inativo</span>'
        )
    is_active_badge.short_description = 'Status'
    is_active_badge.admin_order_field = 'is_active'
    
    def get_form(self, request, obj=None, **kwargs):
        # Passa o request para o formulário
        form = super().get_form(request, obj, **kwargs)
        form.request = request
        return form
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('company')
        
        # Filtra usuários baseado na empresa do usuário logado
        if not request.user.is_superuser and hasattr(request.user, 'company'):
            if not request.user.is_master_user():
                qs = qs.filter(company=request.user.company)
        
        return qs
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "company":
            # Filtra empresas baseado no usuário logado
            if not request.user.is_superuser and hasattr(request.user, 'company'):
                if not request.user.is_master_user():
                    kwargs["queryset"] = Company.objects.filter(id=request.user.company.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        # Define automaticamente can_access_all_companies para usuários master
        if obj.company and obj.company.is_master_company():
            obj.can_access_all_companies = True
        super().save_model(request, obj, form, change)


class CompanyPermissionAdmin(admin.ModelAdmin):
    list_display = ['company_granted', 'company_owner', 'permission_type', 'is_active', 'created_by', 'created_at']
    list_filter = ['permission_type', 'is_active', 'created_at']
    search_fields = ['company_owner__name', 'company_granted__name', 'permission_type']
    readonly_fields = ['created_at', 'created_by']
    
    fieldsets = (
        ('Configuração da Permissão', {
            'fields': ('company_owner', 'company_granted', 'permission_type', 'is_active'),
            'description': 'Configure qual empresa pode acessar dados de qual empresa'
        }),
        ('Metadados', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'company_owner', 'company_granted', 'created_by'
        )
        
        # Filtrar permissões baseado na empresa do usuário
        if not request.user.is_superuser and hasattr(request.user, 'company'):
            if not request.user.is_master_user():
                # Usuários não-master só veem permissões relacionadas à sua empresa
                qs = qs.filter(
                    models.Q(company_owner=request.user.company) |
                    models.Q(company_granted=request.user.company)
                )
        
        return qs
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Filtra empresas baseado no usuário logado
        if db_field.name in ["company_owner", "company_granted"]:
            if not request.user.is_superuser and hasattr(request.user, 'company'):
                if not request.user.is_master_user():
                    # Limita às empresas que o usuário pode gerenciar
                    kwargs["queryset"] = Company.objects.filter(
                        models.Q(id=request.user.company.id) |
                        models.Q(permissions_granted__company_granted=request.user.company)
                    ).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        if not change:  # Novo objeto
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request):
        # Apenas usuários master ou administradores de empresa podem criar permissões
        if request.user.is_superuser:
            return True
        if hasattr(request.user, 'role') and request.user.role in ['admin']:
            return True
        return False


# Registrar os modelos no admin
admin.site.register(Company, CompanyAdmin)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(CompanyPermission, CompanyPermissionAdmin)

# Personalização do Django Admin
admin.site.site_header = "SyncWave - Administração"
admin.site.site_title = "SyncWave Admin"
admin.site.index_title = "Painel de Controle"

# Remove o link "Ver site" se não tiver frontend ainda
admin.site.site_url = None