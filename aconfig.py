# coding=UTF8
# IP-адрес интерфейса и порт:
interface_ip = ""
port = 1907

# Пауза при опросе UDP-сокета:
sleep_int = 0.001

# Пауза ожидания блока данных. По истечении интервала начинается обработка данных
nodata_int = 5

# Файл журнала:
logfile = "/var/log/attractor.log"

# Шаблон полного имени метрики
MetricNameTemplate = "{$device}_{$host}_{$metric}_{$key}"

# Настройки Jabber
useJabber = False
jid = "attractor@jabber.localhost"
jps = "jpass"
jcr = "nebula@conference.jabber.localhost"
jnn = "attractor"
JabberMetricsList = ['UP', 'TX', 'CT', 'CPU']

# Выполнение GET-запроса при срабатывании правил
use_external_urls = True
external_urls = ['http://']
external_requests_metrics = ['UP', 'TX', 'CT', 'CPU']

# Настройки Telegram
useTelegram = False
telegram_tokens = ['']
telegram_url = 'https://mybot.example.com/{}/send'

# Настройки MySQL
useMySQL = True
mysql_addr = "attractor.localhost"
mysql_user = "attractor"
mysql_pass = "apass"
mysql_base = "blackhole"
mysql_cset = "utf8"
mysql_tabl = "alarms"
mysql_chain_len = 10

# Настройки Oracle Apex
useOracleApex = False
apex_url = "http://oracle.localhost:8082/apex/f?p=ins:1:::::QUERY:"
apex_cmd = "INSERT INTO c##blackhole.alarms (DATETIME,EVENT_CODE,KEY_,VALUE,METRIC,HOST,DEVICE) "
apex_chain_len = 50

