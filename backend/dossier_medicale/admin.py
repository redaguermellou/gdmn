# dossier_medicale/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    DossierMedical, 
    MedicalAttachment, 
    DossierAuditLog, 
    PieceJointe
)
from user.models import User, Role

# ======================
# USER MANAGEMENT ADMIN
# ======================
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'permissions_count', 'user_count')
    filter_horizontal = ('permissions',)
    search_fields = ('name',)
    
    def permissions_count(self, obj):
        return obj.permissions.count()
    permissions_count.short_description = _('Permissions')
    
    def user_count(self, obj):
        return obj.user_set.count()
    user_count.short_description = _('Users')


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'get_employee_id', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'full_name', 'employee_id')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal Info'), {'fields': ('full_name', 'employee_id', 'role', 'last_login')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 
                      'groups', 'user_permissions'),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'employee_id', 'role', 'password1', 'password2',
                      'is_active', 'is_staff', 'is_superuser'),
        }),
    )
    
    def get_employee_id(self, obj):
        return obj.employee_id
    get_employee_id.short_description = 'Employee ID'


# ======================
# MEDICAL DOSSIER ADMIN
# ======================
class MedicalAttachmentInline(admin.TabularInline):
    model = MedicalAttachment
    extra = 1
    fields = ('type', 'name', 'file', 'is_approved', 'uploaded_at')
    readonly_fields = ('uploaded_at',)
    classes = ('collapse',)

class PieceJointeInline(admin.TabularInline):
    model = PieceJointe
    extra = 1
    fields = ('type', 'nom_fichier', 'chemin_storage', 'date_upload')
    readonly_fields = ('date_upload',)
    classes = ('collapse',)


@admin.register(DossierMedical)
class DossierMedicalAdmin(admin.ModelAdmin):
    list_display = ('reference', 'employer', 'department', 'status_badge', 'created_by')
    list_filter = ('status', 'department', 'is_confidential', 'employer')
    search_fields = ('reference', 'employer__employee_id', 'doctor', 'employer__email')
    inlines = [MedicalAttachmentInline, PieceJointeInline]
    list_select_related = ('employer', 'created_by')  # Only existing fields
    
    def display_employer(self, obj):
        # Access employer information
        if obj.employer:
            # Show full name and employee ID if available
            full_name = obj.employer.get_full_name() if hasattr(obj.employer, 'get_full_name') else str(obj.employer)
            emp_id = getattr(obj.employer, 'employee_id', None)
            if emp_id:
                return f"{full_name} ({emp_id})"
            return full_name
        return "Not assigned"
    display_employer.short_description = 'Assigned Employer'
    display_employer.admin_order_field = 'employer__employee_id'
    
    def status_badge(self, obj):
        color = {
            'DRAFT': 'gray',
            'SUBMITTED': 'blue', 
            'UNDER_REVIEW': 'orange',
            'APPROVED': 'green',
            'REJECTED': 'red',
            'ARCHIVED': 'black'
        }.get(obj.status, 'gray')
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 3px">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('Status')
    
    def get_readonly_fields(self, request, obj=None):
        readonly = ['created_by']
        if obj:  # When editing existing instance
            readonly.append('employer')
        return readonly
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "employer":
            # Usually, only NORMAL users are employers
            kwargs["queryset"] = User.objects.filter(role__name='NORMAL')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(MedicalAttachment)
class MedicalAttachmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'dossier_link', 'is_approved')
    list_filter = ('type', 'is_approved')
    
    def dossier_link(self, obj):
        url = reverse('admin:dossier_medicale_dossiermedical_change', args=[obj.dossier.id])
        return format_html('<a href="{}">{}</a>', url, obj.dossier.reference)
    dossier_link.short_description = _('Dossier')

@admin.register(PieceJointe)
class PieceJointeAdmin(admin.ModelAdmin):
    list_display = ('nom_fichier', 'type', 'dossier_link', 'date_upload')
    
    def dossier_link(self, obj):
        url = reverse('admin:dossier_medicale_dossiermedical_change', args=[obj.dossier.id])
        return format_html('<a href="{}">{}</a>', url, obj.dossier.reference)
    dossier_link.short_description = _('Dossier')

@admin.register(DossierAuditLog)
class DossierAuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'dossier_link', 'user', 'timestamp')
    readonly_fields = ('action', 'dossier', 'user', 'timestamp', 'details')
    
    def dossier_link(self, obj):
        url = reverse('admin:dossier_medicale_dossiermedical_change', args=[obj.dossier.id])
        return format_html('<a href="{}">{}</a>', url, obj.dossier.reference)
    dossier_link.short_description = _('Dossier')

# Admin site configuration
admin.site.site_header = _("Medical Dossier Administration")
admin.site.site_title = _("Dossier Medical System")
admin.site.index_title = _("Welcome to Medical Dossier Admin")