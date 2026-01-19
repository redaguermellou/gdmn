from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseForbidden, FileResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
import zipfile
import io
from .models import DossierMedical, PieceJointe, DossierAuditLog, PriseEnCharge
from .forms import DossierForm, PieceJointeForm, PriseEnChargeForm
from django.db.models import Q
from decimal import Decimal

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
    # Base queryset per role
    if user.role.name in ['ADMIN', 'CONTROLLER']:
        dossiers = DossierMedical.objects.all()
        template = 'dossier_medicale/list_admin.html'
    elif user.role.name == 'AGENT':
        dossiers = DossierMedical.objects.filter(department=user.department)
        template = 'dossier_medicale/list_agent.html'
    else:
        dossiers = DossierMedical.objects.none()
        template = 'dossier_medicale/list_agent.html'

    # Apply search filter if needed
    if query:
        dossiers = dossiers.filter(
            Q(reference__icontains=query) |
            Q(employer__first_name__icontains=query) |
            Q(employer__last_name__icontains=query)
        )

    import json
    
    context = {
        'dossiers': dossiers,
        'search_query': query,
    }

    # Add statistics for Admin/Controller
    if user.role.name in ['ADMIN', 'CONTROLLER']:
        # General stats
        stats = {
            'total': dossiers.count(),
            'approved': dossiers.filter(status='APPROVED').count(),
            'pending': dossiers.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count(),
            'rejected': dossiers.filter(status='REJECTED').count(),
        }
        
        context.update({
            'stats': stats,
        })

    return render(request, template, context)

