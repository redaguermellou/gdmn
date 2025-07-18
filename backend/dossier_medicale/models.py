from django.db import models
from user.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class MedicalDossierBase(models.Model):
    """Abstract base class for all medical dossier functionality"""
    STATUS_CHOICES = [
        ('DRAFT', 'Brouillon'),
        ('SUBMITTED', 'Soumis'),
        ('UNDER_REVIEW', 'En révision'),
        ('APPROVED', 'Approuvé'),
        ('REJECTED', 'Rejeté'),
        ('ARCHIVED', 'Archivé'),
    ]
    
    reference = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_%(class)s')
    
    class Meta:
        abstract = True
    
    def get_status_color(self):
        status_colors = {
            'DRAFT': 'secondary',
            'SUBMITTED': 'info',
            'UNDER_REVIEW': 'warning',
            'APPROVED': 'success',
            'REJECTED': 'danger',
            'ARCHIVED': 'dark',
        }
        return status_colors.get(self.status, 'light')

class DossierMedical(MedicalDossierBase):
    PRIORITY_LEVELS = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
    ]
    
    department = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    doctor = models.CharField(max_length=100)
    diagnosis = models.TextField()
    treatment_plan = models.TextField()
    comments = models.TextField(blank=True)
    reason = models.CharField(max_length=255, null=True, blank=True)
    priority = models.IntegerField(
        choices=PRIORITY_LEVELS,
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    is_confidential = models.BooleanField(default=False)
    
    controller = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='controlled_dossiers',
        limit_choices_to={'role__name__in': ['CONTROLLER', 'ADMIN']}
    )
    
    employer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='managed_dossiers',
        verbose_name='Assigned Employer',
       
    )
    
    class Meta:
        verbose_name = "Dossier Médical"
        verbose_name_plural = "Dossiers Médicaux"
        ordering = ['-priority', '-created_at']
        permissions = [
            ('can_review', "Can review medical dossiers"),
            ('can_approve', "Can approve medical dossiers"),
            ('view_confidential', "Can view confidential dossiers"),
        ]
    def __str__(self):
        return f"{self.reference} - {self.employer} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        if not self.reference:
            # Generate reference: DM-YYYYMMDD-XXXX
            date_part = timezone.now().strftime('%Y%m%d')
            last_num = DossierMedical.objects.filter(
                reference__startswith=f'DM-{date_part}'
            ).count() + 1
            self.reference = f"DM-{date_part}-{last_num:04d}"
        
        # Automatically set controller if submitted by agent
        if self.status == 'SUBMITTED' and not self.controller:
            if self.created_by.role.name == 'AGENT':
                self.controller = User.objects.filter(
                    role__name='CONTROLLER'
                ).first()
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('dossier_medicale:detail', args=[str(self.id)])
    
    #new
    def user_can_view(self, user):
        """Check if user can view this dossier"""
        if user.role.name == 'NORMAL':
            return self.created_by == user
        return True  # Other roles can view all

    def user_can_edit(self, user):
        """Check if user can modify this dossier"""
        if user.role.name == 'AGENT':
            return True
        return False
class MedicalAttachment(models.Model):
    TYPE_CHOICES = [
        ('PRESCRIPTION', 'Ordonnance'),
        ('CERTIFICATE', 'Certificat médical'),
        ('SCAN', 'Radiographie/Scanner'),
        ('TEST', 'Résultat de test'),
        ('REPORT', 'Rapport médical'),
        ('OTHER', 'Autre'),
    ]
    
    dossier = models.ForeignKey(
        DossierMedical,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='medical_attachments/%Y/%m/%d/')
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    size_kb = models.IntegerField(editable=False)
    is_approved = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Medical Attachment"
        verbose_name_plural = "Medical Attachments"
        ordering = ['-uploaded_at']
    
    def save(self, *args, **kwargs):
        if self.file:
            self.size_kb = self.file.size // 1024
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"
    
    
    
   
class DossierAuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Création'),
        ('UPDATE', 'Modification'),
        ('STATUS_CHANGE', 'Changement de statut'),
        ('ATTACHMENT_ADD', 'Ajout de pièce jointe'),
        ('ATTACHMENT_REMOVE', 'Suppression de pièce jointe'),
        ('CONTROLLER_ASSIGN', 'Assignation de contrôleur'),
    ]
    
    dossier = models.ForeignKey(
        DossierMedical,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict)
    
    class Meta:
        verbose_name = "Dossier Audit Log"
        verbose_name_plural = "Dossier Audit Logs"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.dossier.reference} - {self.get_action_display()} by {self.user}"
    
    from django.db import models

class PieceJointe(models.Model):
   
    nom_fichier = models.CharField(max_length=255)
    chemin_storage = models.FileField(upload_to='pieces_jointes/')
    type = models.CharField(max_length=50)
    taille_ko = models.IntegerField()
    date_upload = models.DateTimeField(auto_now_add=True)
    dossier = models.ForeignKey('DossierMedical', on_delete=models.CASCADE,related_name='pieces_jointes')
    
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_pieces'
    )   
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.nom_fichier 
    def user_can_download(self, user):
        """Check if user can download this attachment"""
        return self.dossier.user_can_view(user)
    
def get_role_based_queryset(user):
    if user.role.name in ['ADMIN', 'CONTROLLER']:
        return DossierMedical.objects.all()
    elif user.role.name == 'AGENT':
        return DossierMedical.objects.filter(created_by=user)
    else:  # NORMAL user
        return DossierMedical.objects.filter(employer=user.employer)

def user_can_view(self, user):
    """Check if user can view this dossier"""
    if user.role.name == 'NORMAL':
        return self.employer == user.employer
    elif user.role.name == 'AGENT':
        return self.created_by == user or self.employer == user.employer
    return True  # Admin/controller can view all

def user_can_edit(self, user):
    """Check if user can modify this dossier"""
    if user.role.name in ['ADMIN', 'AGENT']:
        return self.status == 'DRAFT' and (
            user.role.name == 'ADMIN' or 
            self.created_by == user
        )
    return False