from django.urls import path
from .views import (
    MediaAnalyzeView,
    ConversionOptionsView,
    MediaConvertView,
    ConversionStatusView,
    SupportedFormatsView
)

urlpatterns = [
    path('analyze/', MediaAnalyzeView.as_view(), name='media-analyze'),
    path('options/', ConversionOptionsView.as_view(), name='conversion-options'),
    path('convert/', MediaConvertView.as_view(), name='media-convert'),
    path('status/<str:task_id>/', ConversionStatusView.as_view(), name='conversion-status'),
    path('formats/', SupportedFormatsView.as_view(), name='supported-formats'),
]