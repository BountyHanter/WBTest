from rest_framework import serializers

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=6)