from django import forms
from django.core.exceptions import ValidationError
from .models import Tag, Contact, Campaign, Message


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['nome', 'cor']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: VIP, Black Friday, Inadimplente'
            }),
            'cor': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control'
            })
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].label = 'Nome da Tag'
        self.fields['cor'].label = 'Cor'


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['nome', 'telefone', 'email', 'tags', 'observacoes', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: João da Silva'
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+5548999999999'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'joao@email.com'
            }),
            'tags': forms.CheckboxSelectMultiple(),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações sobre o contato...'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # Filtra tags pela empresa
        if self.company:
            self.fields['tags'].queryset = Tag.objects.filter(company=self.company)
        
        # Labels
        self.fields['nome'].label = 'Nome'
        self.fields['telefone'].label = 'Telefone'
        self.fields['email'].label = 'Email (opcional)'
        self.fields['tags'].label = 'Tags'
        self.fields['observacoes'].label = 'Observações'
        self.fields['ativo'].label = 'Contato ativo'
        
        # Help texts
        self.fields['telefone'].help_text = 'Formato internacional: +5548999999999'
    
    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        if not telefone:
            return telefone
            
        # Remove caracteres especiais
        telefone_limpo = telefone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Só verifica duplicação se company estiver definida
        if self.company:
            # Verifica se já existe (exceto para o próprio objeto)
            existing = Contact.objects.filter(telefone=telefone_limpo, company=self.company)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError(f'Já existe um contato com o telefone {telefone_limpo} nesta empresa.')
        
        return telefone_limpo


class ContactImportForm(forms.Form):
    csv_file = forms.FileField(
        label='Arquivo CSV',
        widget=forms.FileInput(attrs={
            'class': 'custom-file-input',
            'accept': '.csv'
        }),
        help_text='Arquivo deve conter as colunas: nome, telefone, email (opcional), tags (opcional, separadas por vírgula)'
    )


# =============================================================================
# FORMULÁRIOS PARA CAMPANHAS
# =============================================================================

class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ['nome', 'texto', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Aniversário, Promoção Black Friday, Cobrança...'
            }),
            'texto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Olá {{nome}}! Temos uma oferta especial para você...'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].label = 'Nome da Campanha'
        self.fields['texto'].label = 'Texto da Mensagem'
        self.fields['ativo'].label = 'Campanha ativa'
        
        # Help texts
        self.fields['texto'].help_text = 'Use {{nome}} para incluir automaticamente o nome do contato'
        self.fields['nome'].help_text = 'Nome para identificar sua campanha'


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['nome', 'campanha', 'contatos', 'timeout_envio', 'data_agendamento']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Aniversariantes Janeiro 2024'
            }),
            'campanha': forms.Select(attrs={
                'class': 'form-control'
            }),
            'contatos': forms.CheckboxSelectMultiple(),
            'timeout_envio': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 60,
                'value': 2
            }),
            'data_agendamento': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }, format='%Y-%m-%dT%H:%M')
        }
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # Filtra campanhas e contatos pela empresa
        if self.company:
            self.fields['campanha'].queryset = Campaign.objects.filter(
                company=self.company, 
                ativo=True
            )
            self.fields['contatos'].queryset = Contact.objects.filter(
                company=self.company, 
                ativo=True
            )
        
        # Labels
        self.fields['nome'].label = 'Nome do Envio'
        self.fields['campanha'].label = 'Campanha'
        self.fields['contatos'].label = 'Selecionar Contatos'
        self.fields['timeout_envio'].label = 'Intervalo entre envios (segundos)'
        self.fields['data_agendamento'].label = 'Agendar para (opcional)'
        
        # Help texts
        self.fields['nome'].help_text = 'Nome para identificar este envio específico'
        self.fields['timeout_envio'].help_text = 'Tempo de espera entre cada envio (1 a 60 segundos)'
        self.fields['data_agendamento'].help_text = 'Deixe em branco para enviar imediatamente'
        self.fields['contatos'].help_text = 'Selecione os contatos que receberão a mensagem'
        
        # Formato correto da data para datetime-local
        if self.instance and self.instance.data_agendamento:
            # Converte para o formato datetime-local (YYYY-MM-DDTHH:MM)
            from django.utils import timezone
            local_time = timezone.localtime(self.instance.data_agendamento)
            self.fields['data_agendamento'].initial = local_time.strftime('%Y-%m-%dT%H:%M')
    
    def clean_contatos(self):
        contatos = self.cleaned_data.get('contatos')
        if not contatos or contatos.count() == 0:
            raise ValidationError('Selecione pelo menos um contato para envio.')
        return contatos


class MessageFilterForm(forms.Form):
    """
    Formulário para filtrar contatos rapidamente ao criar mensagens
    """
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        label="Filtrar por Tags"
    )
    
    status_contato = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('ativo', 'Apenas Ativos'),
            ('inativo', 'Apenas Inativos')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Status do Contato"
    )
    
    busca_nome = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nome...'
        }),
        label="Buscar por Nome"
    )
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if company:
            self.fields['tags'].queryset = Tag.objects.filter(company=company)


class PreviewMessageForm(forms.Form):
    """
    Formulário para prévia da mensagem antes do envio
    """
    campanha = forms.ModelChoiceField(
        queryset=Campaign.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Campanha"
    )
    
    contato_preview = forms.ModelChoiceField(
        queryset=Contact.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        label="Visualizar com contato"
    )
    
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        if company:
            self.fields['campanha'].queryset = Campaign.objects.filter(
                company=company, 
                ativo=True
            )
            self.fields['contato_preview'].queryset = Contact.objects.filter(
                company=company, 
                ativo=True
            )[:10]  # Primeiros 10 para performance
        
        self.fields['contato_preview'].help_text = 'Selecione um contato para ver como ficará a mensagem personalizada'
