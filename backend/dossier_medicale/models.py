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
        return self.get_status_color_by_status(self.status)

    @staticmethod
    def get_status_color_by_status(status):
        status_colors = {
            'DRAFT': 'secondary',
            'SUBMITTED': 'info',
            'UNDER_REVIEW': 'warning',
            'APPROVED': 'success',
            'REJECTED': 'danger',
            'ARCHIVED': 'dark',
        }
        return status_colors.get(status, 'light')

    @staticmethod
    def get_status_hex_by_status(status):
        status_hex = {
            'DRAFT': '#6c757d',
            'SUBMITTED': '#0dcaf0',
            'UNDER_REVIEW': '#ffc107',
            'APPROVED': '#198754',
            'REJECTED': '#dc3545',
            'ARCHIVED': '#212529',
        }
        return status_hex.get(status, '#f8f9fa')

class DossierMedical(MedicalDossierBase):
    PRIORITY_LEVELS = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
    ]

    CATEGORY_CHOICES = [
        ('GENERAL', 'Médecine Générale'),
        ('OPTIQUE', 'Optique'),
        ('CARDIOLOGIE', 'Cardiologie'),
        ('DENTAIRE', 'Dentaire'),
        ('ORL', 'ORL'),
        ('DERMATOLOGIE', 'Dermatologie'),
        ('AUTRE', 'Autre'),
    ]
    
    category = models.CharField(
        max_length=50, 
        choices=CATEGORY_CHOICES, 
        default='GENERAL',
        verbose_name="Catégorie de dossier"
    )
    department = models.CharField(max_length=100, blank=True)
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
            prefix = f'DM-{date_part}-'
            # Get all references for today and find the max suffix
            last_dossier = DossierMedical.objects.filter(
                reference__startswith=prefix
            ).only('reference').order_by('-reference').first()
            
            if last_dossier:
                try:
                    last_num = int(last_dossier.reference.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1
                
            self.reference = f"{prefix}{new_num:04d}"
        
        # Auto-fetch department from employer
        if self.employer and not self.department:
            self.department = self.employer.department or "Non spécifié"

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
        if user.role.name == 'AGENT':
            return self.created_by == user or self.employer == user
        return True # Admin/controller can usually view

    def user_can_edit(self, user):
        """Check if user can edit this dossier"""
        if user.role.name == 'ADMIN':
            return True
        if user.role.name == 'CONTROLLER':
            return True
        if user.role.name == 'AGENT':
            return self.created_by == user and self.status != 'APPROVED'
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

class PriseEnCharge(MedicalDossierBase):
    CARE_TYPES = [
        ('CONSULTATION', 'Consultation'),
        ('HOSPITALIZATION', 'Hospitalisation'),
        ('PHARMACY', 'Pharmacie'),
        ('LABORATORY', 'Laboratoire / Examens'),
        ('SURGERY', 'Chirurgie'),
        ('DENTAL', 'Soins Dentaires'),
        ('OPTICAL', 'Optique'),
        ('OTHER', 'Autre'),
    ]

    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pec_requests', verbose_name="Patient")
    institution = models.CharField(max_length=200, verbose_name="Établissement")
    care_type = models.CharField(max_length=50, choices=CARE_TYPES, default='CONSULTATION', verbose_name="Type de soin")
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Coût estimé")
    coverage_percentage = models.IntegerField(default=100, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name="Taux de couverture")
    start_date = models.DateField(default=timezone.now, verbose_name="Date de début")
    end_date = models.DateField(null=True, blank=True, verbose_name="Date de fin")
    diagnosis = models.TextField(verbose_name="Diagnostic")
    physician = models.CharField(max_length=100, verbose_name="Médecin traitant")
    department = models.CharField(max_length=100, blank=True, verbose_name="Département")
    comments = models.TextField(blank=True, verbose_name="Commentaires")

    class Meta:
        verbose_name = "Prise en Charge"
        verbose_name_plural = "Prises en Charge"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} - {self.patient.full_name} ({self.institution})"

    def save(self, *args, **kwargs):
        if not self.reference:
            date_part = timezone.now().strftime('%Y%m%d')
            prefix = f'PEC-{date_part}-'
            last_pec = PriseEnCharge.objects.filter(
                reference__startswith=prefix
            ).only('reference').order_by('-reference').first()
            
            if last_pec:
                try:
                    last_num = int(last_pec.reference.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1
            self.reference = f"{prefix}{new_num:04d}"
            
        # Auto-fetch department from patient
        if self.patient and not self.department:
            self.department = getattr(self.patient, 'department', "") or "Non spécifié"
            
        super().save(*args, **kwargs)

    def user_can_view(self, user):
        if user.role.name == 'AGENT':
            return self.created_by == user or self.patient == user
        return True

    def user_can_edit(self, user):
        if user.role.name in ['ADMIN', 'CONTROLLER']:
            return True
        if user.role.name == 'AGENT':
            return self.created_by == user and self.status != 'APPROVED'
        return False