from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseForbidden, FileResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from reportlab.pdfgen import canvas
import zipfile
import io
from .models import DossierMedical, PieceJointe, DossierAuditLog
from .forms import DossierForm, PieceJointeForm
from django.db.models import Q

# Helper Functions
from django.shortcuts import render
from .models import DossierMedical
from django.contrib.auth.decorators import login_required

from django.utils import timezone

# views.py
from django.shortcuts import redirect

def redirect_home(request):
    
    return redirect('dossier_list')

@login_required
def dossier_delete(request, pk):
    dossier = get_object_or_404(DossierMedical, pk=pk)
    if request.method == "POST":
        dossier.delete()
        messages.success(request, "Dossier supprimé avec succès.")
        return redirect('dossier_list')        
        
    messages.error(request, "Suppression non autorisée.")
    return redirect('dossier_list')

@login_required 
def dossier_list(request):
    query = request.GET.get('q', '').strip()
    user = request.user

    # Base queryset per role
    if user.role.name == 'NORMAL':
        dossiers = DossierMedical.objects.filter(employer=user)
        template = 'dossier_medicale/detail.html'
    elif user.role.name in ['ADMIN', 'CONTROLLER']:
        dossiers = DossierMedical.objects.all()
        template = 'dossier_medicale/list_admin.html'
    elif user.role.name == 'AGENT':
        dossiers = DossierMedical.objects.filter(department=user.department)
        template = 'dossier_medicale/list_agent.html'
    else:
        dossiers = DossierMedical.objects.none()
        template = 'dossier_medicale/list_normal.html'

    # Apply search filter if needed
    if query:
        dossiers = dossiers.filter(
            Q(reference__icontains=query) |
            Q(employer__first_name__icontains=query) |
            Q(employer__last_name__icontains=query)
        )

    return render(request, template, {
        'dossiers': dossiers,
        'search_query': query,
    })

def get_role_actions(user, dossier):
    """Returns available actions based on user role and dossier status"""
    actions = []
    
    # Common actions for all authenticated users
    actions.append({
        'name': 'view',
        'label': 'View Details',
        'url': '#details'
    })
    
    # Normal User specific actions
    if user.role.name == 'NORMAL':
        if dossier.created_by == user:
            actions.append({
                'name': 'download_all',
                'label': 'Download All Documents',
                'url': reverse('download_all', args=[dossier.id])
            })
    
    # Agent specific actions
    elif user.role.name == 'AGENT':
        actions.extend([
            {
                'name': 'upload',
                'label': 'Upload Document',
                'url': reverse('upload_document', args=[dossier.id])
            },
            {
                'name': 'update',
                'label': 'Update Information',
                'url': reverse('update_dossier', args=[dossier.id])
            },
            {
                'name': 'scan',
                'label': 'Scan Document',
                'url': reverse('scan_document', args=[dossier.id])
            }
        ])
    
    # Controller and Admin specific actions
    elif user.role.name in ['CONTROLLER', 'ADMIN']:
        actions.extend([
            {
                'name': 'upload',
                'label': 'Upload Document',
                'url': reverse('upload_document', args=[dossier.id])
            },
            {
                'name': 'approve',
                'label': 'Approve Dossier',
                'url': reverse('approve_dossier', args=[dossier.id])
            },
            {
                'name': 'reject',
                'label': 'Reject Dossier',
                'url': reverse('reject_dossier', args=[dossier.id])
            },
            {
                'name': 'generate_report',
                'label': 'Generate Report',
                'url': reverse('generate_report', args=[dossier.id])
            },
            {
                'name': 'edit',
                'label': 'Edit Dossier',
                'url': reverse('edit_dossier', args=[dossier.id])
            }
        ])
    
    return actions

