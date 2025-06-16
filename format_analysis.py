#!/usr/bin/env python3
"""
Analysis of format string generation issues in YouTube downloader.
"""

def current_build_video_format_string(video_quality, video_format, video_codec, file_size_limit=None):
    """Current implementation - demonstrates the issues."""
    format_options = []
    
    # Build primary video selection
    if video_quality == 'best':
        video_selector = 'bestvideo'
    elif video_quality == 'worst':
        video_selector = 'worstvideo'
    elif video_quality.isdigit():
        height = video_quality
        video_selector = f'bestvideo[height<={height}]'
    else:
        video_selector = 'bestvideo'
    
    # Add format constraint if specified (but keep MP4 flexible)
    if video_format != 'auto':
        video_with_format = f'{video_selector}[ext={video_format}]'
        format_options.append(f'{video_with_format}+bestaudio[ext=m4a]/bestaudio')
        format_options.append(f'{video_with_format}+bestaudio')
    
    # Add general video selection with best audio
    format_options.append(f'{video_selector}+bestaudio[ext=m4a]/bestaudio')
    format_options.append(f'{video_selector}+bestaudio')
    
    # Add format-specific fallbacks
    if video_format != 'auto':
        format_options.append(f'best[ext={video_format}]')
    
    # Add universal fallbacks
    format_options.extend([
        'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
        'best'
    ])
    
    return '/'.join(format_options)

def improved_build_video_format_string(video_quality, video_format, video_codec, file_size_limit=None):
    """Improved implementation - simpler and more reliable."""
    format_parts = []
    
    # Build video selector
    if video_quality == 'best':
        video_base = 'bestvideo'
    elif video_quality == 'worst':
        video_base = 'worstvideo'
    elif video_quality.isdigit():
        video_base = f'bestvideo[height<={video_quality}]'
    else:
        video_base = 'bestvideo'
    
    # Add format constraint
    if video_format != 'auto':
        video_selector = f'{video_base}[ext={video_format}]'
    else:
        video_selector = video_base
    
    # Add codec constraint (this was missing in original!)
    if video_codec != 'auto':
        codec_map = {
            'h264': 'avc1',
            'h265': 'hev1', 
            'vp9': 'vp09',
            'av1': 'av01'
        }
        if video_codec in codec_map:
            video_selector += f'[vcodec^={codec_map[video_codec]}]'
    
    # Add file size limit
    if file_size_limit:
        video_selector += f'[filesize<{file_size_limit}M]'
    
    # Build simple, reliable format string
    format_parts = [
        f'{video_selector}+bestaudio',
        f'{video_base}+bestaudio',  # Fallback without specific format
        'best'  # Final fallback
    ]
    
    return '/'.join(format_parts)

def analyze_format_strings():
    """Compare current vs improved format strings."""
    test_cases = [
        ('1080', 'mp4', 'h264', None),
        ('720', 'webm', 'vp9', None),
        ('480', 'mp4', 'auto', 100),
        ('best', 'auto', 'auto', None),
    ]
    
    print("FORMAT STRING COMPARISON")
    print("=" * 80)
    
    for quality, format_type, codec, size_limit in test_cases:
        print(f"\nTest: quality={quality}, format={format_type}, codec={codec}, size={size_limit}MB")
        print("-" * 60)
        
        current = current_build_video_format_string(quality, format_type, codec, size_limit)
        improved = improved_build_video_format_string(quality, format_type, codec, size_limit)
        
        print("CURRENT (problematic):")
        print(f"  {current}")
        print(f"  Length: {len(current)} chars")
        print(f"  Options: {len(current.split('/'))}")
        
        print("\nIMPROVED (simplified):")
        print(f"  {improved}")
        print(f"  Length: {len(improved)} chars")
        print(f"  Options: {len(improved.split('/'))}")

def identify_specific_issues():
    """Identify specific issues in the current implementation."""
    print("\n\nSPECIFIC ISSUES IDENTIFIED:")
    print("=" * 80)
    
    print("\n1. CODEC PARAMETER IGNORED")
    print("   - video_codec parameter is accepted but never used")
    print("   - Users can select h264, h265, vp9, av1 but it has no effect")
    print("   - This could lead to unexpected codec selection")
    
    print("\n2. OVERLY COMPLEX FORMAT STRINGS")
    current = current_build_video_format_string('1080', 'mp4', 'h264', None)
    print(f"   - Current generates: {len(current.split('/'))} fallback options")
    print(f"   - String length: {len(current)} characters")
    print("   - Too many options can confuse yt-dlp's selection logic")
    
    print("\n3. CONTRADICTORY FORMAT OPTIONS")
    print("   - Mixes specific format requests with generic fallbacks")
    print("   - Example: 'bestvideo[ext=mp4]+bestaudio' followed by 'best[ext=mp4]'")
    print("   - This can cause yt-dlp to select suboptimal formats")
    
    print("\n4. MISSING FILE SIZE HANDLING")
    print("   - file_size_limit parameter is accepted but ignored")
    print("   - Users can't actually limit file sizes")
    
    print("\n5. REDUNDANT AUDIO SELECTION")
    print("   - Repeatedly tries 'bestaudio[ext=m4a]/bestaudio'")
    print("   - Creates unnecessary complexity")

def demonstrate_corruption_causes():
    """Show how current format strings could cause corruption."""
    print("\n\nPOTENTIAL CORRUPTION CAUSES:")
    print("=" * 80)
    
    print("\n1. FORMAT SELECTION CONFLICTS")
    print("   - Complex format strings can cause yt-dlp to select incompatible streams")
    print("   - Video stream might be selected from different source than audio")
    print("   - This can lead to sync issues or corruption during merging")
    
    print("\n2. CODEC MISMATCHES")
    print("   - Without proper codec filtering, unexpected codecs may be selected")
    print("   - Some codecs may not be properly supported by FFmpeg")
    print("   - Transcoding failures can result in corrupted output")
    
    print("\n3. FALLBACK CHAIN ISSUES")
    print("   - Long fallback chains can select very different quality/format")
    print("   - Final 'best' fallback might select a single stream instead of video+audio")
    print("   - This can bypass the proper merging process")
    
    print("\n4. POSTPROCESSOR CONFLICTS")
    print("   - Format strings might select formats that conflict with postprocessors")
    print("   - Example: Selecting MP4 video but then trying to convert to AVI")
    print("   - Double conversion can introduce corruption")

if __name__ == "__main__":
    analyze_format_strings()
    identify_specific_issues()
    demonstrate_corruption_causes()