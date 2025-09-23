# accounts/management/commands/create_master_company.py
from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import Company, CustomUser

class Command(BaseCommand):
    help = 'Cria a empresa master (SyncWave) e o usuário administrador'

    def add_arguments(self, parser):
        parser.add_argument('--name', type=str, default='SyncWave', help='Nome da empresa master')
        parser.add_argument('--slug', type=str, default='syncwave', help='Slug da empresa master')
        parser.add_argument('--email', type=str, required=True, help='Email da empresa master')
        parser.add_argument('--admin-username', type=str, required=True, help='Username do admin')
        parser.add_argument('--admin-email', type=str, required=True, help='Email do admin')
        parser.add_argument('--admin-password', type=str, required=True, help='Senha do admin')

    @transaction.atomic
    def handle(self, *args, **options):
        # Verifica se já existe uma empresa master
        if Company.objects.filter(company_type='master').exists():
            self.stdout.write(
                self.style.WARNING('Empresa master já existe!')
            )
            return

        # Cria a empresa master
        company = Company.objects.create(
            name=options['name'],
            slug=options['slug'],
            email=options['email'],
            company_type='master',
            is_active=True
        )

        # Cria o usuário administrador
        admin_user = CustomUser.objects.create_superuser(
            username=options['admin_username'],
            email=options['admin_email'],
            password=options['admin_password'],
            company=company,
            role='admin',
            can_access_all_companies=True
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Empresa master "{company.name}" criada com sucesso!\n'
                f'Usuário administrador "{admin_user.username}" criado com sucesso!'
            )
        )