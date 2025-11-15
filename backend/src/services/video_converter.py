"""
Video conversion service using FFmpeg for platform-specific video requirements.
"""
import os
import tempfile
from typing import Dict, Optional, Tuple
from pathlib import Path
import ffmpeg
from enum import Enum

from src.models.database_models import PlatformEnum


class VideoFormat(str, Enum):
    """Supported video formats"""
    MP4 = "mp4"
    MOV = "mov"
    AVI = "avi"
    WEBM = "webm"


class PlatformVideoSpecs:
    """Platform-specific video specifications"""
    
    TIKTOK = {
        "format": "mp4",
        "video_codec": "libx264",
        "audio_codec": "aac",
        "max_duration": 600,  # 10 minutes
        "min_duration": 3,
        "max_size_mb": 287,
        "max_resolution": (1920, 1080),
        "aspect_ratios": [(9, 16), (16, 9), (1, 1)],
        "fps": 30,
        "video_bitrate": "5000k",
        "audio_bitrate": "128k"
    }
    
    YOUTUBE = {
        "format": "mp4",
        "video_codec": "libx264",
        "audio_codec": "aac",
        "max_duration": 60,  # Shorts limit
        "min_duration": 1,
        "max_size_mb": 256,
        "max_resolution": (1920, 1080),
        "aspect_ratios": [(9, 16)],  # Shorts are vertical
        "fps": 30,
        "video_bitrate": "5000k",
        "audio_bitrate": "128k"
    }
    
    INSTAGRAM = {
        "format": "mp4",
        "video_codec": "libx264",
        "audio_codec": "aac",
        "max_duration": 90,  # Reels limit
        "min_duration": 3,
        "max_size_mb": 100,
        "max_resolution": (1920, 1080),
        "aspect_ratios": [(9, 16)],  # Reels are vertical
        "fps": 30,
        "video_bitrate": "3500k",
        "audio_bitrate": "128k"
    }
    
    FACEBOOK = {
        "format": "mp4",
        "video_codec": "libx264",
        "audio_codec": "aac",
        "max_duration": 240,  # 4 minutes
        "min_duration": 1,
        "max_size_mb": 1024,
        "max_resolution": (1920, 1080),
        "aspect_ratios": [(9, 16), (16, 9), (1, 1)],
        "fps": 30,
        "video_bitrate": "5000k",
        "audio_bitrate": "128k"
    }
    
    @classmethod
    def get_specs(cls, platform: PlatformEnum) -> Dict:
        """Get specifications for a platform"""
        specs_map = {
            PlatformEnum.TIKTOK: cls.TIKTOK,
            PlatformEnum.YOUTUBE: cls.YOUTUBE,
            PlatformEnum.INSTAGRAM: cls.INSTAGRAM,
            PlatformEnum.FACEBOOK: cls.FACEBOOK
        }
        return specs_map.get(platform, cls.TIKTOK)


class VideoConversionError(Exception):
    """Raised when video conversion fails"""
    pass


class VideoValidationError(Exception):
    """Raised when video validation fails"""
    pass


