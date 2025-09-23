# accounts/decorators.py
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

def company_required(view_func):
    """
    Decorator que garante que o usuário pertence a uma empresa ativa
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request.user, 'company') or not request.user.company.is_active:
            raise PermissionDenied("Usuário deve pertencer a uma empresa ativa.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def master_company_required(view_func):
    """
    Decorator que permite acesso apenas para usuários da empresa master
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("Usuário deve estar autenticado.")
        if not request.user.is_master_user():
            raise PermissionDenied("Acesso restrito à empresa master.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def company_access_required(company_slug):
    """
    Decorator que verifica se o usuário pode acessar uma empresa específica
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Usuário deve estar autenticado.")
            
            try:
                company = Company.objects.get(slug=company_slug, is_active=True)
                if not request.user.can_access_company(company):
                    raise PermissionDenied(f"Acesso negado à empresa {company.name}.")
                
                # Adiciona a empresa ao request para uso na view
                request.target_company = company
                return view_func(request, *args, **kwargs)
            except Company.DoesNotExist:
                raise Http404("Empresa não encontrada.")
        return _wrapped_view
    return decorator