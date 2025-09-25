from django import forms
from django.core.exceptions import ValidationError
from .models import Tag, Contact


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
