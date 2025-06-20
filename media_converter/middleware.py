from django.http import JsonResponse
from django.conf import settings

class LargeFileUploadMiddleware:
    """
    Middleware to handle large file uploads and provide better error messages
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check content length before processing
        if request.content_type and 'multipart/form-data' in request.content_type:
            content_length = request.META.get('CONTENT_LENGTH')
            if content_length:
                content_length = int(content_length)
                max_size = getattr(settings, 'DATA_UPLOAD_MAX_MEMORY_SIZE', 2621440)  # Default 2.5MB
                
                if content_length > max_size:
                    return JsonResponse({
                        'error': f'File too large. Maximum size allowed is {max_size // (1024*1024)}MB, but received {content_length // (1024*1024)}MB.'
                    }, status=413)

        response = self.get_response(request)
        return response