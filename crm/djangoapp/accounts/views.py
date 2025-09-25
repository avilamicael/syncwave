from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.urls import reverse_lazy

class CollaboratorLoginView(LoginView):
    """View customizada para login de colaboradores"""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """Redireciona para o dashboard após login bem-sucedido"""
        return reverse_lazy('wpp:dashboard')
    
    def form_invalid(self, form):
        """Customiza mensagem de erro"""
        messages.error(self.request, 'Usuário ou senha incorretos.')
        return super().form_invalid(form)


class CollaboratorLogoutView(LogoutView):
    """View customizada para logout"""
    next_page = reverse_lazy('accounts:login')
    
    def dispatch(self, request, *args, **kwargs):
        """Adiciona mensagem de logout"""
        messages.success(request, 'Você foi desconectado com sucesso.')
        return super().dispatch(request, *args, **kwargs)
