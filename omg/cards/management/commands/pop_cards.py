import json
import os

from django.core.management.base import BaseCommand

from cards.models import ClassCard, Type, Rarity, CardStore


class Command(BaseCommand):
    help = 'Заполняет базу для приложения cards данными из json файлов'

    def handle(self, *args, **kwargs):
        """ Запуск функций загрузки данных приложения cards """

        self.load_class_card()
        self.load_type_card()
        self.load_rarity_card()
        self.load_card_store()

    def load_class_card(self):
        """ Заполняет класс карт """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/class_card.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            classes = data.get('class_card', [])

            for class_card in classes:
                existing_class = ClassCard.objects.filter(name=class_card['name']).first()
                if existing_class:
                    self.stdout.write(f'Класс {class_card["name"]} уже существует. Пропускаем.')
                    continue
                new_class_card = ClassCard(name=class_card['name'],
                                           skill=class_card['skill'],
                                           description=class_card['description'],
                                           description_for_history_fight=class_card['description_for_history_fight'],
                                           numeric_value=class_card['numeric_value'],
                                           chance_use=class_card['chance_use'],
                                           image=class_card['image'])
                new_class_card.save()
                self.stdout.write(self.style.SUCCESS(f'Успешно добавлен класс: {class_card["name"]}'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "class_card.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))

    def load_type_card(self):
        """ Заполняет тип карт """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/type_card.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            types = data.get('type', [])

            for type_card in types:
                existing_type = Type.objects.filter(name=type_card['name']).first()
                if existing_type:
                    self.stdout.write(f'Тип {type_card["name"]} уже существует. Пропускаем.')
                    continue
                new_type_card = Type(name=type_card['name'])
                new_type_card.save()
                self.stdout.write(self.style.SUCCESS(f'Успешно добавлен тип: {type_card["name"]}'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "type_card.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))

        try:
            all_type = list(Type.objects.all())
            green_type = all_type[0]
            red_type = all_type[1]
            blue_type = all_type[2]

            green_type.better = blue_type
            green_type.worst = red_type
            green_type.save()

            red_type.better = green_type
            red_type.worst = blue_type
            red_type.save()

            blue_type.better = red_type
            blue_type.worst = green_type
            blue_type.save()

            self.stdout.write(self.style.SUCCESS('Связи между типами карт успешно установлены.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла ошибка при установке связи: {e}'))

    def load_rarity_card(self):
        """ Заполняет редкость карт """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/rarity_card.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            all_rarity = data.get('rarity', [])

            for rarity in all_rarity:
                existing_rarity = Rarity.objects.filter(name=rarity['name']).first()
                if existing_rarity:
                    self.stdout.write(f'Тип {rarity["name"]} уже существует. Пропускаем.')
                    continue
                new_rarity_card = Rarity(name=rarity['name'],
                                         max_level=rarity['max_level'],
                                         coefficient_damage_for_level=rarity['coefficient_damage_for_level'],
                                         coefficient_hp_for_level=rarity['coefficient_hp_for_level'],
                                         min_hp=rarity['min_hp'],
                                         max_hp=rarity['max_hp'],
                                         min_damage=rarity['min_damage'],
                                         max_damage=rarity['max_damage'],
                                         drop_chance=rarity['drop_chance'], )
                new_rarity_card.save()
                self.stdout.write(self.style.SUCCESS(f'Успешно добавлена редкость: {rarity["name"]}'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "rarity_card.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))

    def load_card_store(self):
        """ Заполняет магазин карт """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/card_store.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            card_store = data.get('card_store', [])

            all_class_card_list = list(ClassCard.objects.all())
            all_class_types_list = list(Type.objects.all())
            all_class_rarity_list = list(Rarity.objects.all())

            for card in card_store:
                new_card_store = CardStore(class_card=all_class_card_list[card['class_card'] - 1],
                                           type=all_class_types_list[card['type'] - 1],
                                           rarity=all_class_rarity_list[card['rarity'] - 1],
                                           hp=card['hp'],
                                           damage=card['damage'],
                                           sale_now=card['sale_now'],
                                           price=card['price'],
                                           discount=card['discount'],
                                           discount_now=card['discount_now'])
                new_card_store.save()
                self.stdout.write(self.style.SUCCESS(f'Успешно добавлена карта в магазин'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "card_store.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))
