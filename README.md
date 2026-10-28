Проект состоит из Агента - клиентской части и соответственно сервер. Они передают данные по HTTP, то есть пока без защиты и шифрования.

server_main.py — Точка входа сервера мониторинга.

Запуск:
    python server_main.py                          # дефолтный конфиг
    python server_main.py --port 9000              # другой порт
    python server_main.py --no-dashboard           # без дашборда
    python server_main.py --refresh 2              # обновление каждые 2 сек


agent_main.py — Точка входа агента мониторинга.

Запуск:
    python agent_main.py                          # дефолтный конфиг
    python agent_main.py --config my_config.yaml  # свой конфиг
    python agent_main.py --server http://10.0.0.1:8000  # переопределить сервер
    python agent_main.py --interval 10            # переопределить интервал