def get_role_actions(user, dossier):
    """Returns available actions based on user role and dossier status"""
    actions = []
    
    # Common actions for all authenticated users
    actions.append({
        'name': 'view',
        'label': 'View Details',
        'url': '#details'
    })
    
    # No more normal user specific actions info
    pass
    
    # Agent specific actions
    if user.role.name == 'AGENT':
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
    if request.user.role.name in ['ADMIN', 'CONTROLLER']:
        template = 'dossier_medicale/detail_admin.html'
    else:  # AGENT or other roles
        template = 'dossier_medicale/detail.html'
    
    context = {
        'dossier': dossier,
        'documents': documents,
        'actions': get_role_actions(request.user, dossier),
        'is_owner': dossier.created_by == request.user,
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
        form = DossierForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                # Save main dossier
                dossier = form.save(commit=False)
                dossier.created_by = request.user
                dossier.status = 'SUBMITTED'
                dossier.save()

                # Audit Log: Create
                DossierAuditLog.objects.create(
                    dossier=dossier,
                    action='CREATE',
                    user=request.user,
                    details={'reference': dossier.reference, 'status': dossier.status}
                )

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
                    # Audit Log: Attachment
                    DossierAuditLog.objects.create(
                        dossier=dossier,
                        action='ATTACHMENT_ADD',
                        user=request.user,
                        details={'filename': file.name, 'size_kb': file.size // 1024}
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
        form = DossierForm(initial=initial_data, user=request.user)

    return render(request, 'dossier_medicale/create.html', {
        'form': form,
        'title': 'Créer un nouveau dossier médical',
        'required_fields': ['employer', 'department', 'doctor', 'diagnosis', 'treatment_plan', 'start_date']
    })


from django.contrib.auth.decorators import permission_required
@login_required

def edit_dossier(request, dossier_id):
    dossier = get_object_or_404(DossierMedical, id=dossier_id)
    
    # Updated permissions: Admin, Controller, or the Agent who created it
    is_authorized = (
        request.user.role.name in ['ADMIN', 'CONTROLLER'] or 
        (request.user.role.name == 'AGENT' and dossier.created_by == request.user)
    )
    
    if not is_authorized:
        return HttpResponseForbidden()

    if dossier.status == 'APPROVED':  # Only ban editing if APPROVED
        messages.error(request, "Approved dossiers cannot be edited.")
        return redirect('dossier_detail', dossier_id=dossier.id)

    if request.method == 'POST':
        form = DossierForm(request.POST, request.FILES, instance=dossier, user=request.user)
        if form.is_valid():
            # Track changes could be implemented here if needed, for now just logging the event
            old_status = dossier.status
            updated_dossier = form.save()
            
            # Audit Log: Update
            DossierAuditLog.objects.create(
                dossier=updated_dossier,
                action='UPDATE',
                user=request.user,
                details={'changes': 'Dossier updated via edit form'}
            )
            
            messages.success(request, f'Dossier {updated_dossier.reference} updated successfully!')
            
            # Handle additional attachments if any were added during edit
            files = request.FILES.getlist('attachments')
            for file in files:
                PieceJointe.objects.create(
                    dossier=updated_dossier,
                    chemin_storage=file,
                    nom_fichier=file.name,
                    type=file.content_type.split('/')[-1].upper(),
                    taille_ko=file.size // 1024,
                    uploaded_by=request.user,
                    description=f"Added during update: {file.name}"
                )
                DossierAuditLog.objects.create(
                    dossier=updated_dossier,
                    action='ATTACHMENT_ADD',
                    user=request.user,
                    details={'filename': file.name, 'size_kb': file.size // 1024}
                )

            return redirect('dossier_detail', dossier_id=dossier.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = DossierForm(instance=dossier, user=request.user)

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

            # Audit Log: Attachment Add
            DossierAuditLog.objects.create(
                dossier=dossier,
                action='ATTACHMENT_ADD',
                user=request.user,
                details={'filename': piece.nom_fichier, 'type': piece.type}
            )

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
    
    old_status = dossier.status
    dossier.status = 'APPROVED'
    dossier.save()
    
    # Audit Log: Status Change
    DossierAuditLog.objects.create(
        dossier=dossier,
        action='STATUS_CHANGE',
        user=request.user,
        details={'old_status': old_status, 'new_status': 'APPROVED'}
    )

    messages.success(request, 'Dossier approved successfully!')
    return redirect('dossier_detail', dossier_id=dossier.id)

@login_required
def reject_dossier(request, dossier_id):
    dossier = get_object_or_404(DossierMedical, pk=dossier_id)
    if request.user.role.name not in ['CONTROLLER', 'ADMIN']:
        return HttpResponseForbidden()
    
    old_status = dossier.status
    dossier.status = 'REJECTED'
    dossier.save()

    # Audit Log: Status Change
    DossierAuditLog.objects.create(
        dossier=dossier,
        action='STATUS_CHANGE',
        user=request.user,
        details={'old_status': old_status, 'new_status': 'REJECTED'}
    )

    messages.warning(request, 'Dossier has been rejected.')
    return redirect('dossier_detail', dossier_id=dossier.id)

@login_required
def generate_report(request, dossier_id):
    dossier = get_object_or_404(DossierMedical, pk=dossier_id)

    # Permission check
    if request.user.role.name in ['CONTROLLER', 'ADMIN']:
        pass
    elif request.user.role.name == 'AGENT' and dossier.created_by == request.user:
        pass
    else:
        return HttpResponseForbidden()

    # Create the PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_{dossier.reference}.pdf"'

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor("#0ea5e9"),
        alignment=1,
        spaceAfter=30
    )
    
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=20,
        spaceAfter=10,
        borderPadding=5,
        backgroundColor=colors.HexColor("#f1f5f9")
    )

    content = []

    # Title
    content.append(Paragraph(f"RAPPORT MÉDICAL", title_style))
    content.append(Paragraph(f"Référence: {dossier.reference}", styles['Normal']))
    content.append(Spacer(1, 0.2 * inch))

    # General Information Table
    data = [
        ["INFORMATION GÉNÉRALE", ""],
        ["Employé:", dossier.employer.full_name],
        ["Département:", dossier.department],
        ["Médecin:", dossier.doctor],
        ["Date de début:", dossier.start_date.strftime('%d/%m/%Y')],
        ["Statut:", dossier.get_status_display()],
        ["Priorité:", dossier.get_priority_display()]
    ]
    
    t = Table(data, colWidths=[1.5*inch, 4*inch])
    t.setStyle(TableStyle([
        ('SPAN', (0, 0), (1, 0)),
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor("#0ea5e9")),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor("#f8fafc")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    content.append(t)

    # Medical Details
    content.append(Paragraph("DÉTAILS MÉDICAUX", section_style))
    
    content.append(Paragraph("<b>Diagnostic:</b>", styles['Normal']))
    content.append(Paragraph(dossier.diagnosis, styles['Normal']))
    content.append(Spacer(1, 0.1 * inch))
    
    content.append(Paragraph("<b>Plan de Traitement:</b>", styles['Normal']))
    content.append(Paragraph(dossier.treatment_plan, styles['Normal']))
    
    if dossier.reason:
        content.append(Spacer(1, 0.1 * inch))
        content.append(Paragraph("<b>Raison:</b>", styles['Normal']))
        content.append(Paragraph(dossier.reason, styles['Normal']))

    if dossier.comments:
        content.append(Spacer(1, 0.1 * inch))
        content.append(Paragraph("<b>Commentaires additionnels:</b>", styles['Normal']))
        content.append(Paragraph(dossier.comments, styles['Normal']))

    # Documents
    if dossier.pieces_jointes.exists():
        content.append(Paragraph("PIÈCES JOINTES", section_style))
        for piece in dossier.pieces_jointes.all():
            content.append(Paragraph(f"• {piece.nom_fichier} ({piece.type})", styles['Normal']))

    # Footer
    content.append(Spacer(1, 0.5 * inch))
    footer_text = f"Généré le {timezone.now().strftime('%d/%m/%Y à %H:%M')} - Système de Gestion Dossiers Médicaux"
    content.append(Paragraph(footer_text, styles['Italic']))

    # Build PDF
    doc.build(content)
    
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
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

            # Audit Log: Scan Attachment
            DossierAuditLog.objects.create(
                dossier=dossier,
                action='ATTACHMENT_ADD',
                user=request.user,
                details={'filename': piece.nom_fichier, 'type': 'SCAN'}
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

# Prise en Charge Views
@login_required
def pec_list(request):
    query = request.GET.get('q', '').strip()
    user = request.user

    if user.role.name in ['ADMIN', 'CONTROLLER']:
        pecs = PriseEnCharge.objects.all()
    else:
        pecs = PriseEnCharge.objects.filter(Q(patient=user) | Q(created_by=user))

    if query:
        pecs = pecs.filter(
            Q(reference__icontains=query) |
            Q(patient__full_name__icontains=query) |
            Q(institution__icontains=query)
        )

    return render(request, 'dossier_medicale/pec_list.html', {
        'pecs': pecs,
        'search_query': query,
    })

@login_required
def pec_create(request):
    if request.method == 'POST':
        form = PriseEnChargeForm(request.POST, user=request.user)
        if form.is_valid():
            pec = form.save(commit=False)
            pec.created_by = request.user
            pec.status = 'SUBMITTED'
            pec.save()
            messages.success(request, f'Prise en charge {pec.reference} créée avec succès.')
            return redirect('pec_detail', pec_id=pec.id)
    else:
        form = PriseEnChargeForm(user=request.user)
    
    return render(request, 'dossier_medicale/pec_create.html', {'form': form})

@login_required
def pec_detail(request, pec_id):
    pec = get_object_or_404(PriseEnCharge, pk=pec_id)
    if not pec.user_can_view(request.user):
        raise PermissionDenied()
    
    remainder = None
    if pec.estimated_cost:
        remainder = pec.estimated_cost * (Decimal('1.0') - (Decimal(str(pec.coverage_percentage)) / Decimal('100.0')))

    return render(request, 'dossier_medicale/pec_detail.html', {
        'pec': pec,
        'remainder': remainder,
        'is_admin': request.user.role.name in ['ADMIN', 'CONTROLLER']
    })

@login_required
def pec_approve(request, pec_id):
    if request.user.role.name not in ['ADMIN', 'CONTROLLER']:
        return HttpResponseForbidden()
    pec = get_object_or_404(PriseEnCharge, pk=pec_id)
    pec.status = 'APPROVED'
    pec.save()
    messages.success(request, 'Prise en charge approuvée.')
    return redirect('pec_detail', pec_id=pec.id)

@login_required
def pec_reject(request, pec_id):
    if request.user.role.name not in ['ADMIN', 'CONTROLLER']:
        return HttpResponseForbidden()
    pec = get_object_or_404(PriseEnCharge, pk=pec_id)
    pec.status = 'REJECTED'
    pec.save()
    messages.warning(request, 'Prise en charge rejetée.')
    return redirect('pec_detail', pec_id=pec.id)

@login_required
def pec_delete(request, pec_id):
    pec = get_object_or_404(PriseEnCharge, pk=pec_id)
    if request.user.role.name != 'ADMIN' and pec.created_by != request.user:
        return HttpResponseForbidden()
    pec.delete()
    messages.success(request, 'Prise en charge supprimée.')
    return redirect('pec_list')

@login_required
def global_report(request):
    if request.user.role.name not in ['ADMIN', 'CONTROLLER']:
        return HttpResponseForbidden()

    from django.db.models import Count, Sum
    import json

    # --- Dossier Stats ---
    dossiers = DossierMedical.objects.all()
    dossier_stats = {
        'total': dossiers.count(),
        'approved': dossiers.filter(status='APPROVED').count(),
        'pending': dossiers.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count(),
        'rejected': dossiers.filter(status='REJECTED').count(),
    }

    status_counts = list(dossiers.values('status').annotate(count=Count('id')))
    priority_counts = list(dossiers.values('priority').annotate(count=Count('id')))
    dept_counts = list(dossiers.values('department').annotate(count=Count('id')))

    chart_dossier_status = {
        'labels': [dict(DossierMedical.STATUS_CHOICES).get(s['status']) for s in status_counts],
        'data': [s['count'] for s in status_counts],
        'colors': [DossierMedical.get_status_hex_by_status(s['status']) for s in status_counts]
    }

    priority_labels = dict(DossierMedical.PRIORITY_LEVELS)
    chart_dossier_priority = {
        'labels': [priority_labels.get(p['priority']) for p in priority_counts],
        'data': [p['count'] for p in priority_counts]
    }

    chart_dossier_dept = {
        'labels': [d['department'] for d in dept_counts],
        'data': [d['count'] for d in dept_counts]
    }

    # --- Prise en Charge Stats ---
    pecs = PriseEnCharge.objects.all()
    pec_stats = {
        'total': pecs.count(),
        'approved': pecs.filter(status='APPROVED').count(),
        'pending': pecs.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count(),
        'rejected': pecs.filter(status='REJECTED').count(),
        'total_cost': pecs.aggregate(total=Sum('estimated_cost'))['total'] or 0,
    }

    pec_status_counts = list(pecs.values('status').annotate(count=Count('id')))
    pec_type_counts = list(pecs.values('care_type').annotate(count=Count('id')))

    chart_pec_status = {
        'labels': [dict(PriseEnCharge.STATUS_CHOICES).get(s['status']) for s in pec_status_counts],
        'data': [s['count'] for s in pec_status_counts],
        'colors': [PriseEnCharge.get_status_hex_by_status(s['status']) for s in pec_status_counts]
    }

    chart_pec_type = {
        'labels': [dict(PriseEnCharge.CARE_TYPES).get(t['care_type']) for t in pec_type_counts],
        'data': [t['count'] for t in pec_type_counts]
    }

    # Data for Tables
    dossier_table = []
    for status_code, status_label in DossierMedical.STATUS_CHOICES:
        count = dossiers.filter(status=status_code).count()
        dossier_table.append({'label': status_label, 'count': count})

    pec_table = []
    for type_code, type_label in PriseEnCharge.CARE_TYPES:
        count = pecs.filter(care_type=type_code).count()
        cost = pecs.filter(care_type=type_code).aggregate(total=Sum('estimated_cost'))['total'] or 0
        pec_table.append({'label': type_label, 'count': count, 'cost': cost})

    # Recent & Critical lists
    critical_dossiers = dossiers.filter(priority__gte=3).order_by('-created_at')[:5]
    recent_pecs = pecs.order_by('-created_at')[:5]

    context = {
        'dossier_stats': dossier_stats,
        'pec_stats': pec_stats,
        'dossier_table': dossier_table,
        'pec_table': pec_table,
        'critical_dossiers': critical_dossiers,
        'recent_pecs': recent_pecs,
        'chart_dossier_status': json.dumps(chart_dossier_status),
        'chart_dossier_priority': json.dumps(chart_dossier_priority),
        'chart_dossier_dept': json.dumps(chart_dossier_dept),
        'chart_pec_status': json.dumps(chart_pec_status),
        'chart_pec_type': json.dumps(chart_pec_type),
    }

    return render(request, 'dossier_medicale/report_global.html', context)