# Горизонт событий :)
event_horizon = {
    "RX_crc": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", "+>", "5"]], 'trigger': 3, 'skip': 9, 'reset': 12,
               'code': 1},

    "DS": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", "==", "2"]], 'trigger': 3, 'skip': 9, 'reset': 12,
           'code': 2},

    "CNS": {'terms': [["DES-3200-28_{$host}_{$metric}_{$key}", "~", ">>", "1"],
                      ["DES-3200-28_{$host}_{$metric}_25.100", "~", "<<", "0"],
                      ["DES-3200-28_{$host}_{$metric}_26.100", "~", "<<", "0"],
                      ["DES-3200-28_{$host}_{$metric}_27.100", "~", "<<", "0"],
                      ["DES-3200-28_{$host}_{$metric}_28.100", "~", "<<", "0"],

                      ["DES-3200-18_{$host}_{$metric}_{$key}", "~", ">>", "1"],
                      ["DES-3200-18_{$host}_{$metric}_25.100", "~", "<<", "0"],
                      ["DES-3200-18_{$host}_{$metric}_26.100", "~", "<<", "0"],
                      ["DES-3200-18_{$host}_{$metric}_27.100", "~", "<<", "0"],
                      ["DES-3200-18_{$host}_{$metric}_28.100", "~", "<<", "0"],

                      ["DES-3200-28_C1_{$host}_{$metric}_{$key}", "~", ">>", "2"],
                      ["DES-3200-28_C1_{$host}_{$metric}_25.1", "~", "<<", "0"],
                      ["DES-3200-28_C1_{$host}_{$metric}_26.1", "~", "<<", "0"],
                      ["DES-3200-28_C1_{$host}_{$metric}_27.1", "~", "<<", "0"],
                      ["DES-3200-28_C1_{$host}_{$metric}_28.1", "~", "<<", "0"],

                      ["DES-3200-18_C1_{$host}_{$metric}_{$key}", "~", ">>", "2"],
                      ["DES-3200-18_C1_{$host}_{$metric}_25.1", "~", "<<", "0"],
                      ["DES-3200-18_C1_{$host}_{$metric}_26.1", "~", "<<", "0"],
                      ["DES-3200-18_C1_{$host}_{$metric}_27.1", "~", "<<", "0"],
                      ["DES-3200-18_C1_{$host}_{$metric}_28.1", "~", "<<", "0"],

                      ["DES-3028_{$host}_{$metric}_{$key}", "~", ">>", "1"],
                      ["DES-3028_{$host}_{$metric}_25.100", "~", "<<", "0"],
                      ["DES-3028_{$host}_{$metric}_26.100", "~", "<<", "0"],
                      ["DES-3028_{$host}_{$metric}_27.100", "~", "<<", "0"],
                      ["DES-3028_{$host}_{$metric}_28.100", "~", "<<", "0"]], 'trigger': 3, 'skip': 9, 'reset': 12,
            'code': 3},

    "UP": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", "<-", "1"]], 'trigger': 1, 'skip': 0, 'reset': 0,
           'code': 9},

    "FW": {'terms': [["DES-3200-28_{$host}_{$metric}_{$key}", "~", "ni", "1.85"],
                     ["DES-3200-18_{$host}_{$metric}_{$key}", "~", "ni", "1.85"],
                     ["DES-3200-28_C1_{$host}_{$metric}_{$key}", "~", "ni", "4.39"],
                     ["DES-3200-18_C1_{$host}_{$metric}_{$key}", "~", "ni", "4.39"],
                     ["DES-3028_{$host}_{$metric}_{$key}", "~", "ni", "2.94"]], 'trigger': 1, 'skip': 35, 'reset': 36,
           'code': 12},

    "TX": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "937500000"],
                     ["{$device}_{$host}_{$metric}_{$key}", "RX", ">>", "937500000"],
                     ["{$device}_{$host}_{$metric}_25", "~", "<<", "0"],
                     ["{$device}_{$host}_{$metric}_26", "~", "<<", "0"],
                     ["{$device}_{$host}_{$metric}_27", "~", "<<", "0"],
                     ["{$device}_{$host}_{$metric}_28", "~", "<<", "0"]], 'trigger': 6, 'skip': 6, 'reset': 12,
           'code': 13},

    "CT": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "60"]], 'trigger': 2, 'skip': 4, 'reset': 6,
           'code': 14},

    "CPU": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "50"]], 'trigger': 2, 'skip': 4, 'reset': 6,
            'code': 15},

    "RX": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "750000000"],
                     ["{$device}_{$host}_{$metric}_25", "~", "<<", "0"],
                     ["{$device}_{$host}_{$metric}_26", "~", "<<", "0"],
                     ["{$device}_{$host}_{$metric}_27", "~", "<<", "0"],
                     ["{$device}_{$host}_{$metric}_28", "~", "<<", "0"]], 'trigger': 6, 'skip': 6, 'reset': 12,
           'code': 16},

    # На практике не используется. Здесь оставлено как пример
    "P1S": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "1"],
                      ["{$device}_{$host}_{$metric}_{$key}", "~", "<<", "5"]], 'trigger': 3, 'skip': 3, 'reset': 6,
            'code': 4},
    # На практике не используется. Здесь оставлено как пример
    "P2S": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "1"],
                      ["{$device}_{$host}_{$metric}_{$key}", "~", "<<", "5"]], 'trigger': 3, 'skip': 3, 'reset': 6,
            'code': 5},
    # На практике не используется. Здесь оставлено как пример
    "P2S/C1": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "1"],
                         ["{$device}_{$host}_{$metric}_{$key}", "~", "<<", "5"]], 'trigger': 3, 'skip': 3, 'reset': 6,
               'code': 4},
    # На практике не используется. Здесь оставлено как пример
    "P3S/C1": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "1"],
                         ["{$device}_{$host}_{$metric}_{$key}", "~", "<<", "5"]], 'trigger': 3, 'skip': 3, 'reset': 6,
               'code': 5},
    # На практике не используется. Здесь оставлено как пример
    "P1L": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "0"],
                      ["{$device}_{$host}_{$metric}_{$key}", "~", "<-", "20"]], 'trigger': 1, 'skip': 5, 'reset': 6,
            'code': 6},
    # На практике не используется. Здесь оставлено как пример
    "P2L": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "0"],
                      ["{$device}_{$host}_{$metric}_{$key}", "~", "<-", "20"]], 'trigger': 1, 'skip': 5, 'reset': 6,
            'code': 7},
    # На практике не используется. Здесь оставлено как пример
    "P2L*": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "0"],
                       ["{$device}_{$host}_{$metric}_{$key}", "P1L", ">>", "0"],
                       ["{$device}_{$host}_{$metric}_{$key}", "DS", "==", "1"],
                       ["{$device}_{$host}_{$metric}_{$key}", "P1L", "<>", "10"]], 'trigger': 3, 'skip': 3, 'reset': 6,
             'code': 8},
    # На практике не используется. Здесь оставлено как пример
    "P2L/C1": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "0"],
                         ["{$device}_{$host}_{$metric}_{$key}", "~", "<-", "20"]], 'trigger': 1, 'skip': 5, 'reset': 6,
               'code': 6},
    # На практике не используется. Здесь оставлено как пример
    "P3L/C1": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "0"],
                         ["{$device}_{$host}_{$metric}_{$key}", "~", "<-", "20"]], 'trigger': 1, 'skip': 5, 'reset': 6,
               'code': 7},
    # На практике не используется. Здесь оставлено как пример
    "P3L/C1*": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "0"],
                          ["{$device}_{$host}_{$metric}_{$key}", "P2L/C1", ">>", "0"],
                          ["{$device}_{$host}_{$metric}_{$key}", "DS", "==", "1"],
                          ["{$device}_{$host}_{$metric}_{$key}", "P2L/C1", "<>", "10"]], 'trigger': 3, 'skip': 3,
                'reset': 6, 'code': 8},
    # На практике не используется. Здесь оставлено как пример
    "P1L*": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "95"]], 'trigger': 3, 'skip': 3, 'reset': 6,
             'code': 10},
    # На практике не используется. Здесь оставлено как пример
    "P2L/C1*": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", ">>", "95"]], 'trigger': 3, 'skip': 3, 'reset': 6,
                'code': 10},
    # На практике не используется. Здесь оставлено как пример
    "DS*": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", "==", "3"],
                      ["{$device}_{$host}_{$metric}_{$key}", "P2S", "==", "0"],
                      ["{$device}_{$host}_{$metric}_{$key}", "P2L", "==", "0"]], 'trigger': 3, 'skip': 3, 'reset': 6,
            'code': 11},
    # На практике не используется. Здесь оставлено как пример
    "DS#": {'terms': [["{$device}_{$host}_{$metric}_{$key}", "~", "==", "3"],
                      ["{$device}_{$host}_{$metric}_{$key}", "P2S/C1", "==", "0"],
                      ["{$device}_{$host}_{$metric}_{$key}", "P2L/C1", "==", "0"]], 'trigger': 3, 'skip': 3, 'reset': 6,
            'code': 11},
}

