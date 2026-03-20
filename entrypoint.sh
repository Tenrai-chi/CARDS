#!/bin/sh
set -e

echo "Ожидание подключения к базе данных"
/wait

echo "Запуск миграций базы данных..."
python manage.py migrate

populate_if_empty() {
    local app_label="$1"
    local model_path="$2"
    local model_name="$3"
    local command="$4"

    echo "Проверка наличия данных в $app_label ..."
    if python manage.py shell -c "from $model_path import $model_name; exit(0 if $model_name.objects.exists() else 1)"; then
        echo "Данные в $app_label уже существуют, пропуск..."
    else
        echo "Заполнение данными в $app_label ..."
        python manage.py "$command"
    fi
}

populate_if_empty "cards" "cards.models" "ClassCard" "pop_cards"
populate_if_empty "users" "users.models" "Profile" "pop_users"
populate_if_empty "exchange" "exchange.models" "BattleEventAwards" "pop_exch"

exec "$@"