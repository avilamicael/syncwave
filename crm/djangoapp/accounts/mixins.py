from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

class CompanyRequiredMixin(LoginRequiredMixin):
    """Mixin que garante que o usuário tem uma empresa associada"""
    
    def dispatch(self, request, *args, **kwargs):
        # Primeiro verifica se está autenticado (LoginRequiredMixin)
        response = super().dispatch(request, *args, **kwargs)
        if hasattr(response, 'status_code'):
            return response  # Retorna redirect do LoginRequiredMixin se necessário
            
        # Verifica se tem empresa associada
        if not hasattr(request.user, 'company') or not request.user.company:
            messages.error(request, 'Você precisa estar associado a uma empresa.')
            return redirect('accounts:login')
        return response
    
    def get_queryset(self):
        """Filtra objetos pela empresa do usuário"""
        if hasattr(super(), 'get_queryset'):
            return super().get_queryset().filter(company=self.request.user.company)
        return self.model.objects.filter(company=self.request.user.company)


class MasterCompanyRequiredMixin(LoginRequiredMixin):
    """Mixin que permite acesso apenas a usuários da empresa master"""
    
    def dispatch(self, request, *args, **kwargs):
        # Primeiro verifica se está autenticado
        response = super().dispatch(request, *args, **kwargs)
        if hasattr(response, 'status_code'):
            return response
            
        # Verifica se é usuário master
        if not request.user.is_authenticated or not hasattr(request.user, 'is_master_user') or not request.user.is_master_user():
            messages.error(request, 'Acesso restrito à empresa master.')
            return redirect('accounts:login')
        return response
