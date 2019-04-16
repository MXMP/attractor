#!/usr/local/bin/python2
# coding=UTF8

import logging
import socket
import struct
import sys
import time
import urllib2
import subprocess
from copy import copy

import requests

# TODO: переделать импорты
from aconfig import event_horizon, event_codes, MetricNameTemplate
from aconfig import interface_ip, port, sleep_int, nodata_int, logfile
from aconfig import mysql_base, mysql_cset, mysql_tabl, mysql_chain_len
from aconfig import useJabber, jid, jps, jcr, jnn, JabberMetricsList
from aconfig import useMySQL, mysql_addr, mysql_user, mysql_pass
from aconfig import useOracleApex, apex_url, apex_cmd, apex_chain_len
from aconfig import useTelegram, telegram_tokens, telegram_url, telegram_metrics
from aconfig import use_external_urls, external_urls, external_requests_metrics
from aconfig import use_external_scripts, external_scripts, external_scripts_metrics
from daemon import Daemon
from jabberbot import JabberBot

logging.basicConfig(filename=logfile,format='%(asctime)s  %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Функция подстановки значений переменных в строку
def get_processed_str(datastr, r_event):
    return datastr.replace("{$device}", r_event['device']).replace("{$host}", r_event['host']).replace('{$metric}',
                                                                                                       r_event[
                                                                                                           'metric']).replace(
        "{$key}", r_event['key']).replace("{$val}", r_event['value'])


def graphite2attractor(source):
    """
    Функция преобразования формата метрик Graphite к формату Attractor.

    :param str source: строка с метрикой в формате Graphite
    :return: метрика в формате Attractor (dict), в случае неудачи False
    """
    try:
        # Выдергиваем из входной строки метку времени, имя метрики и значение
        tmp_metric = source.split()
        timestamp = tmp_metric.pop()  # время, последний элемент
        metric_name = tmp_metric.pop(0)  # имя метрики, первый элемент
        value = '_'.join(tmp_metric)  # остальные элементы - значение, пробелы меняем на '_'

        # "Дербаним" имя метрики, оттуда мы получим все нужные параметры
        metric_dict = metric_name.split('.')
        device_model = metric_dict[0]
        host_ip = ".".join(metric_dict[1:5])
        metric = metric_dict[5]
        key = ".".join(metric_dict[6:])

        return {'metric': metric, 'device': device_model, 'host': host_ip, 'key': key, 'value': value,
                'timestamp': timestamp}
    except:
        return False


# Функция проверки истинности выполнения всех условий
def check_metric_terms(metrics_storage, r_event, r_metricname, e_terms, last_val):
    # tres - истинность выполнения условий, match_found - истинность хотя бы одного совпадения имен метрик
    tres = True
    match_found = False
    for term in e_terms:
        # e_mname - имя метрики из файла конфигурации
        # r_val - полученное значение
        # e_val - ожидаемое значение
        # c_mname - имя для сравнения
        # r_val_copy - прошлое значение для сравнения
        e_mname = get_processed_str(term[0], r_event)
        e_val = term[3]
        # Проверяем с чем будем сравнивать ожидаемое значение.
        # Значение "~" говорит, что будем работать с полученной метрикой,
        # а отличное значение указывает на новое имя метрики
        if term[1] == "~":
            r_val = r_event['value']
        else:
            # Запоминаем копию полученного значение.
            # Она пригодится для сравнения полученной и указанной метрик между собой
            r_val_copy = r_event['value']
            # Получаем новое имя метрики для сравнения
            c_mname = (r_metricname.replace(r_event['metric'], term[1]))
            # Пробуем получить последнее значение новой метрики.
            # При этом считаем, будто мы получили это значение только что (r_val)
            try:
                r_val = metrics_storage[c_mname]['lastval']
            # Если это не удалось, то значение принимаем равным "." - НЕ число
            except:
                r_val = "."

        if e_mname == r_metricname:
            match_found = True
            # Проверяем все операции сравнения
            if term[2] == '==':
                tres = tres * (r_val == e_val)
            elif term[2] == '!=':
                tres = tres * (r_val != e_val)
            elif term[2] == 'in':
                tres = tres * (e_val in r_val)
            elif term[2] == 'ni':
                tres = tres * (e_val not in r_val)
            elif term[2] == '>>':
                tres = tres * ((int(r_val) > int(e_val)) if (r_val.isdigit() * e_val.isdigit()) else 0)
            elif term[2] == '<<':
                tres = tres * ((int(r_val) < int(e_val)) if (r_val.isdigit() * e_val.isdigit()) else 0)
            elif term[2] == '+>':
                tres = tres * ((int(r_val) - int(last_val) > int(e_val)) if (
                        r_val.isdigit() * last_val.isdigit() * e_val.isdigit()) else 0)
            elif term[2] == '<-':
                tres = tres * ((int(last_val) - int(r_val) > int(e_val)) if (
                        r_val.isdigit() * last_val.isdigit() * e_val.isdigit()) else 0)
            elif term[2] == '<>':
                tres = tres * ((abs(int(r_val) - int(r_val_copy)) > int(e_val)) if (
                        r_val.isdigit() * r_val_copy.isdigit() * e_val.isdigit()) else 0)
    # Этот прием выполняется для удобства подсчета. По умолчанию считаем, что результат True.
    # Если условия выполняются, то умножение на 1 сохраняет этот результат.
    # Если имена метрик не совпали или хотя бы одно из условия не выполнилось,
    # произойдет умножение на 0, которое затем везде будет давать 0 в результате
    tres = tres * int(match_found)
    return tres


# Функция проверки счетчиков метрики
def check_metric_counters(metrics_storage, r_metricname, test_m, e_trigger, e_skip, e_reset, e_code):
    new_trigger = 0
    new_skip = 0
    new_reset = e_reset
    new_code = 0
    # Пробуем получить предыдущие значения счетчиков из хранилища метрик. При неудаче используем значения по умолчанию
    # Важно: Использование try..except работает существенно быстрее, чем предварительный поиск ключа.
    # Именно поэтому здесь так.
    try:
        old_trigger = metrics_storage[r_metricname]['trigger']
        old_skip = metrics_storage[r_metricname]['skip']
        old_reset = metrics_storage[r_metricname]['reset']
    except:
        old_trigger = 0
        old_skip = 0
        old_reset = 0
    # Декрементируем значение, если старое больше 0
    if old_skip > 0:
        new_skip = old_skip - 1
    # Если пропускать ничего не требуется, увеличиваем счетчик триггера на результат текущей проверки (0 или 1)
    if old_skip == 0:
        new_trigger = old_trigger + test_m
    # При любом срабатывании триггера начинаем отсчет до сброса сначала
    if test_m:
        new_reset = e_reset
    else:
        # Декрементируем значение, если старое больше 0
        if old_reset > 0:
            new_reset = old_reset - 1
        # Если счетчик 'reset' (старое значение) дошел до 0, значит триггер не сработал $e_reset раз.
        # Сбрасываем все параметры
        if old_reset == 0:
            new_trigger = 0
            new_skip = 0
            new_reset = e_reset
    # Если триггер срабатывал хотя бы $e_trigger раз, значит собираемся пропустить следующие $e_skip срабатываний
    # и возвращаем код события:
    if new_trigger >= e_trigger:
        new_skip = e_skip
        new_code = e_code
    return new_trigger, new_skip, new_reset, new_code


# Функция отправки данных в базу MySQL. При успехе возвращает True
def post_data_to_mysql(cr, send_query):
    try:
        logger.debug("Trying to execute MySQL query: {}".format(send_query))
        cr.execute(send_query)
    except Exception as e:
        logger.error(e.message)
        pass
    else:
        return True


def post_data_to_oracle_apex(apexurl):
    # Пытаемся открыть URL для Oracle Apex
    try:
        data = urllib2.urlopen(apexurl).read()
        # Проверка успешности обработки запроса
        if "INSERT_SUCCESS" in data:
            return True
        elif "class=\"error\"" in data:
            return False
    # При неудаче возвращаем код ошибки
    except:
        return False
    # Если подключение успешно, но результат неизвестен, ничего не возвращаем. Автоматически вернется None


def send_msg_to_telegram(msg):
    """
    Отправляет сообщение в телеграм для соответствующего токена.

    :param msg: Сообщение которое нужно отправить
    """
    if msg:
        with requests.Session() as session:
            for token in telegram_tokens:
                payload = {'message': msg, 'mode': 'markdown'}
                try:
                    response = session.get(telegram_url.format(token), params=payload)
                    response.raise_for_status()
                except requests.ConnectionError:
                    logger.warning("Can't send message to Telegram: connection error")
                except requests.Timeout:
                    logger.warning("Can't send message to Telegram: timeout")
                except requests.TooManyRedirects:
                    logger.warning("Can't send message to Telegram: too many redirects")
                except requests.HTTPError:
                    logger.warning(
                        "Can't send message to Telegram: {} something goes wrong".format(response.status_code))


def make_external_requests(message, device_ipaddr):
    """
    Отправляет сообщение в телеграм для соответствующего токена.

    :param message: Сообщение которое нужно отправить
    :param device_ipaddr: ip-адрес устройства, для которого сработал триггер
    """
    if message:
        with requests.Session() as session:
            for url in external_urls:
                payload = {'message': message, 'device_ipaddr': device_ipaddr}
                try:
                    response = session.get(url, params=payload)
                    response.raise_for_status()
                except requests.ConnectionError:
                    logger.warning("Can't send external request to {}: connection error".format(url))
                except requests.Timeout:
                    logger.warning("Can't send external request to {}: timeout".format(url))
                except requests.TooManyRedirects:
                    logger.warning("Can't send external request to {}: too many redirects".format(url))
                except requests.HTTPError:
                    logger.warning(
                        "Can't send external request to {}: {} something goes wrong".format(url, response.status_code))


def call_external_scripts(event):
    """
    Запускает внешние скрипты.

    :param event: событие
    """

    for script_line in external_scripts:
        command = copy(script_line[0])
        for m in script_line[1]:
            try:
                command.append(event[m])
            except IndexError:
                logger.warn('Failed to construct external script command.')
                break
        try:
            subprocess.call(command)
        except OSError:
            logger.warning('Failed to execute external script [{}], file not found.'.format(command))
        except ValueError:
            logger.warning('Failed to execute external script [{}], wrong arguments.'.format(command))
        except:
            logger.warning('Failed to execute external script [{}], unknown error.'.format(command))


def main():
    logger.info("Daemon 'Attractor' started...")

    if useMySQL:
        import MySQLdb

    # Создаем сокет для приема метрик
    tcps = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Переводим сокет в неблокирующий режим и задаем опции для более быстрого освобождения ресурсов
    tcps.setblocking(0)
    tcps.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcps.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))

    clients = []  # список клиентов (входящих соединений)
    events_raw = ''  # сырые данные, принятые при очередном цикле
    metrics_storage = {}  # хранилище метрик, сюда складываются обработанные метрики со счетчиками

    # Пробуем открыть сокет
    try:
        tcps.bind((interface_ip, port))
    # Обрабатываем возможную ошибку сокета (сокет уже занят), делаем запись в лог и ноги :):
    except socket.error as err:
        logger.error("Socket Error: {}. Exiting...".format(err.args[1]))
        tcps.close()
        sys.exit(2)
    else:
        # При отсутствии ошибок начинаем прослушивать порт
        tcps.listen(2)

    # Пробуем подключиться к Jabber
    jbot_ok = False  # флаг, живо ли соединение с Jabber
    if useJabber:
        # jid - JID, jps - password, jcr - chat room, jnn - nickname
        jbot = JabberBot(jid, jps, jcr, jnn)
        if jbot.connect():
            if jbot.auth():
                jbot.joinroom()
                jbot_ok = True
                logger.info("Connection to Jabber '{}' established!".format(jid.split("@")[1]))
            else:
                logger.info("ERROR (Jabber): Can't log ID '{}'!".format(jid.split("@")[0]))
        else:
            logger.info("ERROR (Jabber): Can't connect to '{}'!".format(jid.split("@")[1]))

    try_mysql = True  # флаг, нужно ли пробовать открыть новое соединение с MySQL
    recog_events = 0  # счетчик распознанных событий (события которые были преобразованы в формат Attractor)
    triggered_events = 0  # счетчик сработавших условий
    timer = int(time.time())  # время начала основного цикла программы (циклы по 5 секунд)
    timer_last_data = int(time.time())  # время получения последних данных при опросе сокета
    pause_ratio = 1  # множитель для паузы опроса сокета

    while True:
        events = []  # список всех распознанных событий

        # Каждые 5 секунд проверяем список клиентов и полученные события
        if int(time.time()) - timer >= 5:
            timer = int(time.time())

            # Убираем из списка неактивных клиентов
            for client in clients:
                try:
                    client.getpeername()
                except:
                    clients.remove(client)

            if useJabber:
                # Если подключение к Jabber не живо, то пробуем переподключиться
                if not jbot.is_alive:
                    jbot_ok = False
                    logger.info("WARNING: Not connected to Jabber! Trying to reconnect...")
                    if jbot.connect():
                        if jbot.auth():
                            jbot.joinroom()
                            jbot_ok = True
                            logger.info("Reconnection to Jabber '{}' established!".format(jid.split("@")[1]))
                        else:
                            logger.info("ERROR (Jabber): Can't log ID '{}'!".format(jid.split("@")[0]))
                    else:
                        logger.info("ERROR (Jabber): Can't connect to '{}'!".format(jid.split("@")[1]))
                if jbot_ok:
                    jbot.proc()

        jCount = 0  # счетчик сообщений, которые должны быть отправлены в Jabber
        external_requests_count = 0  # счетчик сообщений, которые должны быть отправлены путем запроса на внешний URL
        telegram_events_count = 0  # счетчик событий, которые должны быть отправлены в Telegram
        external_scripts_count = 0  # счетчик событий, которые должны быть отправлены во внешние скрипты

        # Пробуем принять подключение
        try:
            connect, addr = tcps.accept()
        except:
            pass
        else:
            # Переводим сокет в неблокирующий режим и говорим, чтобы при отключении освобождался
            # быстрее (no linger) и добавляем в список
            connect.setblocking(0)
            connect.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
            clients.append(connect)

        # Пробуем получить данные с сокета, перебирая всех клиентов
        for client in clients:
            try:
                data = client.recv(512)
            # Если данных нет возникнет ошибка, это нормально, ничего не трогаем
            except:
                pass
            else:
                # Если клиент отключился, то recv вернет пустую строку. Закроем такой сокет.
                if data == '':
                    client.close()
                # Складываем вместе данные, оставшиеся с прошлой обработки (могут быть пустыми), вместе с полученными
                events_raw = events_raw + data
                timer_last_data = int(time.time())
                # Если данные поступают, начинаем опрашивать сокет чаще путем уменьшения интервала ожидания
                pause_ratio = 0.01

        # Если истек интервал ожидания данных и сами данные не пустые, начинаем их обрабатывать
        if (int(time.time()) - timer_last_data >= nodata_int) & (len(events_raw) > 0):
            # Возвращаем прежнее значение коэффициента паузы для ожидания данных
            pause_ratio = 1
            # Необработанные данные преобразываются в список.
            # Если элемент списка удается преобразовать в словарь, значит получено валидное событие.
            tmp_events = events_raw.split("\n")
            for ev_item in tmp_events:
                # Пробуем преобразовать данные в словарь
                event = graphite2attractor(ev_item)
                if event:
                    events.append(event)
                    recog_events += 1
                else:
                    if ev_item != '':
                        logger.info("WARNING! Unknown data format: %s", ev_item)
            del tmp_events
            events_raw = ''
            # Проверяем, получены ли новые события
            if recog_events > 0:
                logger.info("New events are recieved. Recognized {} entries.".format(recog_events))
                recog_events = 0
            # Пробуем подключиться к MySQL. Используем таймаут в 1 секунду
            if useMySQL and try_mysql:
                try:
                    mysql_conn = MySQLdb.connect(host=mysql_addr, user=mysql_user, passwd=mysql_pass, db=mysql_base,
                                                 charset=mysql_cset, connect_timeout=1)
                    mysql_conn.autocommit(True)
                except:
                    logger.info('ERROR (MySQL): Cannot connect to server. :(')
                else:
                    logger.info("Connection to MySQL Server '{}' (Write) established".format(mysql_addr))
                    # Создаем 'курсор'. (Особая MySQLdb-шная магия)
                    mysql_cr = mysql_conn.cursor()
                finally:
                    try_mysql = False
            # Определяем словари, содержащие счетчики событий для MySQL и Oracle Apex
            send_query = {'query': '', 'count': 0, 'total': 0}
            apex_query = {'query': '', 'count': 0, 'total': 0}

            # Обработка событий
            for event in events:
                if event['metric'] in event_horizon:
                    # Полное имя полученной метрики
                    r_metricname = get_processed_str(MetricNameTemplate, event)
                    # Пробуем получить предыдущее значение метрики
                    # Важно: Использование try..except работает существенно быстрее,
                    # чем предварительный поиск ключа. Именно поэтому здесь так.
                    try:
                        last_val = metrics_storage[r_metricname]['lastval']
                    except:
                        last_val = '0'
                    test_metric = check_metric_terms(metrics_storage, event, r_metricname,
                                                     event_horizon[event['metric']]['terms'], last_val)
                    tmp_trig, tmp_skip, tmp_reset, tmp_code = check_metric_counters(
                        metrics_storage,
                        r_metricname,
                        test_metric,
                        event_horizon[event['metric']]['trigger'],
                        event_horizon[event['metric']]['skip'],
                        event_horizon[event['metric']]['reset'],
                        event_horizon[event['metric']]['code'])

                    # Обновляем хранилище метрик, записывая туда временные значения счетчик срабатывания
                    # условий и счетчика пропусков
                    metrics_storage[r_metricname] = {'lastval': event['value'], 'trigger': tmp_trig, 'skip': tmp_skip,
                                                     'reset': tmp_reset}
                    if (tmp_code > 0) & (tmp_code in event_codes):
                        triggered_events += 1
                        if useJabber and jbot_ok and (event['metric'] in JabberMetricsList):
                            try:
                                jbot.send_msg(get_processed_str(event_codes[tmp_code], event))
                            except:
                                logger.info("ERROR (Jabber): Cannot send data to Jabber!")
                            jCount += 1
                        if useTelegram and (event['metric'] in telegram_metrics):
                            send_msg_to_telegram(get_processed_str(event_codes[tmp_code], event))
                            telegram_events_count += 1
                        if use_external_urls and (event['metric'] in external_requests_metrics):
                            make_external_requests(get_processed_str(event_codes[tmp_code], event), event['host'])
                            external_requests_count += 1
                        if use_external_scripts and (event['metric'] in external_scripts_metrics):
                            call_external_scripts(event)
                            external_scripts_count += 1
                        if useMySQL:
                            if send_query['count'] == 0:
                                send_query['query'] = """INSERT INTO {0}.{1} (
                                    {1}.device, {1}.host, {1}.metric, {1}.key, {1}.value, {1}.event_code,
                                    {1}.event_text, {1}.datetime) 
                                    VALUES """.format(mysql_base, mysql_tabl)
                            send_query['query'] += "('{0}','{1}','{2}','{3}','{4}',{5},'{6}','{7}'),".format(
                                event['device'], event['host'], event['metric'], event['key'], event['value'], tmp_code,
                                get_processed_str(event_codes[tmp_code], event), int(time.time()))
                            send_query['count'] += 1
                            if send_query['count'] >= mysql_chain_len:
                                if post_data_to_mysql(mysql_cr, send_query['query'][:-1]):
                                    send_query['total'] += send_query['count']
                                send_query['count'] = 0
                                send_query['query'] = ''
                        if useOracleApex:
                            if apex_query['count'] == 0:
                                apex_query['query'] = apex_url + apex_cmd.encode("hex")
                            apex_query['query'] += ("SELECT {},{},'{}','{}','{}','{}','{}' FROM dual UNION ALL ".format(
                                int(time.time()), tmp_code, event['key'], event['value'], event['metric'],
                                event['host'], event['device'])).encode("hex")
                            apex_query['count'] += 1
                            if apex_query['count'] >= apex_chain_len:
                                if post_data_to_oracle_apex(apex_query['query'][:-22]):
                                    apex_query['total'] += apex_query['count']
                                apex_query['count'] = 0
                                apex_query['query'] = ''
            # Проверяем, осталось ли что-то в буфере для MySQL. Если да - отправляем. После этого отключаемся от MySQL
            if useMySQL:
                if send_query['count'] > 0:
                    if post_data_to_mysql(mysql_cr, send_query['query'][:-1]):
                        send_query['total'] += send_query['count']
                try:
                    mysql_conn.close()
                except:
                    pass
                finally:
                    try_mysql = True
            # Проверяем, осталось ли что-то в буфере для Oracle Apex. Если да - отправляем
            if useOracleApex:
                if apex_query['count'] > 0:
                    if post_data_to_oracle_apex(apex_query['query'][:-22]):
                        apex_query['total'] += apex_query['count']

            # Проверяем, есть ли события, для которых достигнуто необходимое количество срабатываний
            if triggered_events > 0:
                logger.info("WARNING: New alerts triggered: {}.".format(triggered_events))
                triggered_events = 0
            # Пишем в лог сколько записей мы отправили в Jabber, MySQL и Orale Apex
            logger.info("Alerts sended to Jabber: {}, to MySQL: {}, to Oracle Apex: {}, to external URLs: {},"
                         " to external scripts: {}, to Telegram: {}".format(jCount,
                                                                            send_query['total'],
                                                                            apex_query['total'],
                                                                            external_requests_count,
                                                                            external_scripts_count,
                                                                            telegram_events_count))
            # Пишем в лог о завершении обработки
            logger.info("All events have been processed.")
            logger.info("-------")
        time.sleep(sleep_int * pause_ratio)


# ------- Служебный блок: создание и управление демоном -------

class MyDaemon(Daemon):
    def run(self):
        main()


if __name__ == "__main__":
    daemon = MyDaemon('/var/run/attractor.pid', '/dev/null', logfile, logfile)
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'faststart' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Attractor: " + sys.argv[1] + " - unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)

# ------- Конец служебного блока -------
