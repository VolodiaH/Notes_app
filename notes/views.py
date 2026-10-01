from django.http import HttpResponse


def index(request):
    return HttpResponse('Hello from Notes app.', content_type='text/plain')
