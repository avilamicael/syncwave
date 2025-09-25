from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def processar_para_contato(campanha, contato):
    """
    Processa o texto da campanha substituindo variáveis pelo contato específico
    """
    if not campanha or not contato:
        return ""
    
    return campanha.processar_texto_para_contato(contato)


@register.filter
def mul(value, arg):
    """Multiplica dois valores"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def div(value, arg):
    """Divide dois valores"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def sub(value, arg):
    """Subtrai dois valores"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0


@register.simple_tag
def get_preview_with_contact(campanha, contato):
    """
    Template tag para gerar prévia da campanha com contato específico
    """
    if not campanha or not contato:
        return ""
    
    return campanha.processar_texto_para_contato(contato)
