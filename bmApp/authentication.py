from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings

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


class UserEntityTokenRefreshSerializer(TokenRefreshSerializer):

    def validate(self, attrs):
        refresh = self.token_class(attrs['refresh'])

        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM, None)
        if user_id is None:
            raise AuthenticationFailed(
                self.error_messages['no_active_account'],
                code='no_active_account',
            )

        try:
            user = UserEntity.objects.get(id=user_id)
        except UserEntity.DoesNotExist:
            raise AuthenticationFailed(
                self.error_messages['no_active_account'],
                code='no_active_account',
            )

        if not user.created:
            raise AuthenticationFailed(
                self.error_messages['no_active_account'],
                code='no_active_account',
            )

        data = {'access': str(refresh.access_token)}

        if api_settings.ROTATE_REFRESH_TOKENS:
            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()
            data['refresh'] = str(refresh)

        return data