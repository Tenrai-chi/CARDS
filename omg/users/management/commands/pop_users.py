import json
import os

from django.core.management.base import BaseCommand

from users.models import GuildBuff


class Command(BaseCommand):
    help = 'Заполняет базу для приложения users данными из json файлов'

    def handle(self, *args, **kwargs):
        """ Запуск функций загрузки данных приложения users """

        self.load_guild_buff()

    def load_guild_buff(self):
        """ Заполняет список усилений гильдии """

        try:
            file_path = os.path.join(os.path.dirname(__file__), 'db_info/guild_buff.json')
            with open(file_path, 'r', encoding='utf-8') as js:
                data = json.load(js)
            all_guild_buff = data.get('guild_buff', [])

            for guild_buff in all_guild_buff:
                existing_guild_buff = GuildBuff.objects.filter(name=guild_buff['name']).first()
                if existing_guild_buff:
                    self.stdout.write(f'Усиление гильдии {guild_buff["name"]} уже существует. Пропускаем.')
                    continue
                new_guild_buff = GuildBuff(name=guild_buff['name'],
                                           description=guild_buff['description'],
                                           numeric_value=guild_buff['numeric_value'])
                new_guild_buff.save()
                self.stdout.write(self.style.SUCCESS(f'Успешно добавлена редкость амулета: {guild_buff["name"]}'))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл "amulet_rarity.json" не найден.'))
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при разборе JSON: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла непредвиденная ошибка: {e}'))
