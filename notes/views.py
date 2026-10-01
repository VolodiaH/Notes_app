from django.shortcuts import render

from .models import Note


def index(request):
    notes = Note.objects.select_related('category').all()
    return render(request, 'notes/index.html', {'notes': notes})
