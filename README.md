<p>Проект состоит из Агента - клиентской части и соответственно Сервер. 
Агент собирает и передают метрики компьютера по HTTP, то есть пока без защиты и шифрования.</p>

<p>Данные полученные на сервере от агента записываются в базу данных (пока через SQLite), 
в перспективе для визуального отображения прошлой инфы на графике, но пока только запись.
Также присутствует логирование и дешборт для сервера, с отображением всех подключений.</p>

## Запуск сервера
1. Скачиваем [MonitoringServer.exe](https://github.com/RomanNeZloy/GraduationWork/releases/tag/V0.1); 
2. Запускаем его от имени администратор либо вручную, либо через терминал (об аргументах ниже);
3. Оно работает;
4. Если хотим завершить работу ctrl + C.

## Запуск Агента
1. Скачиваем [MonitoringAgent.exe](https://github.com/RomanNeZloy/GraduationWork/releases/tag/V0.1) и config.yaml;
2. В конфиге находим host и в водим ip компьютера, на котором сервер;
3. Запускаем его от имени администратор либо вручную, либо через терминал (об аргументах ниже);
4. Оно работает;

### server_main.py — Точка входа сервера мониторинга.

Запуск:
    <H4>python server_main.py                          # дефолтный конфиг</H4>
    <H4>python server_main.py --port 9000              # другой порт</H4>
    <H4>python server_main.py --no-dashboard           # без дашборда</H4>
    <H4>python server_main.py --refresh 2              # обновление каждые 2 сек</H4>
    <H4>python server_main.py --db                     # путь к БД
    <H4>python server_main.py --no-dashboard           # без дашборда
    <H4>python server_main.py --refresh                # частота обновления дашборда
    <H4>python server_main.py --debug                  # тладочные логи

### agent_main.py — Точка входа агента мониторинга.

Запуск:
    <H4>python agent_main.py                                # дефолтный конфиг</H4>
    <H4>python agent_main.py --config my_config.yaml        # свой конфиг</H4>
    <H4>python agent_main.py --server http://10.0.0.1:8000  # переопределить сервер</H4>
    <H4>python agent_main.py --interval 10                  # переопределить интервал</H4>
    <H4>python agent_main.py --config                       # Путь к конфигу
    <H4>python agent_main.py --debug                        # Отладочные логи
    <H4>python agent_main.py --quiet                        # Только логи ошибки

