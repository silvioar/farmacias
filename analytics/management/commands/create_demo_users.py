from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Creates demo users: one admin and one client'

    def handle(self, *args, **kwargs):
        # Create Admin
        if not User.objects.filter(username='admin_bioderma').exists():
            User.objects.create_superuser('admin_bioderma', 'admin@bioderma.com', 'Admin123!')
            self.stdout.write(self.style.SUCCESS('Successfully created admin user: admin_bioderma / Admin123!'))
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists'))

        # Create Client
        if not User.objects.filter(username='cliente_bioderma').exists():
            user = User.objects.create_user('cliente_bioderma', 'cliente@bioderma.com', 'Cliente123!')
            self.stdout.write(self.style.SUCCESS('Successfully created client user: cliente_bioderma / Cliente123!'))
        else:
            self.stdout.write(self.style.WARNING('Client user already exists'))
