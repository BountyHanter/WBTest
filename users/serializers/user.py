from rest_framework import serializers


class UserSerializer(serializers.Serializer):
    email = serializers.EmailField(read_only=True)
