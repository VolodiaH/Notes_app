from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import NoteFilterForm, NoteForm
from .models import Note


@login_required
def index(request):
    scope = 'group' if request.GET.get('scope') == 'group' else 'personal'
    notes = Note.objects.select_related('category', 'owner', 'group')
    if scope == 'group':
        notes = notes.filter(group__in=request.user.groups.all())
    else:
        notes = notes.filter(owner=request.user, group__isnull=True)
    filters = NoteFilterForm(request.GET)
    if filters.is_valid():
        data = filters.cleaned_data
        if data['q']:
            notes = notes.filter(title__icontains=data['q'])
        if data['category']:
            notes = notes.filter(category=data['category'])
        if data['reminder_from']:
            notes = notes.filter(reminder__gte=data['reminder_from'])
        if data['reminder_to']:
            notes = notes.filter(reminder__lte=data['reminder_to'])
    else:
        notes = notes.none()
    return render(request, 'notes/index.html', {'notes': notes, 'filters': filters, 'scope': scope})


@login_required
@require_http_methods(['GET', 'POST'])
def create(request):
    form = NoteForm(request.POST if request.method == 'POST' else None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        note = form.save()
        return redirect('notes:detail', pk=note.pk)
    return render(request, 'notes/form.html', {'form': form})


@login_required
@require_http_methods(['GET', 'POST'])
def detail(request, pk):
    visible = Note.objects.filter(Q(owner=request.user) | Q(group__in=request.user.groups.all()))
    note = get_object_or_404(visible, pk=pk)
    if note.owner_id != request.user.pk:
        if request.method == 'POST':
            raise Http404
        return render(request, 'notes/detail.html', {'note': note})
    form = NoteForm(request.POST if request.method == 'POST' else None, instance=note, user=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('notes:detail', pk=note.pk)
    return render(request, 'notes/form.html', {'form': form, 'note': note})


@login_required
@require_POST
def delete(request, pk):
    note = get_object_or_404(Note, pk=pk, owner=request.user)
    note.delete()
    return redirect('notes:index')
