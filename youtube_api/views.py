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


def build_video_format_string(
    video_quality, video_format, video_codec, file_size_limit=None
):
    """Build simple yt-dlp format string for video downloads."""

    # For video downloads, we want the complete video file (with audio already included)
    # yt-dlp will automatically handle merging when needed

    if video_quality == "best":
        format_string = "best"
    elif video_quality == "worst":
        format_string = "worst"
    elif video_quality.isdigit():
        # Download best video at or below specified height
        format_string = f"best[height<={video_quality}]"
    else:
        format_string = "best"

    # Add format constraint if specified
    if video_format and video_format != "auto":
        format_string = f"best[ext={video_format}]"
        if video_quality.isdigit():
            format_string = f"best[height<={video_quality}][ext={video_format}]"

    # Simple fallback
    return f"{format_string}/best"


def build_audio_format_string(audio_quality, audio_format, file_size_limit=None):
    """Build simple yt-dlp format string for MP3/audio downloads."""

    # For audio, we just need the best audio stream
    # The postprocessor will handle conversion to MP3 or other formats
    return "bestaudio/best"


def get_postprocessors(
    download_type,
    video_format,
    audio_format,
    audio_quality,
    include_subtitles,
    include_thumbnail,
    include_metadata,
):
    """Get yt-dlp postprocessors based on user preferences."""
    postprocessors = []

    if download_type == "audio":
        # Audio extraction and conversion
        postprocessors.append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": audio_quality,
            }
        )
    elif download_type == "video":
        # Add format conversion for non-MP4 formats
        # Note: MP4 and WebM are usually available directly, others need conversion
        if video_format in ["avi", "mov", "mkv", "flv"]:
            postprocessors.append(
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": video_format,
                }
            )

    # Subtitle processor
    if include_subtitles:
        postprocessors.append(
            {
                "key": "FFmpegSubtitlesConvertor",
                "format": "srt",
            }
        )

    # Thumbnail embedding
    if include_thumbnail and download_type == "audio":
        postprocessors.append(
            {
                "key": "EmbedThumbnail",
            }
        )

    # Metadata embedding
    if include_metadata:
        postprocessors.append(
            {
                "key": "FFmpegMetadata",
            }
        )

    return postprocessors


