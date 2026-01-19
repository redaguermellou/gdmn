from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class Role(models.Model):
    ROLE_CHOICES = [
        ('AGENT', 'Medical Agent'),
        ('CONTROLLER', 'Quality Controller'),
        ('ADMIN', 'System Admin'),
    ]
    
    name = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    permissions = models.ManyToManyField(Permission)
    
    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
    
    def __str__(self):
        return self.get_name_display()

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', Role.objects.get_or_create(name='ADMIN')[0])
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None

    email = models.EmailField(_('email address'), unique=True)
    full_name = models.CharField(_('full name'), max_length=255)
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    is_active = models.BooleanField(_('active'), default=True)
    last_login = models.DateTimeField(_('last login'), default=timezone.now)
    employee_id = models.CharField(
        _('employee ID'),
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text=_('Unique identifier for the employee in the organization')
    )
    department = models.CharField(
        _('department'),
        max_length=100,
        blank=True,
        null=True,
        help_text=_('Department the user belongs to')
    )
    # Add custom related_name for groups and user_permissions
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="custom_user_set",  # Changed from default 'user_set'
        related_query_name="custom_user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="custom_user_set",  # Changed from default 'user_set'
        related_query_name="custom_user",
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    objects = UserManager()
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
    
    def __str__(self):
        return f"{self.full_name} ({self.role})"
    
    def save(self, *args, **kwargs):
        if not self.pk:  
            if not hasattr(self, 'role'):
                self.role = Role.objects.get_or_create(name='AGENT')[0]
        super().save(*args, **kwargs)
    def get_full_name(self):
        return self.full_name
    
def has_role(self, role_name):
    return self.role.name == role_name

def can_review(self):
    return self.has_role('CONTROLLER') or self.has_role('ADMIN')

def can_approve(self):
    return self.has_role('ADMIN')