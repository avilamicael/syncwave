# accounts/utils.py
from django.db import models
from .models import Company

class CompanyQuerySet(models.QuerySet):
    """QuerySet personalizado para filtrar por empresa"""
    
    def for_user(self, user):
        """Filtra baseado no que o usuário pode acessar"""
        if user.is_master_user() or user.can_access_all_companies:
            return self
        return self.filter(company=user.company)
    
    def active_only(self):
        """Apenas empresas ativas"""
        return self.filter(is_active=True)


class CompanyManager(models.Manager):
    """Manager personalizado para modelos relacionados a empresas"""
    
    def get_queryset(self):
        return CompanyQuerySet(self.model, using=self._db)
    
    def for_user(self, user):
        return self.get_queryset().for_user(user)
    
    def active_only(self):
        return self.get_queryset().active_only()
