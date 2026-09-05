from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from .models import UserEntity


class UserEntityJWTAuthentication(JWTAuthentication):

    def get_user(self, validated_token):
        user_id = validated_token.get('user_id')

        if user_id is None:
            raise AuthenticationFailed(
                'Token does not contain user_id'
            )

        try:
            user = UserEntity.objects.get(id=user_id)
        except UserEntity.DoesNotExist:
            raise AuthenticationFailed(
                'User not found'
            )

        if not user.created:
            raise AuthenticationFailed(
                'User is not verified'
            )

        return user