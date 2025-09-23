# accounts/context_processors.py
def company_context(request):
    """
    Context processor para disponibilizar informações da empresa nos templates
    """
    context = {
        'current_company': getattr(request, 'current_company', None),
        'is_master_request': getattr(request, 'is_master_request', False),
    }
    
    if request.user.is_authenticated and hasattr(request.user, 'company'):
        context.update({
            'user_company': request.user.company,
            'is_master_user': request.user.is_master_user(),
            'accessible_companies': request.user.get_accessible_companies(),
        })
    
    return context