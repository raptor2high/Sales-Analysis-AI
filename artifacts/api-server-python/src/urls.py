"""Public dashboard assets and API URLs."""

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.urls import path
from django.utils._os import safe_join
from django.views.decorators.http import require_safe

from src.routes import analyze_endpoint, chat_endpoint, health_check


@require_safe
def dashboard(request, filename=''):
    if filename:
        asset = Path(safe_join(settings.FRONTEND_DIR / 'public', filename))
        if asset.is_file():
            return FileResponse(asset.open('rb'))
    return FileResponse((settings.FRONTEND_DIR / 'index.html').open('rb'))


def internal_error(request):
    return JsonResponse({'error': 'Internal server error'}, status=500)


handler500 = internal_error

urlpatterns = [
    path('api/healthz', health_check),
    path('api/analyze', analyze_endpoint),
    path('api/chat', chat_endpoint),
    path('', dashboard),
    path('<path:filename>', dashboard),
]
