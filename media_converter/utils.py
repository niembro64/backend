import os
import subprocess
import json
import mimetypes
import uuid
from pathlib import Path
import shutil
import logging

logger = logging.getLogger(__name__)

# Media type mappings
VIDEO_FORMATS = ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv', 'm4v', 'mpg', 'mpeg', '3gp', 'ogv']
AUDIO_FORMATS = ['mp3', 'wav', 'flac', 'aac', 'ogg', 'wma', 'm4a', 'opus', 'aiff', 'ac3', 'dts']
IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'ico', 'svg', 'heic', 'heif']

def get_media_type(filename):
    """Determine media type from file extension"""
    ext = filename.lower().split('.')[-1]
    if ext in VIDEO_FORMATS:
        return 'video'
    elif ext in AUDIO_FORMATS:
        return 'audio'
    elif ext in IMAGE_FORMATS:
        return 'image'
    return 'unknown'

def get_file_info(file_path):
    """Extract media file information using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            # Extract basic info
            format_info = data.get('format', {})
            info = {
                'filename': os.path.basename(file_path),
                'size': int(format_info.get('size', 0)),
                'duration': float(format_info.get('duration', 0)),
                'bitrate': int(format_info.get('bit_rate', 0))
            }
            
            # Extract stream-specific info
            for stream in data.get('streams', []):
                if stream['codec_type'] == 'video':
                    info.update({
                        'width': stream.get('width'),
                        'height': stream.get('height'),
                        'video_codec': stream.get('codec_name'),
                        'fps': eval(stream.get('r_frame_rate', '0/1'))
                    })
                elif stream['codec_type'] == 'audio':
                    info.update({
                        'audio_codec': stream.get('codec_name'),
                        'sample_rate': int(stream.get('sample_rate', 0)),
                        'channels': stream.get('channels')
                    })
            
            return info
    except Exception as e:
        logger.error(f"Error getting file info: {e}")
    
    # Fallback for images or if ffprobe fails
    return {
        'filename': os.path.basename(file_path),
        'size': os.path.getsize(file_path),
        'duration': None
    }

def get_conversion_options(input_type, input_format, output_format):
    """Get available conversion options based on input and output formats"""
    options = {
        'format': output_format,
        'available_options': {}
    }
    
    if input_type == 'video':
        if output_format in VIDEO_FORMATS:
            options['available_options'] = {
                'resolution': ['4K (3840x2160)', '1080p (1920x1080)', '720p (1280x720)', '480p (854x480)', '360p (640x360)', '240p (426x240)'],
                'fps': [60, 30, 24, 15],
                'codec': ['h264', 'h265', 'vp8', 'vp9'],
                'bitrate': ['5M', '3M', '2M', '1M', '800k', '500k'],
                'quality': ['high', 'medium', 'low']
            }
        elif output_format in AUDIO_FORMATS:
            options['available_options'] = {
                'bitrate': ['320k', '256k', '192k', '128k', '96k'],
                'sample_rate': [48000, 44100, 22050],
                'channels': [2, 1]  # stereo, mono
            }
        elif output_format in IMAGE_FORMATS:
            options['available_options'] = {
                'timestamp': 'Extract frame at specific time (seconds)',
                'quality': ['high', 'medium', 'low']
            }
    
    elif input_type == 'audio':
        if output_format in AUDIO_FORMATS:
            options['available_options'] = {
                'bitrate': ['320k', '256k', '192k', '128k', '96k'],
                'sample_rate': [48000, 44100, 22050],
                'channels': [2, 1],
                'quality': ['high', 'medium', 'low']
            }
    
    elif input_type == 'image':
        if output_format in IMAGE_FORMATS:
            options['available_options'] = {
                'quality': ['high', 'medium', 'low'],
                'resolution': ['original', '1920x1080', '1280x720', '800x600', '640x480']
            }
        elif output_format == 'mp4':  # Image to video slideshow
            options['available_options'] = {
                'duration': 'Duration per image (seconds)',
                'transition': ['none', 'fade', 'slide'],
                'fps': [30, 24, 15]
            }
    
    return options

def build_ffmpeg_command(input_path, output_path, input_type, output_format, options=None):
    """Build FFmpeg command based on conversion parameters"""
    cmd = ['ffmpeg', '-i', input_path, '-y']  # -y to overwrite output
    
    if options is None:
        options = {}
    
    # Video to Video conversion
    if input_type == 'video' and output_format in VIDEO_FORMATS:
        # Resolution
        if 'resolution' in options:
            res_map = {
                '4K (3840x2160)': '3840:2160',
                '1080p (1920x1080)': '1920:1080',
                '720p (1280x720)': '1280:720',
                '480p (854x480)': '854:480',
                '360p (640x360)': '640:360',
                '240p (426x240)': '426:240'
            }
            if options['resolution'] in res_map:
                cmd.extend(['-vf', f"scale={res_map[options['resolution']]}"])
        
        # Frame rate
        if 'fps' in options:
            cmd.extend(['-r', str(options['fps'])])
        
        # Video codec
        if 'codec' in options:
            codec_map = {
                'h264': 'libx264',
                'h265': 'libx265',
                'vp8': 'libvpx',
                'vp9': 'libvpx-vp9'
            }
            cmd.extend(['-c:v', codec_map.get(options['codec'], 'libx264')])
        
        # Bitrate
        if 'bitrate' in options:
            cmd.extend(['-b:v', options['bitrate']])
        
        # Quality preset
        quality_map = {
            'high': 'slow',
            'medium': 'medium',
            'low': 'fast'
        }
        preset = quality_map.get(options.get('quality', 'medium'), 'medium')
        cmd.extend(['-preset', preset])
    
    # Video to Audio conversion
    elif input_type == 'video' and output_format in AUDIO_FORMATS:
        cmd.extend(['-vn'])  # No video
        
        # Audio codec
        codec_map = {
            'mp3': 'libmp3lame',
            'aac': 'aac',
            'ogg': 'libvorbis',
            'flac': 'flac',
            'opus': 'libopus'
        }
        if output_format in codec_map:
            cmd.extend(['-c:a', codec_map[output_format]])
        
        # Bitrate
        if 'bitrate' in options:
            cmd.extend(['-b:a', options['bitrate']])
        
        # Sample rate
        if 'sample_rate' in options:
            cmd.extend(['-ar', str(options['sample_rate'])])
        
        # Channels
        if 'channels' in options:
            cmd.extend(['-ac', str(options['channels'])])
    
    # Video to Image conversion
    elif input_type == 'video' and output_format in IMAGE_FORMATS:
        # Extract single frame
        timestamp = options.get('timestamp', 0)
        cmd = ['ffmpeg', '-ss', str(timestamp), '-i', input_path, '-vframes', '1', '-y']
        
        # Quality
        if output_format in ['jpg', 'jpeg']:
            quality_map = {'high': '2', 'medium': '5', 'low': '10'}
            q_value = quality_map.get(options.get('quality', 'medium'), '5')
            cmd.extend(['-q:v', q_value])
    
    # Audio to Audio conversion
    elif input_type == 'audio' and output_format in AUDIO_FORMATS:
        # Audio codec
        codec_map = {
            'mp3': 'libmp3lame',
            'aac': 'aac',
            'ogg': 'libvorbis',
            'flac': 'flac',
            'opus': 'libopus'
        }
        if output_format in codec_map:
            cmd.extend(['-c:a', codec_map[output_format]])
        
        # Bitrate
        if 'bitrate' in options:
            cmd.extend(['-b:a', options['bitrate']])
        
        # Sample rate
        if 'sample_rate' in options:
            cmd.extend(['-ar', str(options['sample_rate'])])
        
        # Channels
        if 'channels' in options:
            cmd.extend(['-ac', str(options['channels'])])
    
    # Image to Image conversion
    elif input_type == 'image' and output_format in IMAGE_FORMATS:
        # For image conversion, we might use ImageMagick or PIL instead
        # But FFmpeg can handle basic conversions
        if 'resolution' in options and options['resolution'] != 'original':
            cmd.extend(['-vf', f"scale={options['resolution'].replace('x', ':')}"])
        
        if output_format in ['jpg', 'jpeg'] and 'quality' in options:
            quality_map = {'high': '2', 'medium': '5', 'low': '10'}
            q_value = quality_map.get(options['quality'], '5')
            cmd.extend(['-q:v', q_value])
    
    # Trim options (for video/audio)
    if 'start_time' in options:
        # Move -ss before input for faster seeking
        idx = cmd.index('-i')
        cmd.insert(idx, str(options['start_time']))
        cmd.insert(idx, '-ss')
    
    if 'end_time' in options and 'start_time' in options:
        duration = float(options['end_time']) - float(options.get('start_time', 0))
        cmd.extend(['-t', str(duration)])
    
    cmd.append(output_path)
    return cmd

def get_supported_conversions(media_type, input_format):
    """Get list of supported output formats for given input"""
    conversions = []
    
    if media_type == 'video':
        # Video to video
        conversions.extend([
            {'format': fmt, 'type': 'video'} 
            for fmt in VIDEO_FORMATS if fmt != input_format
        ])
        # Video to audio
        conversions.extend([
            {'format': fmt, 'type': 'audio'} 
            for fmt in AUDIO_FORMATS
        ])
        # Video to image
        conversions.extend([
            {'format': 'jpg', 'type': 'image', 'description': 'Extract frame as image'},
            {'format': 'png', 'type': 'image', 'description': 'Extract frame as image'},
            {'format': 'gif', 'type': 'image', 'description': 'Convert to animated GIF'}
        ])
    
    elif media_type == 'audio':
        # Audio to audio only
        conversions.extend([
            {'format': fmt, 'type': 'audio'} 
            for fmt in AUDIO_FORMATS if fmt != input_format
        ])
    
    elif media_type == 'image':
        # Image to image
        conversions.extend([
            {'format': fmt, 'type': 'image'} 
            for fmt in IMAGE_FORMATS if fmt != input_format and fmt not in ['svg', 'heic', 'heif']
        ])
        # Image to video (slideshow)
        if input_format != 'gif':
            conversions.append({
                'format': 'mp4', 
                'type': 'video', 
                'description': 'Create video slideshow'
            })
    
    # Special case for GIF
    if input_format == 'gif':
        conversions.extend([
            {'format': 'mp4', 'type': 'video', 'description': 'Convert GIF to video'},
            {'format': 'webm', 'type': 'video', 'description': 'Convert GIF to video'}
        ])
    
    return conversions