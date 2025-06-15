from django.urls import path
from .views import YouTubeDownloadView, YouTubeInfoView, YouTubeTestView

urlpatterns = [
    path('youtube-download/', YouTubeDownloadView.as_view(), name='youtube-download'),
    path('youtube-info/', YouTubeInfoView.as_view(), name='youtube-info'),
    path('youtube-test/', YouTubeTestView.as_view(), name='youtube-test'),
]