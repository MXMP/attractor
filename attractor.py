#!/usr/local/bin/python2
#coding=UTF8
#version: 2.7.20 (2016.07.20)

import sys, socket, struct, time, logging, xmpp, MySQLdb, urllib2
from daemon import Daemon

from aconfig import interface_ip, port, sleep_int, nodata_int, logfile
from aconfig import event_horizon, event_codes, MetricNameTemplate
from aconfig import useJabber, jid, jps, jcr, jnn, JabberMetricsList
from aconfig import useMySQL, mysql_addr, mysql_user, mysql_pass
from aconfig import mysql_base, mysql_cset, mysql_tabl, mysql_chain_len
from aconfig import useOracleApex, apex_url, apex_cmd, apex_chain_len

logging.basicConfig(filename = logfile, level = logging.DEBUG, format = '%(asctime)s  %(message)s')

class JabberBot:
    def __init__(self, jid, jps ,jcr, jnn):
        jid = xmpp.JID(jid)
        self.user, self.server, self.password, self.jcr, self.jnn, = jid.getNode(), jid.getDomain(), jps, jcr, jnn

    def connect(self):
        self.conn = xmpp.Client(self.server, debug = [])
        return self.conn.connect()

    def auth(self):
        return self.conn.auth(self.user, self.password)

    def joinroom(self):
        self.conn.sendInitPresence(1)
        self.conn.send(xmpp.Presence(to="%s/%s" % (self.jcr, self.jnn)))

    def proc(self):
        self.conn.Process(1)

    def SendMsg(self, msg):
        self.conn.send(xmpp.protocol.Message(self.jcr,msg,'groupchat'))

    def disconnect(self):
        self.conn.send(xmpp.Presence(typ = 'unavailable'))

    def isAlive(self):
        try:
            self.conn.send(xmpp.Presence(status=None, show=None))
            alive = True
        except IOError:
            alive = False
        return alive

# Функция подстановки значений переменных в строку
def GetProcessedStr(datastr, r_event):
    return datastr.replace("{$device}",r_event['device']).replace("{$host}",r_event['host']).replace('{$metric}',r_event['metric']).replace("{$key}",r_event['key']).replace("{$val}",r_event['value'])

# Функция преобразования формата метрик Graphite к формату Attractor
def Graphite2Attractor(source):
    try:
	tmpstr, value, timestamp = source.split(' ')
	tmpstr    = tmpstr.split('.')
	device    = tmpstr[0]
	host      = ".".join(tmpstr[1:5])
	metric    = tmpstr[5]
	key       = ".".join(tmpstr[6:])
	return {'metric':metric, 'device':device, 'host': host, 'key': key, 'value':value, 'timestamp':timestamp}
    except:
	return False

# Функция проверки истинности выполнения всех условий
def CheckMetricTerms(metrics_storage, r_event, r_metricname, e_terms, last_val):
    # tres - истинность выполнения условий, match_found - истинность хотя бы одного совпадения имен метрик
    tres = True
    match_found = False
    for term in e_terms:
        # e_mname - имя метрики из файла конфигурации, r_val - полученное значение, e_val - ожидаемое значение, , c_mname - имя для сравнения, r_val_copy - прошлое значение для сравнения
        e_mname = GetProcessedStr(term[0],r_event)
        e_val = term[3]
	# Проверяем с чем будем сравнивать ожидаемое значение. Значение "~" говорит, что будем работать с полученной метрикой, а отличное значение указывает на новое имя метрики
	if term[1]=="~":
	    r_val = r_event['value']
	else:
	    # Запоминаем копию полученного значение. Она пригодится для сравнения полученной и указанной метрик между собой
	    r_val_copy = r_event['value']
	    # Получаем новое имя метрики для сравнения
	    c_mname = (r_metricname.replace(r_event['metric'],term[1]))
	    # Пробуем получить последнее значение новой метрики. При этом считаем, будто мы получили это значение только что (r_val)
	    try:
		r_val = metrics_storage[c_mname]['lastval']
	    # Если это не удалось, то значение принимаем равным "." - НЕ число
	    except:
		r_val = "."

        if e_mname == r_metricname:
            match_found = True
	    # Проверяем все операции сравнения
	    if   term[2]=='==':
		tres = tres * (r_val==e_val)
	    elif term[2]=='!=':
		tres = tres * (r_val!=e_val)
	    elif term[2]=='in':
		tres = tres * (e_val in r_val)
	    elif term[2]=='ni':
		tres = tres * (e_val not in r_val)
	    elif term[2]=='>>':
		tres = tres * ( (int(r_val) > int(e_val)) if (r_val.isdigit() * e_val.isdigit()) else 0)
	    elif term[2]=='<<':
		tres = tres * ( (int(r_val) < int(e_val)) if (r_val.isdigit() * e_val.isdigit()) else 0)
	    elif term[2]=='+>':
		tres = tres * ( (int(r_val) - int(last_val) > int(e_val)) if (r_val.isdigit() * last_val.isdigit() * e_val.isdigit()) else 0)
	    elif term[2]=='<-':
		tres = tres * ( (int(last_val) - int(r_val) > int(e_val)) if (r_val.isdigit() * last_val.isdigit() * e_val.isdigit()) else 0)
	    elif term[2]=='<>':
		tres = tres * ( (abs(int(r_val) - int(r_val_copy)) > int(e_val)) if (r_val.isdigit() * r_val_copy.isdigit() * e_val.isdigit()) else 0 )
    # Этот прием выполняется для удобства подсчета. По умолчанию считаем, что результат True. Если условия выполняются, то умножение на 1 сохраняет этот результат
    # Если имена метрик не совпали или хотя бы одно из условия не выполнилось, произойдет умножение на 0, которое затем везде будет давать 0 в результате
    tres = tres*int(match_found)
    return tres

