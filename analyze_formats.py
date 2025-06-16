#!/usr/bin/env python3
"""
Comprehensive analysis of the YouTube downloader implementation.
This analyzes the format strings, postprocessors, and potential issues.
"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from youtube_api.views import build_video_format_string, build_audio_format_string, get_postprocessors

def analyze_format_strings():
    """Analyze the format string generation."""
    print("=" * 60)
    print("FORMAT STRING ANALYSIS")
    print("=" * 60)
    
    print("\n1. VIDEO FORMAT STRINGS:")
    print("-" * 40)
    
    video_test_cases = [
        # (quality, format, codec, size_limit)
        ('best', 'mp4', 'auto', None),
        ('1080', 'mp4', 'auto', None),
        ('1080', 'mp4', 'h264', None),
        ('720', 'webm', 'vp9', None),
        ('480', 'auto', 'auto', None),
        ('360', 'mkv', 'h265', 100),
        ('240', 'mp4', 'av1', 50),
        ('144', 'flv', 'auto', 25),
    ]
    
    for quality, format, codec, size_limit in video_test_cases:
        result = build_video_format_string(quality, format, codec, size_limit)
        print(f"Input: quality={quality}, format={format}, codec={codec}, size={size_limit}MB")
        print(f"Output: {result}")
        print()
    
    print("\n2. AUDIO FORMAT STRINGS:")
    print("-" * 40)
    
    audio_test_cases = [
        # (quality, format, size_limit)  
        ('320', 'mp3', None),
        ('256', 'm4a', None),
        ('192', 'flac', None),
        ('128', 'ogg', 50),
        ('96', 'wav', 25),
        ('64', 'opus', 10),
    ]
    
    for quality, format, size_limit in audio_test_cases:
        result = build_audio_format_string(quality, format, size_limit)
        print(f"Input: quality={quality}, format={format}, size={size_limit}MB")
        print(f"Output: {result}")
        print()

def analyze_postprocessors():
    """Analyze the postprocessor generation."""
    print("\n3. POSTPROCESSOR ANALYSIS:")
    print("-" * 40)
    
    postprocessor_test_cases = [
        # (download_type, video_format, audio_format, audio_quality, subtitles, thumbnail, metadata)
        ('audio', 'mp4', 'mp3', '320', False, False, False),
        ('audio', 'mp4', 'mp3', '320', True, True, True),
        ('audio', 'webm', 'flac', '256', False, True, True),
        ('video', 'mp4', 'aac', '192', False, False, False),
        ('video', 'mp4', 'aac', '192', True, False, True),
        ('video', 'mkv', 'mp3', '320', True, True, True),
        ('video', 'avi', 'ogg', '128', False, False, True),
        ('video', 'mov', 'wav', '256', True, False, False),
        ('video', 'webm', 'opus', '96', False, True, True),
    ]
    
    for download_type, video_format, audio_format, audio_quality, subtitles, thumbnail, metadata in postprocessor_test_cases:
        result = get_postprocessors(download_type, video_format, audio_format, audio_quality, subtitles, thumbnail, metadata)
        print(f"Input: type={download_type}, vfmt={video_format}, afmt={audio_format}, aqlt={audio_quality}")
        print(f"       subs={subtitles}, thumb={thumbnail}, meta={metadata}")
        print(f"Output: {result}")
        print()

def identify_issues():
    """Identify potential issues with the current implementation."""
    print("\n4. POTENTIAL ISSUES IDENTIFIED:")
    print("-" * 40)
    
    issues = []
    
    # Issue 1: Audio quality parameter not used in format strings
    print("ISSUE 1: Audio quality parameter ignored in format strings")
    print("- The audio_quality parameter (320, 256, etc.) is passed to build_audio_format_string()")
    print("- But it's completely ignored in the format string generation")
    print("- Only used in postprocessors for audio conversion")
    print("- This means yt-dlp always downloads 'bestaudio' regardless of user preference")
    print()
    
    # Issue 2: Format string issues
    print("ISSUE 2: Video format string complexity")
    test_format = build_video_format_string('1080', 'mp4', 'h264', 100)
    print(f"- Generated format string: {test_format}")
    print("- This is overly complex and may not work as expected")
    print("- The fallback logic may not be optimal")
    print()
    
    # Issue 3: Postprocessor issues
    print("ISSUE 3: Postprocessor logic gaps")
    print("- Video format conversion only happens for avi, mov, mkv")
    print("- But users can select other formats like webm, flv that might need conversion")
    print("- Audio quality is used in FFmpegExtractAudio but not in initial format selection")
    print()
    
    # Issue 4: Missing audio format selection
    print("ISSUE 4: Audio format selection missing")
    print("- build_audio_format_string() doesn't use the audio_format parameter")
    print("- Always returns 'bestaudio/best' regardless of user's format preference")
    print("- Relies entirely on postprocessors for format conversion")
    print()
    
    # Issue 5: Codec mapping
    print("ISSUE 5: Codec mapping issues")
    print("- Codec mapping uses codec prefixes (avc1, hev1, etc.)")
    print("- But these might not match all variants of the codecs")
    print("- May be too restrictive and cause fallbacks")
    print()
    
    return issues

def analyze_strategy_fallbacks():
    """Analyze the download strategy fallbacks."""
    print("\n5. DOWNLOAD STRATEGY FALLBACKS:")
    print("-" * 40)
    
    print("The implementation uses 6 different strategies:")
    print("1. Full advanced config with format strings")
    print("2. iOS client")
    print("3. Android + TV clients")
    print("4. Web with embed bypass")
    print("5. mweb (mobile web)")
    print("6. Desperate fallback with 'worst' quality")
    print()
    print("ISSUE: Strategy 6 completely ignores user preferences")
    print("- Falls back to 'worst' quality instead of respecting user choice")
    print("- Uses 'worst[ext=mp4]' for video, 'worst' for audio")
    print("- This defeats the purpose of having quality selection")
    print()

def recommendations():
    """Provide recommendations for fixing the issues."""
    print("\n6. RECOMMENDATIONS:")
    print("-" * 40)
    
    print("1. FIX AUDIO QUALITY SELECTION:")
    print("   - Modify build_audio_format_string() to use audio_quality parameter")
    print("   - Use format strings like 'bestaudio[abr<=320]' for quality selection")
    print()
    
    print("2. FIX AUDIO FORMAT SELECTION:")
    print("   - Add audio format filtering to build_audio_format_string()")
    print("   - Use format strings like 'bestaudio[ext=m4a]' when specific format requested")
    print()
    
    print("3. SIMPLIFY VIDEO FORMAT STRINGS:")
    print("   - Current format strings are overly complex")
    print("   - Consider simpler alternatives that are more reliable")
    print()
    
    print("4. IMPROVE FALLBACK STRATEGY:")
    print("   - Don't completely abandon user preferences in fallback")
    print("   - Gradually relax constraints instead of jumping to 'worst'")
    print()
    
    print("5. EXPAND VIDEO CONVERSION LOGIC:")
    print("   - Add more video formats to the conversion logic")
    print("   - Handle cases where direct format isn't available")
    print()
    
    print("6. ADD FORMAT VALIDATION:")
    print("   - Validate that requested formats are actually available")
    print("   - Provide better error messages for unsupported combinations")
    print()

def test_real_world_scenarios():
    """Test real-world scenarios."""
    print("\n7. REAL-WORLD SCENARIO TESTING:")
    print("-" * 40)
    
    scenarios = [
        {
            'name': 'Typical user wants 1080p MP4',
            'params': {'video_quality': '1080', 'video_format': 'mp4', 'download_type': 'video'}
        },
        {
            'name': 'User wants high-quality MP3 audio',
            'params': {'audio_quality': '320', 'audio_format': 'mp3', 'download_type': 'audio'}
        },
        {
            'name': 'User wants 720p WebM with VP9',
            'params': {'video_quality': '720', 'video_format': 'webm', 'video_codec': 'vp9', 'download_type': 'video'}
        },
        {
            'name': 'User wants FLAC audio',
            'params': {'audio_quality': '320', 'audio_format': 'flac', 'download_type': 'audio'}
        }
    ]
    
    for scenario in scenarios:
        print(f"SCENARIO: {scenario['name']}")
        params = scenario['params']
        
        if params['download_type'] == 'video':
            format_str = build_video_format_string(
                params.get('video_quality', 'best'),
                params.get('video_format', 'mp4'),
                params.get('video_codec', 'auto'),
                params.get('file_size_limit')
            )
            print(f"  Video format string: {format_str}")
            
        elif params['download_type'] == 'audio':
            format_str = build_audio_format_string(
                params.get('audio_quality', '320'),
                params.get('audio_format', 'mp3'),
                params.get('file_size_limit')
            )
            print(f"  Audio format string: {format_str}")
            
            # Show what postprocessors would be used
            pp = get_postprocessors(
                'audio',
                'mp4',  # video_format (not used for audio)
                params.get('audio_format', 'mp3'),
                params.get('audio_quality', '320'),
                False, False, True  # subtitles, thumbnail, metadata
            )
            print(f"  Postprocessors: {pp}")
        
        print()

if __name__ == "__main__":
    analyze_format_strings()
    analyze_postprocessors()
    identify_issues()
    analyze_strategy_fallbacks()
    recommendations()
    test_real_world_scenarios()