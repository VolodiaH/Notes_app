from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import NoteFilterForm, NoteForm
from .models import Note


def index(request):
    notes = Note.objects.select_related('category').all()
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
    return render(request, 'notes/index.html', {'notes': notes, 'filters': filters})


@require_http_methods(['GET', 'POST'])
def create(request):
    form = NoteForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        note = form.save()
        return redirect('notes:detail', pk=note.pk)
    return render(request, 'notes/form.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def detail(request, pk):
    note = get_object_or_404(Note, pk=pk)
    form = NoteForm(request.POST if request.method == 'POST' else None, instance=note)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('notes:detail', pk=note.pk)
    return render(request, 'notes/form.html', {'form': form, 'note': note})


@require_POST
def delete(request, pk):
    note = get_object_or_404(Note, pk=pk)
    note.delete()
    return redirect('notes:index')