# Функция проверки счетчиков метрики
def CheckMetricCounters(metrics_storage, r_metricname, test_m, e_trigger, e_skip, e_reset, e_code):
    new_trigger = 0; new_skip = 0; new_reset = e_reset; new_code = 0
    # Пробуем получить предыдущие значения счетчиков из хранилища метрик. При неудаче используем значения по умолчанию
    # Важно: Использование try..except работает существенно быстрее, чем предварительный поиск ключа. Именно поэтому здесь так.
    try:
	old_trigger = metrics_storage[r_metricname]['trigger']
	old_skip = metrics_storage[r_metricname]['skip']
	old_reset = metrics_storage[r_metricname]['reset']
    except:
	old_trigger = 0; old_skip = 0; old_reset = 0
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
	# Если счетчик 'reset' (старое значение) дошел до 0, значит триггер не сработал $e_reset раз. Сбрасываем все параметры
	if old_reset == 0:
	    new_trigger = 0
	    new_skip = 0
	    new_reset = e_reset
    # Если триггер срабатывал хотя бы $e_trigger раз, значит собираемся пропустить следующие $e_skip срабатываний и возвращаем код события:
    if new_trigger >= e_trigger:
	new_skip = e_skip
	new_code = e_code
    return new_trigger, new_skip, new_reset, new_code

# Функция отправки данных в базу MySQL. При успехе возвращает True
def PostDataToMySQL(cr,send_query):
    try:
	cr.execute(send_query)
    except:
	pass
    else:
	return True

def PostDataToOracleApex(apexurl):
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

