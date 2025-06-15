from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.conf import settings
import sys
import django
import platform
import subprocess
import os


class HeartbeatView(APIView):
    """
    Simple heartbeat endpoint to check if the API is running.
    Returns system information and current timestamp.
    """
    def get(self, request):
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'service': 'niemo.io backend',
            'version': {
                'python': sys.version,
                'django': django.get_version(),
                'platform': platform.platform()
            }
        }, status=status.HTTP_200_OK)


class SystemCheckView(APIView):
    """
    System diagnostics endpoint to check dependencies and system status.
    Useful for debugging YouTube download issues.
    """
    def get(self, request):
        checks = {}
        
        # Check yt-dlp
        try:
            import yt_dlp
            checks['yt_dlp'] = {
                'status': 'installed',
                'version': yt_dlp.version.__version__
            }
        except ImportError as e:
            checks['yt_dlp'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Check FFmpeg
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                checks['ffmpeg'] = {
                    'status': 'installed',
                    'version': version_line
                }
            else:
                checks['ffmpeg'] = {
                    'status': 'error',
                    'error': 'ffmpeg command failed'
                }
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            checks['ffmpeg'] = {
                'status': 'not_found',
                'error': str(e),
                'message': 'FFmpeg is required for audio conversion. Install it from https://ffmpeg.org/'
            }
        
        # Check temp directory
        temp_dir = getattr(settings, 'TEMP_DOWNLOAD_DIR', None)
        if temp_dir:
            checks['temp_directory'] = {
                'path': temp_dir,
                'exists': os.path.exists(temp_dir),
                'writable': os.access(temp_dir, os.W_OK) if os.path.exists(temp_dir) else False
            }
        else:
            checks['temp_directory'] = {
                'status': 'not_configured'
            }
        
        # Check disk space
        try:
            import shutil
            if temp_dir and os.path.exists(temp_dir):
                total, used, free = shutil.disk_usage(temp_dir)
                checks['disk_space'] = {
                    'total_gb': round(total / (1024**3), 2),
                    'used_gb': round(used / (1024**3), 2),
                    'free_gb': round(free / (1024**3), 2)
                }
        except Exception as e:
            checks['disk_space'] = {
                'error': str(e)
            }
        
        return Response({
            'timestamp': timezone.now().isoformat(),
            'checks': checks
        }, status=status.HTTP_200_OK)