@login_required
def dossier_detail(request, dossier_id):
    dossier = get_object_or_404(DossierMedical, pk=dossier_id)
    attachments = dossier.pieces_jointes.all()
    # Permission check
    if not dossier.user_can_view(request.user):
        raise PermissionDenied("You don't have permission to view this dossier")
    
    # Get documents with download permission check
    documents = []
    for piece in dossier.pieces_jointes.all():
        if piece.user_can_download(request.user):
            documents.append(piece)
    
    # Determine template based on user role
    if request.user.role.name == 'NORMAL':
        template = 'dossier_medicale/detail.html'
    elif request.user.role.name in ['ADMIN', 'CONTROLLER']:
        template = 'dossier_medicale/detail_admin.html'
    else:  # AGENT or other roles
        template = 'dossier_medicale/detail.html'
    
    context = {
        'dossier': dossier,
        'documents': documents,
        'actions': get_role_actions(request.user, dossier),
        'is_owner': dossier.created_by == request.user,
        'is_normal_user': request.user.role.name == 'NORMAL',
        'is_agent': request.user.role.name == 'AGENT',
        'is_controller': request.user.role.name == 'CONTROLLER',
        'is_admin': request.user.role.name == 'ADMIN',
    }
    return render(request, template, context)

@login_required

def create_dossier(request):
    # Permission check
    if not hasattr(request.user, 'role') or request.user.role.name not in ['AGENT', 'ADMIN', 'CONTROLLER']:
        raise PermissionDenied("You don't have permission to create dossiers")

    if request.method == 'POST':
        form = DossierForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Save main dossier
                dossier = form.save(commit=False)
                dossier.created_by = request.user
                dossier.status = 'SUBMITTED'
                dossier.save()

                # Handle file attachments - UPDATED to match model fields
                files = request.FILES.getlist('attachments')
                for file in files:
                    PieceJointe.objects.create(
                        dossier=dossier,
                        chemin_storage=file,  # Using correct field name
                        nom_fichier=file.name,
                        type=file.content_type.split('/')[-1].upper(),  # Extract file type
                        taille_ko=file.size // 1024,  # Calculate size in KB
                        uploaded_by=request.user,  # Only if your model has this field
                        description=f"Attached {file.name}"  # Only if your model has this field
                    )

                messages.success(request, f'Dossier {dossier.reference} created successfully!')
                return redirect('dossier_detail', dossier_id=dossier.id)
            
            except Exception as e:
                messages.error(request, f'Error creating dossier: {str(e)}')
        else:
            # Show all form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        # Initial form setup
        initial_data = {
            'start_date': timezone.now().date(),
            'priority': 2,
            'doctor': request.user.get_full_name() or "Dr. Smith"
        }
        form = DossierForm(initial=initial_data)

    return render(request, 'dossier_medicale/create.html', {
        'form': form,
        'title': 'Create New Medical Dossier',
        'required_fields': ['employee_id', 'department', 'doctor', 'diagnosis', 'treatment_plan']
    })


from django.contrib.auth.decorators import permission_required
@login_required

def edit_dossier(request, dossier_id):
    dossier = get_object_or_404(DossierMedical, id=dossier_id)
    if request.user.role.name not in ['ADMIN', 'CONTROLLER']:
        return HttpResponseForbidden()
    if dossier.status == 'APPROVED':  # Only ban editing if APPROVED
        messages.error(request, "Approved dossiers cannot be edited.")
        return redirect('dossier_detail', dossier_id=dossier.id)

    if request.method == 'POST':
        form = DossierForm(request.POST, instance=dossier)
        if form.is_valid():
            updated_dossier = form.save()
            messages.success(request, f'Dossier {updated_dossier.reference} updated successfully!')
            return redirect('dossier_detail', dossier_id=dossier.id)
    else:
        form = DossierForm(instance=dossier)

    return render(request, 'dossier_medicale/edit.html', {
        'form': form,
        'dossier': dossier,
        'title': f'Edit Dossier {dossier.reference}'
    })

@login_required
def upload_document(request, dossier_id):
    dossier = get_object_or_404(DossierMedical, pk=dossier_id)
    
    if request.user.role.name not in ['AGENT', 'CONTROLLER','ADMIN']:
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        form = PieceJointeForm(request.POST, request.FILES)
        if form.is_valid():
            piece = form.save(commit=False)
            piece.dossier = dossier
            piece.uploaded_by = request.user
            # Set file size in KB
            if piece.chemin_storage and hasattr(piece.chemin_storage, 'size'):
                piece.taille_ko = round(piece.chemin_storage.size / 1024, 2)
            else:
                piece.taille_ko = 0
            piece.save()
            messages.success(request, 'Document uploaded successfully!')
            return redirect('dossier_detail', dossier_id=dossier.id)
    else:
        form = PieceJointeForm()
    
    return render(request, 'dossier_medicale/upload.html', {
        'form': form,
        'dossier': dossier
    })