def main():
    logging.info("Daemon 'Attractor' started...")
    # Создаем сокет для приема метрик
    tcps = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Переводим сокет в неблокирующий режим и задаем опции для более быстрого освобождения ресурсов
    tcps.setblocking(0)
    tcps.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcps.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))

    clients = []
    events_raw = ''
    metrics_storage = {}

    # Пробуем открыть сокет
    try:
	tcps.bind((interface_ip,port))
    # Обрабатываем возможную ошибку сокета (сокет уже занят), делаем запись в лог и ноги :):
    except socket.error as err:
	logging.error("Socket Error: {}. Exiting...".format(err.args[1]))
	tcps.close()
	sys.exit(2)
    else:
	# При отсутствии ошибок начинаем прослушивать порт
	tcps.listen(2)

    # Пробуем подключиться к Jabber
    jbot_ok = False
    if useJabber:
	# jid - JID, jps - password, jcr - chat room, jnn - nickname
	jbot = JabberBot(jid,jps,jcr,jnn)
	if jbot.connect():
	    if jbot.auth():
		jbot.joinroom()
		jbot_ok = True
		logging.info("Connection to Jabber '{}' established!".format(jid.split("@")[1]))
	    else:
		logging.info("ERROR (Jabber): Can't log ID '{}'!".format(jid.split("@")[0]))
	else:
	    logging.info("ERROR (Jabber): Can't connect to '{}'!".format(jid.split("@")[1]))

    try_mysql = True
    recog_events = 0
    triggered_events = 0
    timer = int(time.time())
    timer_last_data = int(time.time())
    pause_ratio = 1
    while True:
	events  = []
	# Каждые 5 секунд проверяем список клиентов и полученные события
	if ((int(time.time()) - timer >= 5)):
	    timer = int(time.time())
	    # Убираем из списка неактивных клиентов
	    i = 0
	    while i < len(clients):
		try: clients[i].getpeername()
		except: clients.remove(clients[i])
		else: i += 1
	    if useJabber:
		# Проверяем, есть ли подключение к Jabber
		if jbot.isAlive:
		    pass
		else:
		    jbot_ok = False
		    logging.info("WARNING: Not connected to Jabber! Trying to reconnect...")
		    if jbot.connect():
			if jbot.auth():
			    jbot.joinroom()
			    jbot_ok = True
			    logging.info("Reconnection to Jabber '{}' established!".format(jid.split("@")[1]))
			else:
			    logging.info("ERROR (Jabber): Can't log ID '{}'!".format(jid.split("@")[0]))
		    else:
			logging.info("ERROR (Jabber): Can't connect to '{}'!".format(jid.split("@")[1]))
		if jbot_ok:
		    jbot.proc()
	jCount = 0
	# Пробуем принять подключение
	try:    connect, addr = tcps.accept()
	except: pass
	else:
	    # Переводим сокет в неблокирующий режим и говорим, чтобы при отключении освобождался быстрее (no linger) и добавляем в список
	    connect.setblocking(0)
	    connect.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
	    clients.append(connect)
	# Пробуем получить данные с сокета, перебирая всех клиентов
	for client in clients:
	    try:    data = client.recv(512)
	    # Если данных нет возникнет ошибка, это нормально, ничего не трогаем
	    except: pass
	    else:
		# Если клиент отключился, то recv вернет пустую строку. Закроем такой сокет.
		if data=='': client.close()
		# Складываем вместе данные, оставшиеся с прошлой обработки (могут быть пустыми), вместе с полученными
		events_raw = events_raw + data
		timer_last_data = int(time.time())
		# Если данные поступают, начинаем опрашивать сокет чаще путем уменьшения интервала ожидания
		pause_ratio = 0.01
	# Если истек интервал ожидания данных и сами данные не пустые, начинаем их обрабатывать
	if ((int(time.time()) - timer_last_data >= nodata_int) & (len(events_raw)>0)):
	    # Возвращаем прежнее значение коэффициента паузы для ожидания данных
	    pause_ratio = 1
	    # Необработанные данные преобразываются в список. Если элемент списка удается преобразовать в словарь, значит получено валидное событие.
	    tmp_events = events_raw.split("\n")
	    for ev_item in tmp_events:
		# Пробуем преобразовать данные в словарь
		event = Graphite2Attractor(ev_item)
		if event:
		    events.append(event)
		    recog_events += 1
		else:
		    if ev_item != '':
			logging.info("WARNING! Unknown data format: %s", ev_item)
	    del tmp_events
	    events_raw = ''
	    # Проверяем, получены ли новые события
	    if (recog_events>0):
		logging.info("New events are recieved. Recognized {} entries.".format(recog_events))
		recog_events = 0
	    # Пробуем подключиться к MySQL. Используем таймаут в 1 секунду
	    if useMySQL and try_mysql:
		try:
		    mysql_conn = MySQLdb.connect(host=mysql_addr, user=mysql_user, passwd=mysql_pass, db=mysql_base, charset=mysql_cset, connect_timeout=1)
		    mysql_conn.autocommit(True)
		except:
		    logging.info('ERROR (MySQL): Cannot connect to server. :(')
		else:
		    logging.info("Connection to MySQL Server '{}' (Write) established".format(mysql_addr))
		    # Создаем 'курсор'. (Особая MySQLdb-шная магия)
		    mysql_cr  = mysql_conn.cursor()
		finally:
		    try_mysql = False
	    # Определяем словари, содержащие счетчики событий для MySQL и Oracle Apex
	    send_query = {'query':'', 'count':0, 'total':0}
	    apex_query = {'query':'', 'count':0, 'total':0}
	    # Обработка событий
	    for event in events:
		if event['metric'] in event_horizon:
		    # Полное имя полученной метрики
		    r_metricname = GetProcessedStr(MetricNameTemplate, event)
		    # Пробуем получить предыдущее значение метрики
		    # Важно: Использование try..except работает существенно быстрее, чем предварительный поиск ключа. Именно поэтому здесь так.
		    try:
			last_val = metrics_storage[r_metricname]['lastval']
		    except:
			last_val = '0'
		    test_metric = CheckMetricTerms(metrics_storage, event, r_metricname, event_horizon[event['metric']]['terms'], last_val)
		    tmp_trig, tmp_skip, tmp_reset, tmp_code = CheckMetricCounters(metrics_storage, r_metricname, test_metric,
			event_horizon[event['metric']]['trigger'],
			event_horizon[event['metric']]['skip'],
			event_horizon[event['metric']]['reset'],
			event_horizon[event['metric']]['code']
			)
		    # Обновляем хранилище метрик, записывая туда временные значения счетчик срабатывания условий и счетчика пропусков
		    metrics_storage[r_metricname]={'lastval':event['value'],'trigger':tmp_trig,'skip':tmp_skip,'reset':tmp_reset}
		    if (tmp_code>0) & (tmp_code in event_codes):
			triggered_events += 1
			if (useJabber and jbot_ok and (event['metric'] in JabberMetricsList)):
			    try:
				jbot.SendMsg(GetProcessedStr(event_codes[tmp_code], event))
				#logging.info(GetProcessedStr(event_codes[tmp_code], event))
			    except:
				logging.info("ERROR (Jabber): Cannot send data to Jabber!")
			    jCount += 1
			if useMySQL:
			    if send_query['count'] == 0:
				send_query['query']= "insert into {0}.{1} ({1}.device,{1}.host,{1}.metric,{1}.key,{1}.value,{1}.event_code,{1}.event_text,{1}.datetime) values ".format(mysql_base,mysql_tabl)
			    send_query['query'] += "('{0}','{1}','{2}','{3}','{4}',{5},'{6}','{7}'),".format(event['device'],event['host'],event['metric'],event['key'],event['value'],tmp_code,GetProcessedStr(event_codes[tmp_code],event),int(time.time()))
			    send_query['count'] += 1
			    if send_query['count'] >= mysql_chain_len:
				if PostDataToMySQL(mysql_cr,send_query['query'][:-1]):
				    send_query['total'] += send_query['count']
				send_query['count'] = 0
				send_query['query'] = ''
			if useOracleApex:
			    if apex_query['count'] == 0:
				apex_query['query']= apex_url+apex_cmd.encode("hex")
			    apex_query['query'] += ("SELECT {},{},'{}','{}','{}','{}','{}' FROM dual UNION ALL ".format(int(time.time()),tmp_code,event['key'],event['value'],event['metric'],event['host'],event['device'])).encode("hex")
			    apex_query['count'] += 1
			    if apex_query['count'] >= apex_chain_len:
				if PostDataToOracleApex(apex_query['query'][:-22]):
				    apex_query['total'] += apex_query['count']
				apex_query['count'] = 0
				apex_query['query'] = ''
	    # Проверяем, осталось ли что-то в буфере для MySQL. Если да - отправляем. После этого отключаемся от MySQL
	    if useMySQL:
		if send_query['count'] > 0:
		    if PostDataToMySQL(mysql_cr,send_query['query'][:-1]):
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
		    if PostDataToOracleApex(apex_query['query'][:-22]):
			apex_query['total'] += apex_query['count']

	    # Проверяем, есть ли события, для которых достигнуто необходимое количество срабатываний
	    if (triggered_events>0):
		logging.info("WARNING: New alerts triggered: {}.".format(triggered_events))
		triggered_events = 0
	    # Пишем в лог сколько записей мы отправили в Jabber, MySQL и Orale Apex
	    logging.info("Alerts sended to Jabber: {}. Alerts sended to MySQL: {}. Alerts sended to Oracle Apex: {}.".format(jCount,send_query['total'],apex_query['total']))
	    # Пишем в лог о завершении обработки
	    logging.info("All events have been processed.")
	    logging.info("-------")
	time.sleep(sleep_int*pause_ratio)

# ------- Служебный блок: создание и управление демоном -------

class MyDaemon(Daemon):
    def run(self):
        main()

if __name__ == "__main__":
    daemon = MyDaemon('/var/run/attractor.pid','/dev/null',logfile,logfile)
    if len(sys.argv) == 2:
        if   'start'     == sys.argv[1]:
            daemon.start()
        elif 'faststart' == sys.argv[1]:
            daemon.start()
        elif 'stop'      == sys.argv[1]:
            daemon.stop()
        elif 'restart'   == sys.argv[1]:
            daemon.restart()
        else:
            print "Attractor: "+sys.argv[1]+" - unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)

# ------- Конец служебного блока -------