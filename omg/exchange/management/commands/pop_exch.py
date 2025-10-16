import json
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from exchange.models import (ExperienceItems, AmuletRarity, AmuletType, UpgradeItemsType,
                             InitialEventAwards, BattleEventAwards)


class Command(BaseCommand):
    help = 'Заполняет базу для приложения exchange данными из json файлов'

    def handle(self, *args, **kwargs):
        """ Запуск функций загрузки данных приложения exchange """

        self._load_amulet_rarity()
        self._load_amulet_type()
        self._load_experience_items()
        self._load_upgrade_items_type()
        self._load_start_event_awards()
        self._load_battle_event_awards()

    def _load_amulet_rarity(self):
        """ Заполняет редкость амулетов """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/amulet_rarity.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            all_amulet_rarity = data.get('amulet_rarity', [])

            new_records = []
            for rarity in all_amulet_rarity:
                if not AmuletRarity.objects.filter(name=rarity['name']).exists():
                    new_amulet_rarity = AmuletRarity(name=rarity['name'],
                                                     chance_drop_on_fight=rarity['chance_drop_on_fight'],
                                                     chance_drop_on_box=rarity['chance_drop_on_box'],
                                                     max_upgrade=rarity['max_upgrade'])
                    new_records.append(new_amulet_rarity)
                    self.stdout.write(self.style.SUCCESS(f'Добавлена редкость амулета: {rarity["name"]}'))
            with transaction.atomic():
                AmuletRarity.objects.bulk_create(new_records)
                print(f'Зарегистрировано {len(new_records)} редкостей в amulet_rarity')

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "amulet_rarity.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))

    def _load_amulet_type(self):
        """ Заполняет типы амулетов """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/amulet_type.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            all_amulet_type = data.get('amulet_type', [])

            all_amulet_rarity = AmuletRarity.objects.all()

            new_records = []
            for amulet_type in all_amulet_type:
                if not AmuletType.objects.filter(name=amulet_type['name']).exists():
                    new_amulet_type = AmuletType(name=amulet_type['name'],
                                                 bonus_hp=amulet_type['bonus_hp'],
                                                 bonus_damage=amulet_type['bonus_damage'],
                                                 price=amulet_type['price'],
                                                 sale_now=amulet_type['sale_now'],
                                                 image=amulet_type['image'],
                                                 discount=amulet_type['discount'],
                                                 discount_now=amulet_type['discount_now'],
                                                 rarity=all_amulet_rarity[amulet_type['rarity'] - 1])
                    new_records.append(new_amulet_type)
                    self.stdout.write(self.style.SUCCESS(f'Добавлен тип амулета: {amulet_type["name"]}'))
            with transaction.atomic():
                AmuletType.objects.bulk_create(new_records)
                print(f'Зарегистрировано {len(new_records)} типов в amulet_type')

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "amulet_type.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))

    def _load_experience_items(self):
        """ Заполняет предметы опыта """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/experience_items.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            all_experience_items = data.get('experience_items', [])

            new_records = []
            for experience_items in all_experience_items:
                if not ExperienceItems.objects.filter(name=experience_items['name']).exists():
                    new_exp_item = ExperienceItems(name=experience_items['name'],
                                                   rarity=experience_items['rarity'],
                                                   experience_amount=experience_items['experience_amount'],
                                                   chance_drop_on_fight=experience_items['chance_drop_on_fight'],
                                                   chance_drop_on_box=experience_items['chance_drop_on_box'],
                                                   price=experience_items['price'],
                                                   image=experience_items['image'],
                                                   gold_for_use=experience_items['gold_for_use'],
                                                   sale_now=experience_items['sale_now'])
                    new_records.append(new_exp_item)
                    self.stdout.write(self.style.SUCCESS(f'Добавлен предмет опыта: {experience_items["name"]}'))
            with transaction.atomic():
                ExperienceItems.objects.bulk_create(new_records)
                print(f'Зарегистрировано {len(new_records)} предметов опыта в experience_items')

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "experience_items.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))

    def _load_upgrade_items_type(self):
        """ Заполняет типы предметов для улучшения амулетов """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/upgrade_items_type.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            all_up_item_type = data.get('upgrade_items_type', [])

            new_records = []
            for up_item in all_up_item_type:
                if not UpgradeItemsType.objects.filter(name=up_item['name']).exists():
                    new_up_item = UpgradeItemsType(name=up_item['name'],
                                                   description=up_item['description'],
                                                   type=up_item['type'],
                                                   amount_up=up_item['amount_up'],
                                                   image=up_item['image'],
                                                   price=up_item['price'],
                                                   price_of_use=up_item['price_of_use'],)
                    new_records.append(new_up_item)
                    self.stdout.write(self.style.SUCCESS(f'Добавлен предмет улучшения амулета: {up_item["name"]}'))
            with transaction.atomic():
                UpgradeItemsType.objects.bulk_create(new_records)
                print(f'Зарегистрировано {len(new_records)} предметов улучшения в upgrade_items_type')

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "upgrade_items_type.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))

    def _load_start_event_awards(self):
        """ Заполняет таблицу с наградами стартового события """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/start_event_awards.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            event_awards = data.get('event_awards', [])

            new_records = []
            for event in event_awards:
                if not InitialEventAwards.objects.filter(day_event_visit=event['day_event_visit']).exists():
                    new_award = InitialEventAwards.objects.create(day_event_visit=event['day_event_visit'],
                                                                  type_award=event['type_award'],
                                                                  amount_or_rarity_award=event['amount_or_rarity_award'],
                                                                  description=event['description'])
                    new_award.save()
                    self.stdout.write(self.style.SUCCESS(f'Добавлен награда {event["day_event_visit"]} дня'))
            with transaction.atomic():
                InitialEventAwards.objects.bulk_create(new_records)
                print(f'Зарегистрировано {len(new_records)} наград в start_event_awards')

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "start_event_awards.json" не найден.'))

        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))

    def _load_battle_event_awards(self):
        """ Заполняет таблицу с наградами боевого события """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/battle_event_awards.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            event_awards = data.get('event_awards', [])

            new_records = []
            for event in event_awards:
                if not BattleEventAwards.objects.filter(rank=event['rank']).exists():
                    new_award = BattleEventAwards.objects.create(rank=event['rank'],
                                                                 award=event['award'],
                                                                 amount=event['amount'])
                    new_records.append(new_award)
                    self.stdout.write(self.style.SUCCESS(f'Добавлен награда {event["rank"]} ранга'))
            with transaction.atomic():
                BattleEventAwards.objects.bulk_create(new_records)
                print(f'Зарегистрировано {len(new_records)} наград в battle_event_awards')

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "battle_event_awards.json" не найден.'))

        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))