@login_required
def download_all(request, dossier_id):
    dossier = get_object_or_404(DossierMedical, pk=dossier_id)
    
    # Only owner or privileged users can download
    if not (dossier.created_by == request.user or request.user.role.name in ['AGENT', 'CONTROLLER']):
        return HttpResponseForbidden()
    
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for piece in dossier.pieces_jointes.all():
            if piece.user_can_download(request.user):
                zip_file.write(piece.chemin_storage.path, piece.nom_fichier)
    
    # Prepare response
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="dossier_{dossier.reference}.zip"'
    return response

@login_required
def approve_dossier(request, dossier_id):
    dossier = get_object_or_404(DossierMedical, pk=dossier_id)
    if request.user.role.name not in ['CONTROLLER', 'ADMIN']:
        return HttpResponseForbidden()
    dossier.status = 'APPROVED'
    dossier.save()
    messages.success(request, 'Dossier approved successfully!')
    return redirect('dossier_detail', dossier_id=dossier.id)

@login_required
def reject_dossier(request, dossier_id):
    dossier = get_object_or_404(DossierMedical, pk=dossier_id)
    if request.user.role.name not in ['CONTROLLER', 'ADMIN']:
        return HttpResponseForbidden()
    dossier.status = 'REJECTED'
    dossier.save()
    messages.warning(request, 'Dossier has been rejected.')
    return redirect('dossier_detail', dossier_id=dossier.id)

@login_required
def generate_report(request, dossier_id):
    dossier = get_object_or_404(DossierMedical, pk=dossier_id)

    # Allow CONTROLLER, ADMIN, or NORMAL (but only for their own dossier)
    if request.user.role.name in ['CONTROLLER', 'ADMIN']:
        pass
    elif request.user.role.name == 'NORMAL':
        if dossier.employer.id != request.user.id:
            return HttpResponseForbidden()
    else:
        return HttpResponseForbidden()

    # Create PDF report
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="report_{dossier.reference}.pdf"'

    p = canvas.Canvas(response)

    # Report header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, f"Medical Dossier Report - {dossier.reference}")

    # Basic information
    p.setFont("Helvetica", 12)
    y_position = 750
    # Show employee name or username
    employee_name = getattr(dossier.employer, 'get_full_name', lambda: str(dossier.employer))()
    p.drawString(100, y_position, f"Employee: {employee_name}")
    y_position -= 30
    p.drawString(100, y_position, f"Department: {dossier.department}")
    y_position -= 30
    p.drawString(100, y_position, f"Status: {dossier.get_status_display()}")
    y_position -= 30

    # Documents list
    p.drawString(100, y_position, "Attached Documents:")
    y_position -= 30
    for piece in dossier.pieces_jointes.all():
        p.drawString(120, y_position, f"- {piece.nom_fichier} ({piece.type})")
        y_position -= 20

    p.showPage()
    p.save()

    return response

@login_required
def scan_document(request, dossier_id):

    dossier = get_object_or_404(DossierMedical, pk=dossier_id)
    
    if request.user.role.name not in ['AGENT', 'CONTROLLER']:
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        # Handle scanned document upload
        scanned_file = request.FILES.get('scanned_doc')
        if scanned_file:
            piece = PieceJointe.objects.create(
                dossier=dossier,
                nom_fichier=f"Scanned_{scanned_file.name}",
                chemin_storage=scanned_file,
                type='SCAN',
                uploaded_by=request.user
            )
            messages.success(request, 'Scanned document uploaded successfully!')
            return redirect('dossier_detail', dossier_id=dossier.id)
    
    return render(request, 'dossier_medicale/scan.html', {'dossier': dossier})

@login_required
def audit_log(request):
    # Only admins and controllers can see the audit log
    if request.user.role.name not in ['ADMIN', 'CONTROLLER']:
        return HttpResponseForbidden()
    logs = DossierAuditLog.objects.select_related('dossier', 'user').order_by('-timestamp')
    return render(request, 'dossier_medicale/audit_log.html', {'logs': logs})