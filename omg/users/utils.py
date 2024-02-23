def new_size(image):
    """ Преобразование изображение в квадратное.
    """
    wight, height = image.size
    print(type(image))

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