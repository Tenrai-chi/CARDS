import json
import os

from django.core.management.base import BaseCommand

from exchange.models import ExperienceItems, AmuletRarity, AmuletType, UpgradeItemsType


class Command(BaseCommand):
    help = 'Заполняет базу для приложения exchange данными из json файлов'

    def handle(self, *args, **kwargs):
        """ Запуск функций загрузки данных приложения exchange """

        self.load_amulet_rarity()
        self.load_amulet_type()
        self.load_experience_items()
        self.load_upgrade_items_type()

    def load_amulet_rarity(self):
        """ Заполняет редкость амулетов """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/amulet_rarity.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            all_amulet_rarity = data.get('amulet_rarity', [])

            for rarity in all_amulet_rarity:
                existing_rarity = AmuletRarity.objects.filter(name=rarity['name']).first()
                if existing_rarity:
                    self.stdout.write(f'Редкость амулета {rarity["name"]} уже существует. Пропускаем.')
                    continue
                new_amulet_rarity = AmuletRarity(name=rarity['name'],
                                                 chance_drop_on_fight=rarity['chance_drop_on_fight'],
                                                 chance_drop_on_box=rarity['chance_drop_on_box'],
                                                 max_upgrade=rarity['max_upgrade'])
                new_amulet_rarity.save()
                self.stdout.write(self.style.SUCCESS(f'Успешно добавлена редкость амулета: {rarity["name"]}'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "amulet_rarity.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))

    def load_amulet_type(self):
        """ Заполняет типы амулетов """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/amulet_type.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            all_amulet_type = data.get('amulet_type', [])

            all_amulet_rarity = AmuletRarity.objects.all()

            for amulet_type in all_amulet_type:
                existing_type = AmuletType.objects.filter(name=amulet_type['name']).first()
                if existing_type:
                    self.stdout.write(f'Редкость амулета {amulet_type["name"]} уже существует. Пропускаем.')
                    continue

                new_amulet_type = AmuletType(name=amulet_type['name'],
                                             bonus_hp=amulet_type['bonus_hp'],
                                             bonus_damage=amulet_type['bonus_damage'],
                                             price=amulet_type['price'],
                                             sale_now=amulet_type['sale_now'],
                                             image=amulet_type['image'],
                                             discount=amulet_type['discount'],
                                             discount_now=amulet_type['discount_now'],
                                             rarity=all_amulet_rarity[amulet_type['rarity'] - 1])
                new_amulet_type.save()
                self.stdout.write(self.style.SUCCESS(f'Успешно добавлен тип амулета: {amulet_type["name"]}'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "amulet_type.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))

    def load_experience_items(self):
        """ Заполняет предметы опыта """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/experience_items.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            all_experience_items = data.get('experience_items', [])

            for experience_items in all_experience_items:
                existing_exp_item = ExperienceItems.objects.filter(name=experience_items['name']).first()
                if existing_exp_item:
                    self.stdout.write(f'Предмет опыта {experience_items["name"]} уже существует. Пропускаем.')
                    continue
                new_exp_item = ExperienceItems(name=experience_items['name'],
                                               rarity=experience_items['rarity'],
                                               experience_amount=experience_items['experience_amount'],
                                               chance_drop_on_fight=experience_items['chance_drop_on_fight'],
                                               chance_drop_on_box=experience_items['chance_drop_on_box'],
                                               price=experience_items['price'],
                                               image=experience_items['image'],
                                               gold_for_use=experience_items['gold_for_use'],
                                               sale_now=experience_items['sale_now'])
                new_exp_item.save()
                self.stdout.write(self.style.SUCCESS(f'Успешно добавлен предмет опыта: {experience_items["name"]}'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "experience_items.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))

    def load_upgrade_items_type(self):
        """ Заполняет типы предметов для улучшения амулетов """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/upgrade_items_type.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            all_up_item_type = data.get('upgrade_items_type', [])

            for up_item in all_up_item_type:
                existing_up_item = UpgradeItemsType.objects.filter(name=up_item['name']).first()
                if existing_up_item:
                    self.stdout.write(f'Предмет улучшения амулета {up_item["name"]} уже существует. Пропускаем.')
                    continue
                new_up_item = UpgradeItemsType(name=up_item['name'],
                                               description=up_item['description'],
                                               type=up_item['type'],
                                               amount_up=up_item['amount_up'],
                                               image=up_item['image'],
                                               price=up_item['price'],
                                               price_of_use=up_item['price_of_use'],)
                new_up_item.save()
                self.stdout.write(self.style.SUCCESS(f'Успешно добавлен предмет улучшения амулета: {up_item["name"]}'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "upgrade_items_type.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))
