from django.db import models
from django.utils import timezone
import uuid


class Campaign(models.Model):
    """
    Modelo simples para campanhas
    Usuário cria campanhas com nome e texto padrão para reutilizar
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(
        max_length=100, 
        verbose_name="Nome da Campanha",
        help_text="Ex: Aniversário, Promoção Black Friday, Cobrança, etc."
    )
    texto = models.TextField(
        verbose_name="Texto da Mensagem",
        help_text="Use {{nome}} para incluir o nome do contato automaticamente"
    )
    ativo = models.BooleanField(default=True, verbose_name="Campanha Ativa")
    
    # Relacionamentos
    company = models.ForeignKey(
        'accounts.Company', 
        on_delete=models.CASCADE, 
        related_name='campanhas',
        verbose_name="Empresa"
    )
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='campanhas_criadas',
        verbose_name="Criado por"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    class Meta:
        verbose_name = "Campanha"
        verbose_name_plural = "Campanhas"
        ordering = ['-created_at']
        unique_together = ('nome', 'company')  # Nome único por empresa
    
    def __str__(self):
        return self.nome
    
    def get_preview_texto(self, contact_name="[NOME DO CONTATO]"):
        """
        Mostra uma prévia do texto substituindo {{nome}} 
        """
        return self.texto.replace('{{nome}}', contact_name)
    
    def processar_texto_para_contato(self, contato):
        """
        Processa o texto substituindo as variáveis pelo contato específico
        """
        texto_processado = self.texto
        
        # Por enquanto só {{nome}}, mas pode expandir no futuro
        texto_processado = texto_processado.replace('{{nome}}', contato.nome)
        
        return texto_processado


class Message(models.Model):
    """
    Modelo para envios de mensagens
    Aqui o usuário seleciona a campanha, contatos e envia
    """
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('pendente', 'Pendente'),
        ('enviando', 'Enviando'),
        ('enviada', 'Enviada'),
        ('erro', 'Erro com Falhas'),
        ('cancelada', 'Cancelada'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(
        max_length=150, 
        verbose_name="Nome do Envio",
        help_text="Ex: Aniversariantes Janeiro 2024"
    )
    
    # Campanha selecionada
    campanha = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='envios',
        verbose_name="Campanha"
    )
    
    # Contatos selecionados para envio
    contatos = models.ManyToManyField(
        'Contact',
        related_name='mensagens_recebidas',
        verbose_name="Contatos Selecionados"
    )
    
    # Status e controle de envio
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='rascunho',
        verbose_name="Status"
    )
    
    # Estatísticas do envio
    total_contatos = models.IntegerField(default=0, verbose_name="Total de Contatos")
    total_enviados = models.IntegerField(default=0, verbose_name="Enviados com Sucesso")
    total_erros = models.IntegerField(default=0, verbose_name="Erros no Envio")
    
    # Agendamento (opcional)
    data_agendamento = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Agendar para",
        help_text="Deixe em branco para enviar imediatamente"
    )
    
    # Timeout entre envios (em segundos)
    timeout_envio = models.IntegerField(
        default=2,
        verbose_name="Timeout entre envios (segundos)",
        help_text="Intervalo entre cada envio para evitar spam"
    )
    
    # Relacionamentos
    company = models.ForeignKey(
        'accounts.Company',
        on_delete=models.CASCADE,
        related_name='mensagens_enviadas',
        verbose_name="Empresa"
    )
    created_by = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.CASCADE,
        related_name='mensagens_enviadas',
        verbose_name="Criado por"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    data_envio_iniciado = models.DateTimeField(null=True, blank=True, verbose_name="Envio Iniciado em")
    data_envio_finalizado = models.DateTimeField(null=True, blank=True, verbose_name="Envio Finalizado em")
    
    class Meta:
        verbose_name = "Envio de Mensagem"
        verbose_name_plural = "Envios de Mensagens"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.nome} - {self.campanha.nome}"
    
    def pode_enviar(self):
        """Verifica se o envio pode ser iniciado"""
        if self.status not in ['rascunho', 'pendente']:
            return False
        
        if self.total_contatos == 0:
            return False
        
        # Se tem agendamento, verifica se já chegou a hora
        if self.data_agendamento and self.data_agendamento > timezone.now():
            return False
        
        return True
    
    def atualizar_totais(self):
        """Atualiza os totais de contatos"""
        self.total_contatos = self.contatos.count()
        self.save(update_fields=['total_contatos'])
    
    def get_preview_primeira_mensagem(self):
        """Retorna prévia da primeira mensagem que será enviada"""
        primeiro_contato = self.contatos.first()
        if primeiro_contato:
            return self.campanha.processar_texto_para_contato(primeiro_contato)
        return self.campanha.get_preview_texto()


class MessageLog(models.Model):
    """
    Log individual de cada envio para auditoria
    """
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('enviado', 'Enviado'),
        ('erro', 'Erro'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relacionamentos
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name="Mensagem"
    )
    contato = models.ForeignKey(
        'Contact',
        on_delete=models.CASCADE,
        related_name='logs_mensagens',
        verbose_name="Contato"
    )
    
    # Dados do envio
    telefone = models.CharField(max_length=20, verbose_name="Telefone")
    texto_enviado = models.TextField(verbose_name="Texto Enviado")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name="Status"
    )
    
    # Resposta da API (quando integrar com Evolution)
    response_api = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Resposta da API"
    )
    erro_mensagem = models.TextField(
        blank=True,
        verbose_name="Mensagem de Erro"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    enviado_em = models.DateTimeField(null=True, blank=True, verbose_name="Enviado em")
    
    class Meta:
        verbose_name = "Log de Mensagem"
        verbose_name_plural = "Logs de Mensagens"
        ordering = ['-created_at']
        unique_together = ('message', 'contato')  # Evita duplicatas
    
    def __str__(self):
        return f"{self.contato.nome} - {self.get_status_display()}"
