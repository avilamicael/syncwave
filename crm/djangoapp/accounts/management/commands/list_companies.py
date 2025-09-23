# accounts/management/commands/list_companies.py
from django.core.management.base import BaseCommand
from accounts.models import Company

class Command(BaseCommand):
    help = 'Lista todas as empresas do sistema'

    def handle(self, *args, **options):
        companies = Company.objects.all().order_by('company_type', 'name')
        
        if not companies.exists():
            self.stdout.write(
                self.style.WARNING('Nenhuma empresa encontrada.')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Encontradas {companies.count()} empresas:\n')
        )

        for company in companies:
            users_count = company.users.count()
            type_display = 'MASTER' if company.company_type == 'master' else 'CLIENTE'
            status = 'ATIVA' if company.is_active else 'INATIVA'
            
            self.stdout.write(
                f'• {company.name} ({type_display}) - {status}\n'
                f'  Slug: {company.slug}\n'
                f'  Email: {company.email}\n'
                f'  Usuários: {users_count}\n'
                f'  Criada em: {company.created_at.strftime("%d/%m/%Y %H:%M")}\n'
            )