# Коды событий и соответствующий им текст, который будет использован при уведомлении о тревоге (alarm)
event_codes = {
    1: "Обнаружен рост ошибок RX Crc на порту {$key} устройства {$host} [{$device}]!",
    2: "Порт {$key} на устройстве {$host} [{$device}] работает в режиме half-duplex!",
    3: "Скорость порта {$key} на устройстве {$host} [{$device}] задана вручную!",
    4: "Пара №1 порта {$key} на устройстве {$host} [{$device}] имеет повреждения!",
    5: "Пара №2 порта {$key} на устройстве {$host} [{$device}] имеет повреждения!",
    6: "Длина 1-й пары на порту {$key} устройства {$host} [{$device}] уменьшилась более чем на 20 метров!",
    7: "Длина 2-й пары на порту {$key} устройства {$host} [{$device}] уменьшилась более чем на 20 метров!",
    8: "Длина пар на порту {$key} устройства {$host} [{$device}] отличается более чем на 10 метров!",
    9: "Устройство {$host} [{$device}] было перезагружено!",
    10: "Длина кабеля на порту {$key} устройства {$host} [{$device}] превышает 95 метров!",
    11: "Длина кабеля на порту {$key} устройства {$host} [{$device}] не определена при поднятом линке!",
    12: "Устройство {$host} [{$device}] имеет устаревшую версию ПО - {$val}",
    13: "Трафик на порту {$key} устройства {$host} [{$device}] превышает 25 мбит/сек в обоих направлениях!",
    14: "Температура устройства {$host} [{$device}] - {$val} градусов!",
    15: "Загрузка CPU на устройстве {$host} [{$device}] - {$val}%!",
    16: "Трафик на порту {$key} устройства {$host} [{$device}] превышает 20 мбит/сек в направлении от абонента!",
}
