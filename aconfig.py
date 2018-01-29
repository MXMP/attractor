#coding=UTF8
# IP-адрес интерфейса и порт
interface_ip = ""
port         = 1907

# Пауза при опросе UDP-сокета
sleep_int = 0.001

# Пауза ожидания блока данных. По истечении интервала начинается обработка данных
nodata_int = 5

# Файл журнала
log_file   = "/var/log/attractor.log"
# Максимальный размер лога до архивирования
log_size        = 1048576
# Количество архивных копий лога
log_backupcount = 4

# Шаблон полного имени метрики
MetricNameTemplate = "{$device}_{$host}_{$metric}_{$key}"

# Настройки Jabber
useJabber = False
jid = "attractor@jabber.localhost"
jps = "jpass"
jcr = "nebula@conference.jabber.localhost"
jnn = "attractor"

JabberMetricsList = ['UP','TX','CT','CPU']

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
event_horizon={
    "RX_CRC" :{'terms':[["{$device}_{$host}_{$metric}_{$key}","~","+>","5"]],'trigger':5,'skip':25,'reset':30,'code':1},

    "CPU"    :{'terms':[["{$device}_{$host}_{$metric}_{$key}","~",">>","50"]],'trigger':5,'skip':10,'reset':15,'code':15},

    "CT"     :{'terms':[["{$device}_{$host}_{$metric}_{$key}","~",">>","60"]],'trigger':5,'skip':10,'reset':15,'code':14},

    "DS"     :{'terms':[["{$device}_{$host}_{$metric}_{$key}","~","==","2"],
			["{$device}_{$host}_{$metric}_{$key}","RX",">>","5"],
			["{$device}_{$host}_{$metric}_{$key}","TX",">>","5"]],'trigger':5,'skip':25,'reset':30,'code':2},

    "UP"     :{'terms':[["{$device}_{$host}_{$metric}_{$key}","~","<-","1"]],'trigger':1,'skip':0,'reset':0,'code':9},

    "RX"     :{'terms':[["{$device}_{$host}_{$metric}_{$key}","~",">>", "3000000000"]],'trigger':15,'skip':15,'reset':30,'code':16},

    "TX"     :{'terms':[["{$device}_{$host}_{$metric}_{$key}","~",">>", "1500000000"],
			["{$device}_{$host}_{$metric}_{$key}","RX",">>","1500000000"]],'trigger':15,'skip':15,'reset':30,'code':13},

    "FW"     :{'terms':[["DES-3200-28_{$host}_{$metric}_{$key}",   "~","ni","1.88"],
			["DES-3200-18_{$host}_{$metric}_{$key}",   "~","ni","1.88"],
			["DES-3200-28_C1_{$host}_{$metric}_{$key}","~","ni","4.4"],
			["DES-3200-18_C1_{$host}_{$metric}_{$key}","~","ni","4.4"],
			["DES-3028_{$host}_{$metric}_{$key}",      "~","ni","2.94"]],'trigger':1,'skip':359,'reset':360,'code':12},

    "CNS"    :{'terms':[["DES-3200-28_{$host}_{$metric}_{$key}","~",">>","1"],
			["DES-3200-18_{$host}_{$metric}_{$key}","~",">>","1"],
			["DES-3200-28_C1_{$host}_{$metric}_{$key}","~",">>","2"],
			["DES-3200-18_C1_{$host}_{$metric}_{$key}","~",">>","2"],
			["DES-3028_{$host}_{$metric}_{$key}","~",">>","1"]],'trigger':5,'skip':25,'reset':30,'code':3},

}

# Коды событий и соответствующий им текст, который будет использован при уведомлении о тревоге (alarm)
event_codes={
    1:"Обнаружен рост ошибок RX Crc на порту {$key} устройства {$host} [{$device}]!",
    2:"Порт {$key} на устройстве {$host} [{$device}] работает в режиме half-duplex!",
    3:"Скорость порта {$key} на устройстве {$host} [{$device}] задана вручную!",
    4:"Пара №1 порта {$key} на устройстве {$host} [{$device}] имеет повреждения!",				# Пример вынесен в dlink_cable_diag.example
    5:"Пара №2 порта {$key} на устройстве {$host} [{$device}] имеет повреждения!",				# Пример вынесен в dlink_cable_diag.example
    6:"Длина 1-й пары на порту {$key} устройства {$host} [{$device}] уменьшилась более чем на 20 метров!",	# Пример вынесен в dlink_cable_diag.example
    7:"Длина 2-й пары на порту {$key} устройства {$host} [{$device}] уменьшилась более чем на 20 метров!",	# Пример вынесен в dlink_cable_diag.example
    8:"Длина пар на порту {$key} устройства {$host} [{$device}] отличается более чем на 10 метров!",		# Пример вынесен в dlink_cable_diag.example
    9:"Устройство {$host} [{$device}] было перезагружено!",
   10:"Длина кабеля на порту {$key} устройства {$host} [{$device}] превышает 95 метров!",			# Пример вынесен в dlink_cable_diag.example
   11:"Длина кабеля на порту {$key} устройства {$host} [{$device}] не определена при поднятом линке!",		# Пример вынесен в dlink_cable_diag.example
   12:"Устройство {$host} [{$device}] имеет устаревшую версию ПО - {$val}",
   13:"Трафик на порту {$key} устройства {$host} [{$device}] превышает 40 Мбит/сек в обоих направлениях! (RX & TX > 40 Mbps)!",
   14:"Температура устройства {$host} [{$device}] - {$val} градусов!",
   15:"Загрузка CPU на устройстве {$host} [{$device}] - {$val}%!",
   16:"Входящий трафик на порту {$key} устройства {$host} [{$device}] превышает 80 Мбит/сек (RX > 80 Mbps)!",
}
