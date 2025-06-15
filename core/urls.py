from django.urls import path
from .views import HeartbeatView, SystemCheckView

urlpatterns = [
    path('heartbeat/', HeartbeatView.as_view(), name='heartbeat'),
    path('system-check/', SystemCheckView.as_view(), name='system-check'),
]