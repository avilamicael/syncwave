from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import uuid


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=50)
    cor = models.CharField(max_length=7, default='#6B7280')  # hex color para UI
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='tags')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('nome', 'company')  # Tag única por empresa
        ordering = ['nome']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
    
    def __str__(self):
        return f"{self.nome}"
    
    def save(self, *args, **kwargs):
        if self.nome:
            self.nome = self.nome.upper()
        super().save(*args, **kwargs)


class ContactManager(models.Manager):
    def ativos(self):
        """Retorna apenas contatos ativos"""
        return self.filter(ativo=True)
    
    def por_empresa(self, company):
        """Retorna contatos de uma empresa específica"""
        return self.filter(company=company)
    
    def com_tags(self, *tag_names):
        """Filtra contatos que possuem determinadas tags"""
        return self.filter(tags__nome__in=tag_names)


class Contact(models.Model):
    # Validators
    phone_validator = RegexValidator(
        regex=r'^\+[1-9]\d{1,14}$',
        message="Telefone deve estar no formato internacional: +5548999999999"
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=150)
    telefone = models.CharField(
        max_length=20, 
        validators=[phone_validator],
        help_text="Formato: +5548999999999"
    )
    email = models.EmailField(blank=True, null=True)  # Campo adicional útil
    ativo = models.BooleanField(default=True)
    
    # Campos de metadados úteis
    origem = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Como o contato foi adicionado (importação, manual, API, etc.)"
    )
    observacoes = models.TextField(blank=True)
    
    # Relacionamentos
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name='contatos')
    tags = models.ManyToManyField(Tag, blank=True, related_name='contatos')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Manager customizado
    objects = ContactManager()
    
    class Meta:
        unique_together = ('telefone', 'company')  # Telefone único por empresa
        ordering = ['nome']
        indexes = [
            models.Index(fields=['company', 'ativo']),  # Query comum
            models.Index(fields=['telefone']),  # Busca por telefone
            models.Index(fields=['created_at']),  # Ordenação por data
        ]
        verbose_name = 'Contato'
        verbose_name_plural = 'Contatos'
    
    def __str__(self):
        return f"{self.nome} - {self.telefone}"
    
    def clean(self):
        """Validação customizada"""
        # Remove espaços do telefone
        if self.telefone:
            self.telefone = self.telefone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Valida se telefone não existe na empresa (exceto para o próprio objeto)
        # Só faz esta validação se company existir
        if self.telefone and self.company_id:
            existing = Contact.objects.filter(
                telefone=self.telefone, 
                company=self.company
            ).exclude(pk=self.pk)
            
            if existing.exists():
                raise ValidationError(f"Já existe um contato com o telefone {self.telefone} nesta empresa.")
    
    def save(self, *args, **kwargs):
        """Override para executar validação somente quando company estiver definida"""
        # Remove espaços do telefone se houver
        if self.telefone:
            self.telefone = self.telefone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if self.nome:
            self.nome = self.nome.upper()
        if self.origem:
            self.origem = self.origem.upper()
        
        super().save(*args, **kwargs)
    
    @property
    def tags_nomes(self):
        """Retorna lista com nomes das tags"""
        return list(self.tags.values_list('nome', flat=True))
    
    def adicionar_tag(self, tag_nome):
        """Método helper para adicionar tag por nome"""
        tag, created = Tag.objects.get_or_create(
            nome=tag_nome,
            company=self.company
        )
        self.tags.add(tag)
        return tag
    
    def remover_tag(self, tag_nome):
        """Método helper para remover tag por nome"""
        try:
            tag = Tag.objects.get(nome=tag_nome, company=self.company)
            self.tags.remove(tag)
        except Tag.DoesNotExist:
            pass