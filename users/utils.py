from PIL.Image import Image

from django.conf import settings
from django.core.signing import TimestampSigner
from django.urls import reverse

signer = TimestampSigner()


def new_size(image: Image) -> Image:
    """ Преобразование изображение в квадратное. """

    wight, height = image.size

    if wight >= height:  # Если ширина больше высоты
        x1 = round((wight - height) / 2)
        y1 = 0
        x2 = round((wight - height) / 2 + height)
        y2 = height
        img_area = (x1, y1, x2, y2)

        image = image.crop(img_area)

    else:  # Если высота больше ширины
        x1 = 0
        y1 = round((height - wight) / 2)
        x2 = wight
        y2 = round((height - wight) / 2 + wight)

        img_area = (x1, y1, x2, y2)

        image = image.crop(img_area)

    return image


def generate_verification_url(user_id: int) -> str:
    """ Возвращает абсолютный URL для подтверждения email """

    signed_value = signer.sign(user_id)
    path = reverse('verify_email', kwargs={'signed_value': signed_value})
    return settings.SITE_URL + path
