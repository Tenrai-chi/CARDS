import json
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from cards.models import ClassCard, Type, Rarity, CardStore, News


class Command(BaseCommand):
    help = 'Заполняет базу для приложения cards данными из json файлов'

    def handle(self, *args, **kwargs):
        """ Запуск функций загрузки данных приложения cards """

        self._load_class_card()
        self._load_type_card()
        self._load_rarity_card()
        self._load_card_store()
        self._load_news()

    def _load_class_card(self):
        """ Заполняет класс карт """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/class_card.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            classes = data.get('class_card', [])

            new_records = []
            for class_card in classes:
                if not ClassCard.objects.filter(name=class_card['name']).exists():
                    new_class_card = ClassCard(name=class_card['name'],
                                               skill=class_card['skill'],
                                               description=class_card['description'],
                                               description_for_history_fight=class_card['description_for_history_fight'],
                                               numeric_value=class_card['numeric_value'],
                                               chance_use=class_card['chance_use'],
                                               image=class_card['image'])
                    new_records.append(new_class_card)
                    self.stdout.write(self.style.SUCCESS(f'Добавлен класс: {class_card["name"]}'))

            with transaction.atomic():
                ClassCard.objects.bulk_create(new_records)
                print(f'Зарегистрировано {len(new_records)} классов в class_card')

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "class_card.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))

    def _load_type_card(self):
        """ Заполняет тип карт """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/type_card.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            types = data.get('type', [])

            new_records = []
            for type_card in types:
                if not Type.objects.filter(name=type_card['name']).exists():
                    new_type_card = Type(name=type_card['name'])
                    new_records.append(new_type_card)
                    self.stdout.write(self.style.SUCCESS(f'Добавлен тип: {type_card["name"]}'))

            with transaction.atomic():
                Type.objects.bulk_create(new_records)
                print(f'Зарегистрировано {len(new_records)} типов в type')

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

    def _load_rarity_card(self):
        """ Заполняет редкость карт """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/rarity_card.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            all_rarity = data.get('rarity', [])

            new_records = []
            for rarity in all_rarity:
                if not Rarity.objects.filter(name=rarity['name']).exists():
                    new_rarity_card = Rarity(name=rarity['name'],
                                             max_level=rarity['max_level'],
                                             coefficient_damage_for_level=rarity['coefficient_damage_for_level'],
                                             coefficient_hp_for_level=rarity['coefficient_hp_for_level'],
                                             min_hp=rarity['min_hp'],
                                             max_hp=rarity['max_hp'],
                                             min_damage=rarity['min_damage'],
                                             max_damage=rarity['max_damage'],
                                             drop_chance=rarity['drop_chance'])
                    new_records.append(new_rarity_card)
                    self.stdout.write(self.style.SUCCESS(f'Добавлена редкость: {rarity["name"]}'))
            with transaction.atomic():
                Rarity.objects.bulk_create(new_records)
                print(f'Зарегистрировано {len(new_records)} редкостей в rarity')

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "rarity_card.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))

    def _load_card_store(self):
        """ Заполняет магазин карт.
            ОСТОРОЖНО, не проверяет бд на наличие аналогичной записи.
        """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/card_store.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            card_store = data.get('card_store', [])

            all_class_card_list = list(ClassCard.objects.all())
            all_class_types_list = list(Type.objects.all())
            all_class_rarity_list = list(Rarity.objects.all())

            new_records = []
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
                new_records.append(new_card_store)
                self.stdout.write(self.style.SUCCESS(f'Добавлена карта в магазин'))
            with transaction.atomic():
                CardStore.objects.bulk_create(new_records)
                print(f'Зарегистрировано {len(new_records)} карт в card_store')

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "card_store.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))

    def _load_news(self):
        """ Заполняет новости сайта """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/news.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            all_news = data.get('news', [])

            new_records = []
            for news in all_news:
                if not News.objects.filter(title=news['title']).exists():
                    new_news = News(title=news['title'],
                                    theme=news['theme'],
                                    text=news['text'],
                                    date_time_create=news['date_time_create'])
                    new_records.append(new_news)
                    self.stdout.write(self.style.SUCCESS(f'Добавлена новость'))
            with transaction.atomic():
                News.objects.bulk_create(new_records)
                print(f'Зарегистрировано {len(new_records)} новостей в news')

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "news.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))