class YouTubeDownloadView(APIView):
    def post(self, request):
        url = request.data.get("url")
        download_type = request.data.get("type", "video")  # 'video' or 'audio'

        # New comprehensive options
        video_quality = request.data.get(
            "video_quality", "best"
        )  # best, 2160, 1440, 1080, 720, 480, 360, 240, 144
        video_format = request.data.get(
            "video_format", "mp4"
        )  # mp4, webm, mkv, avi, mov, flv
        video_codec = request.data.get(
            "video_codec", "auto"
        )  # auto, h264, h265, vp9, av1
        audio_quality = request.data.get(
            "audio_quality", "320"
        )  # 320, 256, 192, 128, 96, 64
        audio_format = request.data.get(
            "audio_format", "mp3"
        )  # mp3, m4a, flac, ogg, wav, opus, aac
        file_size_limit = request.data.get(
            "file_size_limit", None
        )  # max file size in MB
        include_subtitles = request.data.get("include_subtitles", False)
        include_thumbnail = request.data.get("include_thumbnail", False)
        include_metadata = request.data.get("include_metadata", True)

        logger.info(f"YouTube download request: URL={url}, type={download_type}")
        logger.info(
            f"Quality options: video_quality={video_quality}, video_format={video_format}, audio_quality={audio_quality}, audio_format={audio_format}"
        )
        logger.info(f"Raw request data: {request.data}")

        if not url:
            return Response(
                {"error": "URL is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create a temporary directory for this download
            with tempfile.TemporaryDirectory() as temp_dir:
                # Ultra-aggressive options to bypass YouTube restrictions
                common_opts = {
                    "outtmpl": os.path.join(
                        temp_dir, "video.%(ext)s"
                    ),  # Simple filename
                    "quiet": False,  # Enable output for debugging
                    "no_warnings": False,
                    # Essential for bypassing 403 errors
                    "extractor_args": {
                        "youtube": {
                            "player_client": ["android", "web"],
                            "player_skip": ["webpage"],
                        }
                    },
                    # Headers to mimic a real mobile browser
                    "http_headers": {
                        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
                        "Accept": "*/*",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Origin": "https://www.youtube.com",
                        "Referer": "https://www.youtube.com/",
                        "X-Goog-Visitor-Id": "CgtVaVlJeUdvdFZYdyiFjYuSBg%3D%3D",
                        "X-Youtube-Client-Name": "2",
                        "X-Youtube-Client-Version": "2.20231205.00.00",
                    },
                    # Ultra-aggressive anti-detection measures
                    "cookiefile": None,
                    # 'cookiesfrombrowser': ('chrome',),  # Disabled due to DPAPI issues on Windows
                    "no_check_certificate": True,
                    "ignoreerrors": False,
                    "geo_bypass": True,
                    "geo_bypass_country": "US",
                    "extractor_retries": 10,
                    "fragment_retries": 10,
                    "retries": 10,
                    "file_access_retries": 5,
                    "sleep_interval": 3,
                    "max_sleep_interval": 15,
                    "sleep_interval_requests": 2,
                    "sleep_interval_subtitles": 1,
                    # Force IPv4 and other network options
                    "force_ipv4": True,
                    "socket_timeout": 60,
                    # Use alternative extraction methods
                    "extract_flat": False,
                    "writethumbnail": False,
                    "writeinfojson": False,
                    "skip_download": False,
                }

                # Build format string and postprocessors based on user preferences
                if download_type == "audio":
                    format_string = build_audio_format_string(
                        audio_quality, audio_format, file_size_limit
                    )
                    logger.info(f"Generated audio format string: {format_string}")
                else:
                    format_string = build_video_format_string(
                        video_quality, video_format, video_codec, file_size_limit
                    )
                    logger.info(f"Generated video format string: {format_string}")
                    logger.info(
                        f"Video format parameters - quality: {video_quality}, format: {video_format}, codec: {video_codec}"
                    )

                postprocessors = get_postprocessors(
                    download_type,
                    video_format,
                    audio_format,
                    audio_quality,
                    include_subtitles,
                    include_thumbnail,
                    include_metadata,
                )
                logger.info(f"Generated postprocessors: {postprocessors}")

                # Build yt-dlp options
                ydl_opts = {
                    **common_opts,
                    "format": format_string,
                    "postprocessors": postprocessors,
                }

                # Add cookies file if it exists
                cookies_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "cookies.txt"
                )
                if os.path.exists(cookies_path):
                    ydl_opts["cookies"] = cookies_path
                    logger.info(f"Using cookies file: {cookies_path}")
                else:
                    logger.info("No cookies file found, proceeding without cookies")

                # Add subtitle options if requested
                if include_subtitles:
                    ydl_opts.update(
                        {
                            "writesubtitles": True,
                            "writeautomaticsub": True,
                            "subtitleslangs": ["en", "en-US"],
                        }
                    )

                # Add thumbnail options if requested
                if include_thumbnail:
                    ydl_opts.update(
                        {
                            "writethumbnail": True,
                        }
                    )

                # Try different extraction strategies with advanced bypasses
                strategies = [
                    # Strategy 1: Full advanced config
                    ydl_opts,
                    # Strategy 2: iOS client (often works when others fail)
                    {
                        **ydl_opts,
                        "extractor_args": {"youtube": {"player_client": ["ios"]}},
                    },
                    # Strategy 3: Android + TV clients
                    {
                        **ydl_opts,
                        "extractor_args": {
                            "youtube": {"player_client": ["android", "tv"]}
                        },
                    },
                    # Strategy 4: Web with embed bypass
                    {
                        **ydl_opts,
                        "extractor_args": {
                            "youtube": {
                                "player_client": ["web"],
                                "player_skip": ["configs"],
                            }
                        },
                    },
                    # Strategy 5: mweb (mobile web)
                    {
                        **ydl_opts,
                        "extractor_args": {"youtube": {"player_client": ["mweb"]}},
                    },
                    # Strategy 6: Simple fallback maintaining user preferences
                    {**ydl_opts, "format": "best/worst", "extractor_args": {}},
                ]

                info = None
                last_error = None

                for i, strategy in enumerate(strategies):
                    try:
                        logger.info(
                            f"Attempting download strategy {i+1}/{len(strategies)} for URL: {url}"
                        )
                        with yt_dlp.YoutubeDL(strategy) as ydl:
                            info = ydl.extract_info(url, download=True)
                            logger.info(f"Download completed using strategy {i+1}")
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
                    return Response(
                        {"error": "Download failed"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                # Find the actual video/audio file (not temp files)
                # Sort by size to get the main file (usually the largest)
                file_sizes = [
                    (f, os.path.getsize(os.path.join(temp_dir, f)))
                    for f in downloaded_files
                ]
                file_sizes.sort(key=lambda x: x[1], reverse=True)

                # Get the largest file (most likely the actual video/audio)
                main_file = file_sizes[0][0]
                file_path = os.path.join(temp_dir, main_file)
                logger.info(
                    f"Selected file: {main_file} (size: {file_sizes[0][1]} bytes)"
                )

                # Read the file and prepare response
                with open(file_path, "rb") as f:
                    file_data = f.read()

                # Use the actual file extension from the downloaded file
                actual_extension = os.path.splitext(main_file)[1].lstrip(".")
                if not actual_extension:
                    actual_extension = (
                        audio_format if download_type == "audio" else video_format
                    )

                final_filename = f"download.{actual_extension}"

                # Determine content type based on actual file extension
                content_type_map = {
                    # Video formats
                    "mp4": "video/mp4",
                    "webm": "video/webm",
                    "mkv": "video/x-matroska",
                    "avi": "video/x-msvideo",
                    "mov": "video/quicktime",
                    "flv": "video/x-flv",
                    # Audio formats
                    "mp3": "audio/mpeg",
                    "m4a": "audio/mp4",
                    "flac": "audio/flac",
                    "ogg": "audio/ogg",
                    "wav": "audio/wav",
                    "opus": "audio/opus",
                    "aac": "audio/aac",
                }
                content_type = content_type_map.get(
                    actual_extension, "application/octet-stream"
                )

                logger.info(f"Generated final filename: {final_filename}")

                # Create response
                response = HttpResponse(file_data, content_type=content_type)
                disposition_header = f'attachment; filename="{final_filename}"'
                response["Content-Disposition"] = disposition_header
                logger.info(f"Setting Content-Disposition header: {disposition_header}")
                return response

        except Exception as e:
            logger.error(f"YouTube operation error: {str(e)}", exc_info=True)
            error_details = {
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc() if settings.DEBUG else None,
            }
            return Response(error_details, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class YouTubeInfoView(APIView):
    def post(self, request):
        url = request.data.get("url")

        if not url:
            return Response(
                {"error": "URL is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # Extract relevant information
                video_info = {
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader"),
                    "view_count": info.get("view_count"),
                    "description": (
                        info.get("description", "")[:500] + "..."
                        if info.get("description")
                        and len(info.get("description", "")) > 500
                        else info.get("description", "")
                    ),
                    "upload_date": info.get("upload_date"),
                    "tags": info.get("tags", [])[:10],  # First 10 tags
                    "categories": info.get("categories", []),
                    "available_qualities": set(),
                    "available_formats": set(),
                    "has_subtitles": bool(
                        info.get("subtitles") or info.get("automatic_captions")
                    ),
                    "formats": {"video": [], "audio": []},
                }

                # Process available formats
                for f in info.get("formats", []):
                    format_info = {
                        "format_id": f.get("format_id"),
                        "ext": f.get("ext"),
                        "quality": f.get("quality"),
                        "filesize": f.get("filesize"),
                        "filesize_approx": f.get("filesize_approx"),
                        "format_note": f.get("format_note"),
                        "fps": f.get("fps"),
                        "vcodec": f.get("vcodec"),
                        "acodec": f.get("acodec"),
                        "height": f.get("height"),
                        "width": f.get("width"),
                        "abr": f.get("abr"),  # Audio bitrate
                        "vbr": f.get("vbr"),  # Video bitrate
                        "tbr": f.get("tbr"),  # Total bitrate
                    }

                    # Categorize formats
                    if f.get("vcodec") != "none" and f.get("height"):
                        video_info["formats"]["video"].append(format_info)
                        video_info["available_qualities"].add(f.get("height"))
                        video_info["available_formats"].add(f.get("ext"))
                    elif f.get("acodec") != "none":
                        video_info["formats"]["audio"].append(format_info)
                        video_info["available_formats"].add(f.get("ext"))

                # Convert sets to sorted lists
                video_info["available_qualities"] = sorted(
                    list(video_info["available_qualities"]), reverse=True
                )
                video_info["available_formats"] = sorted(
                    list(video_info["available_formats"])
                )

                return Response(video_info, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"YouTube operation error: {str(e)}", exc_info=True)
            error_details = {
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc() if settings.DEBUG else None,
            }
            return Response(error_details, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class YouTubeTestView(APIView):
    """
    Test endpoint to validate YouTube URLs and check system capabilities.
    """

    def post(self, request):
        url = request.data.get("url")

        if not url:
            return Response(
                {"error": "URL is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Test basic URL extraction without downloading
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Testing URL: {url}")
                info = ydl.extract_info(url, download=False)

                test_results = {
                    "url_valid": True,
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "uploader": info.get("uploader"),
                    "available_formats": len(info.get("formats", [])),
                    "extractor": info.get("extractor"),
                    "webpage_url": info.get("webpage_url"),
                }

                return Response(test_results, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"YouTube URL test error: {str(e)}", exc_info=True)
            error_details = {
                "url_valid": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc() if settings.DEBUG else None,
            }
            return Response(error_details, status=status.HTTP_400_BAD_REQUEST)
