from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.generic import TemplateView


class OfflineFallbackView(TemplateView):
    template_name = 'offline.html'


def service_worker_view(request):
    content = render_to_string('pwa/service-worker.js', {'app_version': settings.GSO_APP_VERSION})
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response


def manifest_view(request):
    content = render_to_string('pwa/manifest.webmanifest')
    response = HttpResponse(content, content_type='application/manifest+json')
    response['Cache-Control'] = 'public, max-age=3600'
    return response
