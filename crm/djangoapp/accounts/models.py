# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
import uuid

class Company(models.Model):
    """
    Modelo para representar empresas no sistema
    """
    COMPANY_TYPES = [
        ('master', 'Master'),
        ('client', 'Client'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nome da Empresa")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Slug")
    cnpj = models.CharField(max_length=18, unique=True, null=True, blank=True, verbose_name="CNPJ")
    email = models.EmailField(verbose_name="E-mail da Empresa")
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Telefone")
    
    # Endereço
    address = models.CharField(max_length=255, null=True, blank=True, verbose_name="Endereço")
    city = models.CharField(max_length=100, null=True, blank=True, verbose_name="Cidade")
    state = models.CharField(max_length=100, null=True, blank=True, verbose_name="Estado")
    zip_code = models.CharField(max_length=10, null=True, blank=True, verbose_name="CEP")
    
    # Configurações
    company_type = models.CharField(
        max_length=20, 
        choices=COMPANY_TYPES, 
        default='client',
        verbose_name="Tipo da Empresa"
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def is_master_company(self):
        """Verifica se é a empresa master"""
        return self.company_type == 'master'
    
    def clean(self):
        """Validações customizadas"""
        # Garantir que só existe uma empresa master
        if self.company_type == 'master':
            existing_master = Company.objects.filter(company_type='master').exclude(pk=self.pk)
            if existing_master.exists():
                raise ValidationError("Já existe uma empresa master no sistema.")
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CustomUser(AbstractUser):
    """
    Usuário customizado vinculado a uma empresa
    """
    USER_ROLES = [
        ('admin', 'Administrador'),
        ('manager', 'Gerente'),
        ('employee', 'Funcionário'),
        ('viewer', 'Visualizador'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='users',
        verbose_name="Empresa"
    )
    role = models.CharField(
        max_length=20, 
        choices=USER_ROLES, 
        default='employee',
        verbose_name="Cargo/Função"
    )
    
    # Campos adicionais
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Telefone")
    department = models.CharField(max_length=100, null=True, blank=True, verbose_name="Departamento")
    
    # Configurações de acesso
    can_access_all_companies = models.BooleanField(
        default=False, 
        verbose_name="Pode acessar todas as empresas"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.company.name})"
    
    def is_master_user(self):
        """Verifica se o usuário pertence à empresa master"""
        return self.company.is_master_company()
    
    def can_access_company(self, company):
        """Verifica se o usuário pode acessar uma empresa específica"""
        if self.is_master_user() or self.can_access_all_companies:
            return True
        return self.company == company
    
    def get_accessible_companies(self):
        """Retorna as empresas que o usuário pode acessar"""
        if self.is_master_user() or self.can_access_all_companies:
            return Company.objects.filter(is_active=True)
        return Company.objects.filter(id=self.company.id, is_active=True)
    
    def save(self, *args, **kwargs):
        # Se o usuário pertence à empresa master, automaticamente pode acessar todas
        if self.company and self.company.is_master_company():
            self.can_access_all_companies = True
        super().save(*args, **kwargs)


class CompanyPermission(models.Model):
    """
    Modelo para gerenciar permissões específicas entre empresas
    Útil para casos onde uma empresa client precisa acessar dados de outra
    """
    company_owner = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='permissions_granted',
        verbose_name="Empresa Proprietária"
    )
    company_granted = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='permissions_received',
        verbose_name="Empresa com Acesso"
    )
    permission_type = models.CharField(
        max_length=50, 
        verbose_name="Tipo de Permissão",
        help_text="Ex: read, write, admin"
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        verbose_name="Criado por"
    )
    
    class Meta:
        verbose_name = "Permissão entre Empresas"
        verbose_name_plural = "Permissões entre Empresas"
        unique_together = ['company_owner', 'company_granted', 'permission_type']
    
    def __str__(self):
        return f"{self.company_granted.name} -> {self.company_owner.name} ({self.permission_type})"