import os
import random
from django.core.mail import send_mail
from django.conf import settings

EXTERNAL_PHOTO_PREFIXES = ('http://', 'https://', 'data:')


def is_external_photo(photo):
    return bool(photo) and photo.startswith(EXTERNAL_PHOTO_PREFIXES)


def user_photo_url(request, photo):
    if not photo:
        return None

    if is_external_photo(photo):
        return photo

    return request.build_absolute_uri(f'{settings.MEDIA_URL}{photo}')


def remove_user_photo_file(photo):
    if is_external_photo(photo):
        return

    media_root = os.path.abspath(settings.MEDIA_ROOT)
    file_path = os.path.abspath(os.path.join(media_root, photo or ''))

    if not file_path.startswith(media_root + os.sep):
        return

    if os.path.isfile(file_path):
        os.remove(file_path)


def send_auth_code(email):
    code = str(random.randint(100000, 999999))

    send_mail(
        subject="Authorization",
        message=f"Your authorization code: {code}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )

    return code