class VideoConverter:
    """Service for converting videos to platform-specific formats"""
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    def detect_format(self, video_path: str) -> Dict:
        """
        Detect video format and properties using FFmpeg probe.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Dictionary containing video metadata
            
        Raises:
            VideoValidationError: If video cannot be probed
        """
        try:
            probe = ffmpeg.probe(video_path)
            
            video_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
                None
            )
            audio_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'audio'),
                None
            )
            
            if not video_stream:
                raise VideoValidationError("No video stream found in file")
            
            duration = float(probe['format'].get('duration', 0))
            file_size = int(probe['format'].get('size', 0))
            
            return {
                'format': probe['format']['format_name'],
                'duration': duration,
                'file_size': file_size,
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'video_codec': video_stream.get('codec_name'),
                'audio_codec': audio_stream.get('codec_name') if audio_stream else None,
                'fps': eval(video_stream.get('r_frame_rate', '30/1')),
                'bitrate': int(probe['format'].get('bit_rate', 0))
            }
        except ffmpeg.Error as e:
            raise VideoValidationError(f"Failed to probe video: {e.stderr.decode() if e.stderr else str(e)}")
        except Exception as e:
            raise VideoValidationError(f"Failed to detect video format: {str(e)}")
    
    def validate_video(self, video_path: str, platform: PlatformEnum) -> Tuple[bool, Optional[str]]:
        """
        Validate if video meets platform requirements.
        
        Args:
            video_path: Path to the video file
            platform: Target platform
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            metadata = self.detect_format(video_path)
            specs = PlatformVideoSpecs.get_specs(platform)
            
            # Check duration
            if metadata['duration'] < specs['min_duration']:
                return False, f"Video too short (min {specs['min_duration']}s)"
            if metadata['duration'] > specs['max_duration']:
                return False, f"Video too long (max {specs['max_duration']}s)"
            
            # Check file size
            size_mb = metadata['file_size'] / (1024 * 1024)
            if size_mb > specs['max_size_mb']:
                return False, f"File too large (max {specs['max_size_mb']}MB)"
            
            # Check resolution
            if metadata['width'] > specs['max_resolution'][0] or metadata['height'] > specs['max_resolution'][1]:
                return False, f"Resolution too high (max {specs['max_resolution'][0]}x{specs['max_resolution'][1]})"
            
            # Check format
            supported_formats = [VideoFormat.MP4.value, VideoFormat.MOV.value, 
                               VideoFormat.AVI.value, VideoFormat.WEBM.value]
            if not any(fmt in metadata['format'].lower() for fmt in supported_formats):
                return False, f"Unsupported format: {metadata['format']}"
            
            return True, None
            
        except VideoValidationError as e:
            return False, str(e)
    
    def convert_for_platform(
        self,
        input_path: str,
        output_path: str,
        platform: PlatformEnum,
        preserve_quality: bool = True
    ) -> str:
        """
        Convert video to platform-specific format.
        
        Args:
            input_path: Path to input video
            output_path: Path for output video
            platform: Target platform
            preserve_quality: If True, use CRF for quality preservation (max 5% loss)
            
        Returns:
            Path to converted video
            
        Raises:
            VideoConversionError: If conversion fails
        """
        try:
            specs = PlatformVideoSpecs.get_specs(platform)
            
            # Build FFmpeg command
            stream = ffmpeg.input(input_path)
            
            # Video encoding options
            video_options = {
                'vcodec': specs['video_codec'],
                'video_bitrate': specs['video_bitrate'],
                'r': specs['fps']
            }
            
            # Use CRF for quality preservation (18 = high quality, ~5% loss)
            if preserve_quality:
                video_options['crf'] = 18
                video_options['preset'] = 'slow'  # Better compression
                del video_options['video_bitrate']  # CRF overrides bitrate
            
            # Audio encoding options
            audio_options = {
                'acodec': specs['audio_codec'],
                'audio_bitrate': specs['audio_bitrate']
            }
            
            # Scale video if needed (maintain aspect ratio)
            max_width, max_height = specs['max_resolution']
            video = stream.video.filter('scale', f'min({max_width},iw)', f'min({max_height},ih)')
            audio = stream.audio
            
            # Output
            output = ffmpeg.output(
                video,
                audio,
                output_path,
                format=specs['format'],
                **video_options,
                **audio_options
            )
            
            # Run conversion
            ffmpeg.run(output, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            
            # Verify output exists
            if not os.path.exists(output_path):
                raise VideoConversionError("Output file was not created")
            
            return output_path
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            raise VideoConversionError(f"FFmpeg conversion failed: {error_msg}")
        except Exception as e:
            raise VideoConversionError(f"Video conversion failed: {str(e)}")
    
    def get_conversion_requirements(
        self,
        video_path: str,
        platform: PlatformEnum
    ) -> Dict:
        """
        Determine if conversion is needed and what changes are required.
        
        Args:
            video_path: Path to video file
            platform: Target platform
            
        Returns:
            Dictionary with conversion requirements
        """
        metadata = self.detect_format(video_path)
        specs = PlatformVideoSpecs.get_specs(platform)
        
        needs_conversion = False
        changes = []
        
        # Check codec
        if metadata['video_codec'] != specs['video_codec'].replace('lib', ''):
            needs_conversion = True
            changes.append(f"video_codec: {metadata['video_codec']} -> {specs['video_codec']}")
        
        if metadata['audio_codec'] and metadata['audio_codec'] != specs['audio_codec']:
            needs_conversion = True
            changes.append(f"audio_codec: {metadata['audio_codec']} -> {specs['audio_codec']}")
        
        # Check resolution
        if metadata['width'] > specs['max_resolution'][0] or metadata['height'] > specs['max_resolution'][1]:
            needs_conversion = True
            changes.append(f"resolution: {metadata['width']}x{metadata['height']} -> max {specs['max_resolution'][0]}x{specs['max_resolution'][1]}")
        
        # Check format
        if specs['format'] not in metadata['format'].lower():
            needs_conversion = True
            changes.append(f"format: {metadata['format']} -> {specs['format']}")
        
        return {
            'needs_conversion': needs_conversion,
            'changes': changes,
            'current_metadata': metadata,
            'target_specs': specs
        }
