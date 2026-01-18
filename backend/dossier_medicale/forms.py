from django import forms
from .models import DossierMedical, PieceJointe, User
from django.utils import timezone
from django.core.exceptions import ValidationError

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class DossierForm(forms.ModelForm):
    # Field removed from here to be handled manually in the view
    # to avoid 'No file was submitted' validation errors.
    
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
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control-modern'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control-modern'}),
            'diagnosis': forms.Textarea(attrs={'rows': 3, 'class': 'form-control-modern'}),
            'treatment_plan': forms.Textarea(attrs={'rows': 3, 'class': 'form-control-modern'}),
            'comments': forms.Textarea(attrs={'rows': 2, 'class': 'form-control-modern'}),
            'priority': forms.Select(attrs={'class': 'form-select-modern'}),
            'status': forms.Select(attrs={'class': 'form-select-modern'}),
            'employer': forms.Select(attrs={'class': 'form-select-modern'}),
            'department': forms.TextInput(attrs={'class': 'form-control-modern'}),
            'doctor': forms.TextInput(attrs={'class': 'form-control-modern'}),
            'reason': forms.TextInput(attrs={'class': 'form-control-modern'}),
            'is_confidential': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if 'status' in self.fields:
            self.fields['status'].required = False
            
        # Customize employer queryset 
        if user and hasattr(user, 'role'):
            if user.role.name in ['ADMIN', 'CONTROLLER']:
                self.fields['employer'].queryset = User.objects.filter(is_active=True).exclude(id=user.id).order_by('full_name')
            else:
                self.fields['employer'].queryset = User.objects.filter(
                    is_active=True,
                    role__name__in=['NORMAL', 'AGENT']
                ).order_by('full_name')

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if end_date and start_date and end_date < start_date:
            raise ValidationError("La date de fin ne peut pas être antérieure à la date de début.")
        return cleaned_data

class PieceJointeForm(forms.ModelForm):
    class Meta:
        model = PieceJointe
        fields = ['chemin_storage', 'nom_fichier', 'type', 'description']
        widgets = {
            'chemin_storage': forms.FileInput(attrs={'class': 'form-control-modern'}),
            'nom_fichier': forms.TextInput(attrs={'class': 'form-control-modern'}),
            'type': forms.TextInput(attrs={'class': 'form-control-modern'}),
            'description': forms.Textarea(attrs={'class': 'form-control-modern', 'rows': 2}),
        }