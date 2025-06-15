from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse, HttpResponse
import yt_dlp
import os
import tempfile
import json
from django.conf import settings
import traceback
import logging

logger = logging.getLogger(__name__)


class YouTubeDownloadView(APIView):
    def post(self, request):
        url = request.data.get('url')
        download_type = request.data.get('type', 'video')  # 'video' or 'audio'
        filename = request.data.get('filename', 'download')  # Use cleaned filename from frontend
        
        logger.info(f"YouTube download request: URL={url}, type={download_type}, filename={filename}")
        logger.info(f"Raw request data: {request.data}")
        
        if not url:
            return Response({'error': 'URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create a temporary directory for this download
            with tempfile.TemporaryDirectory() as temp_dir:
                # Ultra-aggressive options to bypass YouTube restrictions
                common_opts = {
                    'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                    
                    # Essential for bypassing 403 errors
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android', 'web'],
                            'player_skip': ['webpage'],
                        }
                    },
                    
                    # Headers to mimic a real mobile browser
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                        'Accept': '*/*',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Origin': 'https://www.youtube.com',
                        'Referer': 'https://www.youtube.com/',
                        'X-Goog-Visitor-Id': 'CgtVaVlJeUdvdFZYdyiFjYuSBg%3D%3D',
                        'X-Youtube-Client-Name': '2',
                        'X-Youtube-Client-Version': '2.20231205.00.00',
                    },
                    
                    # Ultra-aggressive anti-detection measures  
                    'cookiefile': None,
                    # 'cookiesfrombrowser': ('chrome',),  # Disabled due to DPAPI issues on Windows
                    'no_check_certificate': True,
                    'ignoreerrors': False,
                    'geo_bypass': True,
                    'geo_bypass_country': 'US',
                    'extractor_retries': 10,
                    'fragment_retries': 10,
                    'retries': 10,
                    'file_access_retries': 5,
                    'sleep_interval': 3,
                    'max_sleep_interval': 15,
                    'sleep_interval_requests': 2,
                    'sleep_interval_subtitles': 1,
                    
                    # Force IPv4 and other network options
                    'force_ipv4': True,
                    'socket_timeout': 60,
                    
                    # Use alternative extraction methods
                    'extract_flat': False,
                    'writethumbnail': False,
                    'writeinfojson': False,
                    'skip_download': False,
                }

                if download_type == 'audio':
                    # Download audio only (MP3)
                    ydl_opts = {
                        **common_opts,
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '320',
                        }],
                    }
                else:
                    # Download video at highest quality
                    ydl_opts = {
                        **common_opts,
                        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    }
                
                # Try different extraction strategies with advanced bypasses
                strategies = [
                    # Strategy 1: Full advanced config
                    ydl_opts,
                    
                    # Strategy 2: iOS client (often works when others fail)
                    {**ydl_opts, 'extractor_args': {'youtube': {'player_client': ['ios']}}},
                    
                    # Strategy 3: Android + TV clients
                    {**ydl_opts, 'extractor_args': {'youtube': {'player_client': ['android', 'tv']}}},
                    
                    # Strategy 4: Web with embed bypass
                    {**ydl_opts, 'extractor_args': {'youtube': {'player_client': ['web'], 'player_skip': ['configs']}}},
                    
                    # Strategy 5: mweb (mobile web)
                    {**ydl_opts, 'extractor_args': {'youtube': {'player_client': ['mweb']}}},
                    
                    # Strategy 6: Desperate fallback - no client specification
                    {**common_opts, 'format': 'worst' if download_type == 'audio' else 'worst[ext=mp4]', 'extractor_args': {}},
                ]
                
                info = None
                last_error = None
                
                for i, strategy in enumerate(strategies):
                    try:
                        logger.info(f"Attempting download strategy {i+1}/{len(strategies)} for URL: {url}")
                        with yt_dlp.YoutubeDL(strategy) as ydl:
                            info = ydl.extract_info(url, download=True)
                            logger.info(f"Download completed using strategy {i+1}: {filename}")
                            break
                    except Exception as e:
                        last_error = e
                        logger.warning(f"Strategy {i+1} failed: {str(e)}")
                        if i < len(strategies) - 1:
                            logger.info(f"Trying next strategy...")
                            continue
                        else:
                            raise last_error
                
                # Find the downloaded file
                downloaded_files = os.listdir(temp_dir)
                logger.info(f"Downloaded files in temp dir: {downloaded_files}")
                if not downloaded_files:
                    logger.error("No files found in temp directory after download")
                    return Response({'error': 'Download failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                file_path = os.path.join(temp_dir, downloaded_files[0])
                
                # Read the file and prepare response
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                # Use the cleaned filename from frontend and add appropriate extension
                if download_type == 'audio':
                    content_type = 'audio/mpeg'
                    final_filename = f"{filename}.mp3"
                else:
                    content_type = 'video/mp4'
                    final_filename = f"{filename}.mp4"
                
                logger.info(f"Generated final filename: {final_filename}")
                
                # Create response
                response = HttpResponse(file_data, content_type=content_type)
                disposition_header = f'attachment; filename="{final_filename}"'
                response['Content-Disposition'] = disposition_header
                logger.info(f"Setting Content-Disposition header: {disposition_header}")
                return response
                    
        except Exception as e:
            logger.error(f"YouTube operation error: {str(e)}", exc_info=True)
            error_details = {
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc() if settings.DEBUG else None
            }
            return Response(error_details, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class YouTubeInfoView(APIView):
    def post(self, request):
        url = request.data.get('url')
        
        if not url:
            return Response({'error': 'URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Extract relevant information
                video_info = {
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'thumbnail': info.get('thumbnail'),
                    'uploader': info.get('uploader'),
                    'view_count': info.get('view_count'),
                    'formats': []
                }
                
                # Get available formats
                for f in info.get('formats', []):
                    if f.get('vcodec') != 'none' or f.get('acodec') != 'none':
                        format_info = {
                            'format_id': f.get('format_id'),
                            'ext': f.get('ext'),
                            'quality': f.get('quality'),
                            'filesize': f.get('filesize'),
                            'format_note': f.get('format_note'),
                        }
                        video_info['formats'].append(format_info)
                
                return Response(video_info, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"YouTube operation error: {str(e)}", exc_info=True)
            error_details = {
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc() if settings.DEBUG else None
            }
            return Response(error_details, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class YouTubeTestView(APIView):
    """
    Test endpoint to validate YouTube URLs and check system capabilities.
    """
    def post(self, request):
        url = request.data.get('url')
        
        if not url:
            return Response({'error': 'URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Test basic URL extraction without downloading
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Testing URL: {url}")
                info = ydl.extract_info(url, download=False)
                
                test_results = {
                    'url_valid': True,
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'available_formats': len(info.get('formats', [])),
                    'extractor': info.get('extractor'),
                    'webpage_url': info.get('webpage_url')
                }
                
                return Response(test_results, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"YouTube URL test error: {str(e)}", exc_info=True)
            error_details = {
                'url_valid': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc() if settings.DEBUG else None
            }
            return Response(error_details, status=status.HTTP_400_BAD_REQUEST)