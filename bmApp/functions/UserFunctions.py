import random
from django.core.mail import send_mail
from django.conf import settings

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