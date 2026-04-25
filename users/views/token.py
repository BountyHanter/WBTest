from rest_framework_simplejwt.views import TokenObtainPairView
from users.serializers.token import EmailTokenObtainPairSerializer


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer