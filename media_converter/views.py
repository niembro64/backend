from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import uuid
import subprocess
import logging
from pathlib import Path
import json
import mimetypes

from .serializers import (
    MediaUploadSerializer, 
    MediaInfoSerializer,
    MediaConversionSerializer,
    ConversionStatusSerializer
)
from .utils import (
    get_media_type,
    get_file_info,
    get_supported_conversions,
    get_conversion_options,
    build_ffmpeg_command
)

logger = logging.getLogger(__name__)

# In-memory task storage (for demo purposes, use Redis/Celery in production)
conversion_tasks = {}

class MediaAnalyzeView(APIView):
    """Analyze uploaded media and return conversion options"""
    
    def post(self, request):
        serializer = MediaUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            uploaded_file = serializer.validated_data['file']
            
            # Save temporarily
            temp_id = str(uuid.uuid4())
            temp_dir = Path(settings.MEDIA_ROOT) / 'temp_uploads'
            temp_dir.mkdir(exist_ok=True)
            
            file_ext = uploaded_file.name.split('.')[-1].lower()
            temp_path = temp_dir / f"{temp_id}.{file_ext}"
            
            # Save file
            with open(temp_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Analyze file
            media_type = get_media_type(uploaded_file.name)
            file_info = get_file_info(str(temp_path))
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(uploaded_file.name)
            
            # Build response
            response_data = {
                'temp_id': temp_id,
                'filename': uploaded_file.name,
                'file_type': media_type,
                'mime_type': mime_type or 'application/octet-stream',
                'size': uploaded_file.size,
                'file_info': file_info,
                'supported_conversions': get_supported_conversions(media_type, file_ext)
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error analyzing media: {e}")
            
            # Check if it's a file size issue
            if "413" in str(e) or "too large" in str(e).lower():
                return Response(
                    {'error': 'File too large. Maximum size allowed is 500MB.'},
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                )
            
            return Response(
                {'error': f'Failed to analyze media file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ConversionOptionsView(APIView):
    """Get detailed conversion options for specific format"""
    
    def post(self, request):
        input_type = request.data.get('input_type')
        input_format = request.data.get('input_format')
        output_format = request.data.get('output_format')
        
        if not all([input_type, input_format, output_format]):
            return Response(
                {'error': 'Missing required parameters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        options = get_conversion_options(input_type, input_format, output_format)
        return Response(options, status=status.HTTP_200_OK)

class MediaConvertView(APIView):
    """Convert media files"""
    
    def post(self, request):
        try:
            # Check if using temp_id or new upload
            temp_id = request.data.get('temp_id')
            output_format = request.data.get('output_format')
            options = request.data.get('options', {})
            
            if not output_format:
                return Response(
                    {'error': 'output_format is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Handle file source
            if temp_id:
                # Use previously uploaded file
                temp_dir = Path(settings.MEDIA_ROOT) / 'temp_uploads'
                temp_files = list(temp_dir.glob(f"{temp_id}.*"))
                
                if not temp_files:
                    return Response(
                        {'error': 'Temporary file not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                input_path = temp_files[0]
                input_format = input_path.suffix[1:].lower()
            else:
                # New file upload
                serializer = MediaUploadSerializer(data=request.data)
                if not serializer.is_valid():
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                uploaded_file = serializer.validated_data['file']
                temp_id = str(uuid.uuid4())
                temp_dir = Path(settings.MEDIA_ROOT) / 'temp_uploads'
                temp_dir.mkdir(exist_ok=True)
                
                input_format = uploaded_file.name.split('.')[-1].lower()
                input_path = temp_dir / f"{temp_id}.{input_format}"
                
                with open(input_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
            
            # Create task
            task_id = str(uuid.uuid4())
            output_dir = Path(settings.MEDIA_ROOT) / 'conversions'
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"{task_id}.{output_format}"
            
            # Store task info
            conversion_tasks[task_id] = {
                'status': 'pending',
                'progress': 0,
                'input_path': str(input_path),
                'output_path': str(output_path),
                'output_format': output_format
            }
            
            # Get media type
            media_type = get_media_type(input_path.name)
            
            # Build and run FFmpeg command
            try:
                cmd = build_ffmpeg_command(
                    str(input_path),
                    str(output_path),
                    media_type,
                    output_format,
                    options
                )
                
                # Update status
                conversion_tasks[task_id]['status'] = 'processing'
                conversion_tasks[task_id]['progress'] = 10
                
                logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
                
                # Run conversion
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    # Success
                    conversion_tasks[task_id]['status'] = 'completed'
                    conversion_tasks[task_id]['progress'] = 100
                    conversion_tasks[task_id]['download_url'] = f"/media/conversions/{task_id}.{output_format}"
                    
                    # Clean up temp file if it was a new upload
                    if not request.data.get('temp_id'):
                        os.remove(input_path)
                    
                    return Response({
                        'task_id': task_id,
                        'status': 'completed',
                        'download_url': conversion_tasks[task_id]['download_url']
                    }, status=status.HTTP_200_OK)
                else:
                    # Error
                    conversion_tasks[task_id]['status'] = 'failed'
                    conversion_tasks[task_id]['error'] = stderr
                    logger.error(f"FFmpeg error: {stderr}")
                    
                    return Response({
                        'task_id': task_id,
                        'status': 'failed',
                        'error': 'Conversion failed'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
            except Exception as e:
                conversion_tasks[task_id]['status'] = 'failed'
                conversion_tasks[task_id]['error'] = str(e)
                logger.error(f"Conversion error: {e}")
                
                return Response({
                    'task_id': task_id,
                    'status': 'failed',
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Media conversion error: {e}")
            return Response(
                {'error': 'Failed to process conversion request'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ConversionStatusView(APIView):
    """Check conversion task status"""
    
    def get(self, request, task_id):
        task = conversion_tasks.get(task_id)
        
        if not task:
            return Response(
                {'error': 'Task not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        response_data = {
            'task_id': task_id,
            'status': task['status'],
            'progress': task['progress']
        }
        
        if task['status'] == 'completed':
            response_data['download_url'] = task.get('download_url')
        elif task['status'] == 'failed':
            response_data['error'] = task.get('error', 'Conversion failed')
        
        return Response(response_data, status=status.HTTP_200_OK)

class SupportedFormatsView(APIView):
    """Get all supported formats"""
    
    def get(self, request):
        from .utils import VIDEO_FORMATS, AUDIO_FORMATS, IMAGE_FORMATS
        
        return Response({
            'video': VIDEO_FORMATS,
            'audio': AUDIO_FORMATS,
            'image': IMAGE_FORMATS
        }, status=status.HTTP_200_OK)
