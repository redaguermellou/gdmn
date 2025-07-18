from django import forms
from .models import DossierMedical, MedicalAttachment, PieceJointe
from django.utils import timezone
from django.core.exceptions import ValidationError

from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import DossierMedical, User

class DossierForm(forms.ModelForm):
    attachments = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'multiple': True}),
        help_text="You can upload multiple files"
    )
    
    class Meta:
        model = DossierMedical
        fields = [
            'employer',
            'department',
            'start_date',
            'end_date',
            'doctor',
            'diagnosis',
            'status',
            'treatment_plan',
            'comments',
            'reason',
            'priority',
            'is_confidential',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'treatment_plan': forms.Textarea(attrs={'rows': 3}),
            'comments': forms.Textarea(attrs={'rows': 2}),
            'priority': forms.Select(choices=DossierMedical.PRIORITY_LEVELS),
        }
        help_texts = {
            'employee_id': "Employee ID or registration number",
            'is_confidential': "Check if this dossier contains sensitive information",
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Get the current user from kwargs
        super().__init__(*args, **kwargs)
        
        # Set initial values
        self.fields['start_date'].initial = timezone.now().date()
        self.fields['priority'].initial = 2
        
        # Customize employer queryset based on user role
        if user and hasattr(user, 'role'):
            if user.role.name in ['ADMIN', 'CONTROLLER']:
                # Show all active non-admin users for admin/controllers
                self.fields['employer'].queryset = User.objects.filter(
                    is_active=True
                ).exclude(
                    id=user.id
                ).order_by('username')
            else:
                # For other roles, show a more limited selection
                self.fields['employer'].queryset = User.objects.filter(
                    is_active=True,
                    role__name__in=['NORMAL', 'AGENT']  # Adjust as needed
                ).order_by('username')
        
        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            if field_name != 'is_confidential':
                field.widget.attrs.update({'class': 'form-control'})
            if isinstance(field, forms.BooleanField):
                field.widget.attrs.update({'class': 'form-check-input'})
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if end_date and start_date and end_date < start_date:
            raise ValidationError("End date cannot be before start date")
        
        return cleaned_data
from .models import PieceJointe

class PieceJointeForm(forms.ModelForm):
    class Meta:
        model = PieceJointe
        fields = ['chemin_storage', 'nom_fichier', 'type']  # Using the actual field names from your model
        widgets = {
            'chemin_storage': forms.FileInput(attrs={'class': 'form-control'}),
            'nom_fichier': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter file name'
            }),
            'type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter file type'
            }),
        }