from django import forms
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from analytics.models import Client

class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    is_admin = forms.BooleanField(label='¿Es Administrador?', required=False, help_text="Acceso total al sistema y gestión de usuarios")
    permissions = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False,
        choices=[
            ('view_dashboard', 'Ver Dashboard'),
            ('view_visits', 'Ver Visitas'),
            ('view_routes', 'Ver Rutas'),
        ]
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        is_admin = self.cleaned_data.get('is_admin')
        if is_admin:
            user.is_superuser = True
            user.is_staff = True
        
        if commit:
            user.save()
            # Assign permissions
            content_type = ContentType.objects.get_for_model(Client)
            selected_perms = self.cleaned_data.get('permissions')
            if selected_perms:
                perms = Permission.objects.filter(content_type=content_type, codename__in=selected_perms)
                user.user_permissions.set(perms)
        return user

class CustomUserUpdateForm(forms.ModelForm):
    is_admin = forms.BooleanField(label='¿Es Administrador?', required=False, help_text="Acceso total al sistema y gestión de usuarios")
    permissions = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False,
        choices=[
            ('view_dashboard', 'Ver Dashboard'),
            ('view_visits', 'Ver Visitas'),
            ('view_routes', 'Ver Rutas'),
        ]
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Pre-select permissions
            content_type = ContentType.objects.get_for_model(Client)
            user_perms = self.instance.user_permissions.filter(content_type=content_type).values_list('codename', flat=True)
            self.fields['permissions'].initial = list(user_perms)
            self.fields['is_admin'].initial = self.instance.is_superuser

    def save(self, commit=True):
        user = super().save(commit=False)
        is_admin = self.cleaned_data.get('is_admin')
        user.is_superuser = bool(is_admin)
        user.is_staff = bool(is_admin)

        if commit:
            user.save()
            # Update permissions
            content_type = ContentType.objects.get_for_model(Client)
            selected_perms = self.cleaned_data.get('permissions')
            
            # Clear existing analytics perms
            analytics_perms = Permission.objects.filter(content_type=content_type)
            user.user_permissions.remove(*analytics_perms)
            
            if selected_perms:
                perms = Permission.objects.filter(content_type=content_type, codename__in=selected_perms)
                user.user_permissions.add(*perms)
        return user
