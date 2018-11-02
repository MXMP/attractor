**Attractor** - анализатор метрик, собираемых поллером для [Graphite](https://github.com/graphite-project/graphite-web), например [Briseis](https://github.com/xcme/briseis). Программа работает демоном под Linux/FreeBSD и написана на Python.

## Возможности **Attractor**
- Выбор из общего потока метрик тех, которые удовлетворяют определенным условиям
- Отправка событий в базу MySQL
- Отправка событий для произвольных метрик в Jabber
- Отправка событий в Telegram (требуется специальный бот, например вот [этот](https://github.com/hellsman/crierbot))
- Отправка событий для произвольных метрик путем выполнения GET запросов к внешнему URL
- Отправка событий в базу Oracle (через APEX)

## Особенности
- Прием метрик в таком же формате, как и у Graphite
- Проверка метрики по нескольким условиям
- Ожидание подтверждения события во избежание ложных срабатываний
- Пропуск повторяющегося события во избежание избыточных уведомлений
- Необходимость получать данные большими блоками, между которыми отправка данных в **Attractor** не производится

## Требования
- Операционная система Linux или FreeBSD
- Python  с модулями MySQLdb и xmpp
- Сборщик данных, например [Briseis](https://github.com/xcme/briseis)
- Определенный формат имени метрики (подробнее см. ниже)

## Предназначение
Сервис предназначен для выбора из общего потока метрик тех, которые требуют внимания, и отправки соответствующих уведомлений в базу данных. Событием или "тревогой" считается ситуация, когда за определенный интервал времени для метрики определенное количество раз выполнились некоторые условия. Каждое событие имеет свой код, которому соответствует произвольно заданный текст. В этот текст можно автоматически подставлять некоторые переменные. Пример приведен в конце документации.

## Принцип работы
**Attractor** работает следующим образом:

1. При старте открывает на прослушивание порт TCP:1907 (по умолчанию).
2. Пытается подключиться к Jabber (если настроено).
3. Каждые 5 секунд после запуска перепроверяет подключение к Jabber (если настроено) и список активных клиентов, передающих данные.
4. Контролирует поступление и отсутствие данных. Если данные были получены, а затем в течении интервала *nodata_int* больше не поступали, приступает к обработке полученных метрик.
5. Проверяет метрики на соответствие заданным условиям. При соответствии счетчик триггеров для конкретной метрики инкрементируется, а результат сохраняется в памяти.
6. Проверяет достигнуто ли требуемое количество счетчиков триггера для метрики. При достижении генерируется событие.
7. Отправляет события в базы данных MySQL или Oracle Apex, а также в Jabber.

## Формат входящих данных
**Attractor** ожидает данные в том же виде, в каком они передаются в [Graphite](https://github.com/graphite-project/graphite-web), но с небольшим нюансом. Поскольку в Graphite передаются три параметра (имя метрики, ее значение и timestamp), а в **Attractor** используется четыре (добавляется имя устройства), то четвертый параметр кодируется в самом имени метрики.

Пример ожидаемой строки данных: **DES-3200-28.10.90.90.90.RX.25 7654321 1451595600**

Значение    | Описание
------------| --------
DES-3200-28 | Имя устройства - все, что идет до первой точки.
10.90.90.90 | IP-адрес устройства - следующие 4 значения, разделенные точками.
RX          | Имя метрики - значение после точки, идущей пятой.
25          | Ключ метрики - все, что идет после шестой точки до первого пробела.
7654321     | Значение метрики. Здесь все как в Graphite.
1451595600  | Timestamp. И здесь все точно так же, как в Graphite.

# Конфигурирование
## Описание параметров в файле aconfig.py
### Основные параметры
Параметр           | Описание
----------------   | --------
interface_ip       | IP-адрес интерфейса, на котором программа будет слушать сокет.
port               | TCP-порт для прослушки (по умолчанию 1907).
sleep_int          | Пауза при опросе UDP-сокета. Поскольку проверка выполняется в бесконечном цикле, отсутствие паузы приведет к 100% загрузке CPU.
nodata_int         | Пауза ожидания блока данных. По истечении интервала начинается обработка данных.
log_file           | Имя файла журнала.
log_size           | Размер файла журнала при достижении которого начинается ротация.
log_backupcount    | Количество архивных копий журнала.
MetricNameTemplate | Шаблон полного имени метрики. Полное имя хранится в памяти программы. В шаблоне можно использовать переменные окружения\*.

### \*Переменные окружения для **MetricNameTemplate**
Параметр | Описание
-------- | --------
{$device}| Имя устройства.
{$host}  | IP-адрес устройства.
{$metric}| Краткое имя метрики, например 'RX'.
{$key}   | Значение "ключа" метрики.

### Настройки Jabber
Параметр          | Описание
----------------- | --------
useJabber         | Параметр, определяющий будут ли события отправляться в Jabber.
jid               | Jabber ID.
jps               | Пароль к учетной записи Jabber.
jcr               | Имя конференции Jabber.
jnn               | Псевдоним для конференции Jabber.
JabberMetricsList | Список метрик, сообщения для которых будут отправляться в Jabber. Задается как обычный список Python, например *['UP','TX','CT','CPU']*.

### Настройки Telegram
Параметр          | Описание
----------------- | --------
useTelegram       | Параметр, определяющий будут ли события отправляться в Telegram.
telegram_tokens   | Список токенов, которым будут отосланы сообщения.
telegram_url      | URL бота, на который нужно слать запросы. Должен содержать `{}` для подстановки токена.

### Настройки для выполнения внешних запросов
Параметр                  | Описание
------------------------- | --------
use_external_urls         | Параметр, определяющий будут отправляться запросы на внешние URL.
external_urls             | Список URL, на которые будут отправляться запросы.
external_requests_metrics | Список метрик, запросы для которых будут отправляться. Задается как обычный список Python, например *['UP','TX','CT','CPU']*.

### Настройки MySQL
Параметр        | Описание
--------------- | --------
useMySQL        | Параметр, определяющий будут ли события отправляться в MySQL.
mysql_addr      | Адрес MySQL-сервера.
mysql_user      | Имя пользователя.
mysql_pass      | Пароль.
mysql_base      | Имя базы данных.
mysql_cset      | Используемая кодировка.
mysql_tabl      | Имя таблицы для записи событий.
mysql_chain_len | Длина цепочки событий. Позволяет группировать события и записывать их в базу блоками, а не поштучно.

### Настройки Oracle Apex\*
Параметр       | Описание
-------------- | --------
useOracleApex  | Параметр, определяющий будут ли события отправляться в Oracle.
apex_url       | URL для Oracle Apex, например "*http://oracle.localhost:8082/apex/f?p=ins:1:::::QUERY:*".
apex_cmd       | Команда для Oracle Apex, например "*INSERT INTO c##blackhole.alarms (DATETIME,EVENT_CODE,KEY_,VALUE,METRIC,HOST,DEVICE)* ".
apex_chain_len | Параметр, определяющий будут ли события отправляться в MySQL.

\*Настройка Oracle Apex для работы с **Attractor** не является частью данного руководства. Под FreeBSD нет нативных инструментов для работы с Oracle, поэтому **Attractor** использует Oracle Apex как своеобразный "шлюз" к базе Oracle.

### Настройки условий для метрик
Параметр      | Описание
------------- | --------
event_horizon | Горизонт событий :). Словарь с описаниями условий для каждой метрики.

Остановимся поподробнее на этот моменте. Ключами словаря **event_horizon** являются имена метрик. Значениями, соответствующими этим ключам, являются словари, содержащие параметры, на основе которых принимается решение о генерации события. Вот эти параметры:

Параметр | Описание
-------- | --------
terms    | Условия, которые должны быть выполнены для срабатывания триггера. Задаются как список списков.
trigger  | Количество срабатываний триггера, необходимые для возникновения события.
skip     | Количество игнорирований события после того, как достигнуто необходимое значение *trigger*.
reset    | Количество проверок подряд после которых произойдет сброс всех счетчиков в случае, если триггер ни разу не сработал.
code     | Код, указывающий на конкретный тип события.

Значение *terms* для каждой метрики может содержать несколько условий. Каждое условие[\#] состоит из имени метрики[0], указателя на метрику для сравнения[1], операции сравнения[2] и значения для сравнения[3]. **Проверка на соответствие условиям считается пройденной, если выполнены все указанные условия для случаев, когда полное имя метрики, полученное из шаблона *MetricNameTemplate*, равно имени метрики в terms[\#][0]**. Значение *terms[\#]* задается в виде списка. Разберем его параметры ниже:

### Элементы списка условий
Параметр | Описание
-------- | --------
terms[\#][0] | Имя метрики. Проверка условий будет выполняться только в том случае, если имя метрики в памяти программы совпадет с данным именем. При этом в *terms[\#][0]* можно использовать приведенные выше переменные окружения\*.
terms[\#][1] | Указатель на метрику для сравнения. Значение "*~*" говорит, что будем работать с полученной метрикой, а отличное значение указывает на метрику, которая будет использоваться в условии.
terms[\#][2] | Операция сравнения. Список операций приведен ниже.
terms[\#][3] | Значение, используемое в операциях сравнения.

\***Пример**: Если устройство называется '*DES-3200-28*', IP-адрес равен '*10.90.90.90*', метрика имеет имя '*DS*', а событие произошло для ключа (порта) '*5*', то согласно шаблону **MetricNameTemplate** (значение по умолчанию '*{$device}\_{$host}\_{$metric}\_{$key}*') полное имя метрики будет '*DES-3200-28_10.90.90.90_DS_5*'. Это значение сравнивается с terms[\#][0] и если *terms[\#][0]* также равен '*{$device}\_{$host}\_{$metric}\_{$key}*', тогда проверка (операция сравнения) будет произведена. Для исключения некоторых срабатываний можно задавать заведомо невыполнимые условия для конкретных *terms[\#][0]*.

Все эти элементы вместе формируют некоторые условия, к которым применяются операции сравнения[2]. Ниже приведен их перечень:

### Операции сравнения
Варианты операций сравнения (Y=значение метрики *terms[\#][1]*, X=значение *terms[\#][3]*):

Условие | Описание
--------| --------
==      | Y равно X.
!=      | Y не равно X.
+>      | Y увеличился на величину X.
<-      | Y уменьшился на величину X.
\>\>      | Y больше, чем X.
<<      | Y меньше, чем X.
<>      | Y отличается от основной метрики на значение больше X\*.
in      | X входит в значение Y.
ni      | X не входит в значение Y.

\*В случаях, когда мы задаем в *terms[\#][1]* новое имя метрики, то операция сравнения выполняется для нового имени метрики. А в данном случае в памяти создается копия метрики, с которой затем сравнивается метрика в *terms[\#][1]*. Таким образом возможно сравнить две метрики между собой, а не только метрику с константой или с предыдущим значением. 

Самое время разобрать несколько примеров.

### Примеры условий
**Пример \#1**
```
event_horizon={
    "RX_CRC" :{'terms':[["{$device}_{$host}_{$metric}_{$key}","~","+>","5"]],'trigger':3,'skip':9,'reset':12,'code':1},

    "DS"     :{'terms':[["{$device}_{$host}_{$metric}_{$key}","~","==","2"]],'trigger':3,'skip':9,'reset':12,'code':2},
}
```
В данном случае у нас проверяются всего две метрики, где для каждой задано всего одно условие. Имя метрики в памяти программы получается из шаблона **MetricNameTemplate**, а для данных примеров значения *terms[\#][0]* равны значению этого шаблона, то есть сравнение будет выполняться всегда. Так, например, мы получаем в памяти программы имя '*DES-3200-28_10.90.90.90_RX_crc_7*' и такое же имя будет получено для *terms[\#][0]*.  

Значение *terms[\#][1]*, равное '*~*', говорит нам о том, что мы будем работать с той же самой метрикой, для которой проверяется условие, т.е. *'RX_CRC*' в первом случае и '*DS*' во втором.  

Значение *terms[\#][2]* определяет операцию сравнения, а значение *terms[\#][3]* - константу, используемую в этой операции.  

Таким образом, триггер для *'RX_CRC*' сработает, если значение данной метрики увеличилось на *5* или более, а триггер для *'DS*' - если значение этой метрики равно *2*. Значения '*trigger*','*skip*' и '*reset*' для данных метрик совпадают. В данном случае это значит, что:

- Событие будет сгенерировано если условие сработает трижды, т.к. '*trigger*'=3.
- После того, как событие произошло, состояния счетчиков метрики будут проигнорированы 9 раз, т.к. '*skip*'=9.
- Если 12 раз подряд значение '*trigger*' не изменялось, то все счетчики для метки будут сброшены, т.к. *reset*'=12

Например, если мы имеем устойчивый рост RX CRC на интерфейсе, а опрос производится каждые 5 минут, то сигнал о тревоге поступит через 15 минут (5\*3) после начала опроса устройств. После этого 45 минут (5\*9) состояния счетчиков метрики будут проигнорированы. Если же в течении 60 минут (12\*5) рост RX CRC не фиксировался, то счетчики будут сброшены и до следующего сигнала тревоги вновь должно пройти 15 минут после начала устойчивого роста. Таким образом, для каждой проблемы будет генерироваться только один сигнал тревоги в час.


**Пример \#2**
```
"P1S"    :{'terms':[["{$device}_{$host}_{$metric}_{$key}","~",">>","1"],
                    ["{$device}_{$host}_{$metric}_{$key}","~","<<","5"]],'trigger':3,'skip':3,'reset':6,'code':4},
```
Для случая, когда метрика '*P1S*' приходит раз в 10 минут, тревога будет сгенерирована через 30 минут (10\*3). После этого 30 минут (10\*3) состояния счетчиков метрики будут проигнорированы. Время до сброса счетчиков 60 минут (10\*6). Условием для срабатывания триггера будет значение '*P1S*' больше 1 и меньше 5 в то же время.


**Пример \#3**
```
"P2L"    :{'terms':[["{$device}_{$host}_{$metric}_{$key}","~",">>","0"],
                    ["{$device}_{$host}_{$metric}_{$key}","~","<-","20"]],'trigger':1,'skip':5,'reset':6,'code':7},
```
В этом случае метрика также приходит один раз в 10 минут. Условием для срабатывания триггера будет значение '*P2L*' больше 0 и в то же время на 20 меньшее, чем в предыдущем случае. Тревога будет сгенерирована при первом срабатывании условия, когда значение уменьшится на 20 и при этом будет больше, чем 0.  После этого 50 минут (10\*5) состояния счетчиков метрики будут проигнорированы. Время до сброса счетчиков 60 минут (10\*6).


**Пример \#4**
```
"P2L*"   :{'terms':[["{$device}_{$host}_{$metric}_{$key}","~",  ">>",  "0"],
                    ["{$device}_{$host}_{$metric}_{$key}","P1L",">>",  "0"],
                    ["{$device}_{$host}_{$metric}_{$key}","DS" ,"==",  "1"],
                    ["{$device}_{$host}_{$metric}_{$key}","P1L","<>", "10"]],'trigger':3,'skip':3,'reset':6,'code':8},

```
Метрика является копией метрики '*P2L*'. Условиями срабатывания триггера будут:

- Значение 'P2L\*' больше 0
- Значение '*P1L*' больше 0
- Значение '*DS*', равное 1
- Разница между значениями '*P1L*' и '*P2L*', составляющая больше 10

**Важно: Если указано имя другой метрики, то сравнение выполняется с предыдущим значением этой метрики, которое доступно при второй и последующих обработках данных.** Так, в этом примере мы работаем с текущим значением 'P2L\*' и с предыдущими значениями '*P1L*' и '*DS*'.

**Важно: Чтобы метрика вообще попадала в память, для нее должно быть задано условие в event_horizon**.

**Пример \#5**
```
"CNS"    :{'terms':[["DES-3200-28_{$host}_{$metric}_{$key}","~",">>","1"],
                    ["DES-3200-28_{$host}_{$metric}_25.100","~","<<","0"],
                    ["DES-3200-28_{$host}_{$metric}_26.100","~","<<","0"],
                    ["DES-3200-28_{$host}_{$metric}_27.100","~","<<","0"],
                    ["DES-3200-28_{$host}_{$metric}_28.100","~","<<","0"]],'trigger':3,'skip':9,'reset':12,'code':3},
```
В этом примере заданы заведомо невыполнимые условия для определенных значений *key*. Значение для ключа '*25.100*' не может быть меньше 0, поэтому в случае проверки метрики с таким ключом будут выполнены не все условия и триггер не сработает. А для ключа, например, '*24.100*' совпадение имен метрик произойдет только в первом случае, поэтому другие условия проверяться не будут.


**Пример \#6**
```
"UP"     :{'terms':[["{$device}_{$host}_{$metric}_{$key}","~","<-","1"]],'trigger':1,'skip':0,'reset':0,'code':9},
```
В данном случае событие будет сгенерировано каждый раз, когда значение '*UP*' уменьшилось более, чем на единицу. Это достигается благодаря нулевым значениям *skip*' и *reset*' и позволяет получать уведомление о каждой перезагрузке устройства.


**Пример \#7**
```
"FW"     :{'terms':[["DES-3200-28_{$host}_{$metric}_{$key}",   "~","ni","1.88"],
                    ["DES-3200-18_{$host}_{$metric}_{$key}",   "~","ni","1.88"],
                    ["DES-3200-28_C1_{$host}_{$metric}_{$key}","~","ni","4.4"],
                    ["DES-3200-18_C1_{$host}_{$metric}_{$key}","~","ni","4.4"],
                    ["DES-3028_{$host}_{$metric}_{$key}",      "~","ni","2.94"]],'trigger':1,'skip':35,'reset':36,'code':12},
```
Набор данных условий позволяет получать одно уведомление о неправильной версии ПО каждые 6 часов. Для каждой модели предусмотрено отдельное условие. Условия не пересекаются между собой, т.к. отличаются имена *terms[\#][0]*. Триггер сработает в случае, если сравниваемое значение отсутствует (*'ni'*) в текущем значении метрики.

### Коды событий
В примерах выше видно, что события можно отличать между собой по коду, который являющееся идентификатором события. Для каждого идентификатора задается свой текст события в произвольном виде. В этом тексте можно использовать переменные окружения программы.

Параметр    | Описание
----------- | --------
event_codes | Словарь кодами событий с соответствующим текстом.

**Пример описания в файле конфигурации**:
```
event_codes={
    3:"Скорость порта {$key} на устройстве {$host} [{$device}] задана вручную!",
}
```

**Пример сгенерированного события**:
```
Скорость порта 21.100 на устройстве 172.17.110.35 [DES-3028] задана вручную!
```

## Установка под Linux (пример для Centos 7)
+ Выполните команду: **git clone https://github.com/xcme/attractor.git**
+ Скопируйте файл '**attractor.service**' из директории '*./linux/centos/*' в '*/etc/systemd/system/*'.
+ Запустите сервис командой **systemctl start attractor**.
+ Добавьте автозапуск сервиса при загрузке системы командой **systemctl enable attractor**.

## Установка под FreeBSD
+ Скопируйте файл **attractor** из директории '*freebsd*' в '*/usr/local/etc/rc.d/*', а остальные файлы в '*/usr/local/etc/attractor/*'.
+ Добавьте строку **attractor_enable="YES"** в файл '*/etc/rc.conf*'.
+ Запустите сервис командой **service attractor start**.
