from rest_framework import serializers

class MediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    
    def validate_file(self, value):
        # Max file size: 500MB
        max_size = 500 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("File size exceeds 500MB limit.")
        return value

class MediaInfoSerializer(serializers.Serializer):
    filename = serializers.CharField()
    file_type = serializers.CharField()
    mime_type = serializers.CharField()
    size = serializers.IntegerField()
    duration = serializers.FloatField(required=False, allow_null=True)
    width = serializers.IntegerField(required=False, allow_null=True)
    height = serializers.IntegerField(required=False, allow_null=True)
    codec = serializers.CharField(required=False, allow_null=True)
    bitrate = serializers.IntegerField(required=False, allow_null=True)
    sample_rate = serializers.IntegerField(required=False, allow_null=True)

class ConversionOptionsSerializer(serializers.Serializer):
    format = serializers.CharField()
    quality = serializers.CharField(required=False, default='high')
    resolution = serializers.CharField(required=False)
    bitrate = serializers.CharField(required=False)
    sample_rate = serializers.IntegerField(required=False)
    fps = serializers.IntegerField(required=False)
    codec = serializers.CharField(required=False)
    audio_codec = serializers.CharField(required=False)
    channels = serializers.IntegerField(required=False)
    start_time = serializers.FloatField(required=False)
    end_time = serializers.FloatField(required=False)
    
class MediaConversionSerializer(serializers.Serializer):
    file = serializers.FileField()
    output_format = serializers.CharField()
    options = ConversionOptionsSerializer(required=False)
    
class ConversionStatusSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    status = serializers.ChoiceField(choices=['pending', 'processing', 'completed', 'failed'])
    progress = serializers.IntegerField(min_value=0, max_value=100)
    message = serializers.CharField(required=False)
    download_url = serializers.URLField(required=False)
    error = serializers.CharField(required=False)