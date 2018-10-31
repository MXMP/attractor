import xmpp


class JabberBot:
    def __init__(self, jid, jps, jcr, jnn):
        jid = xmpp.JID(jid)
        self.user, self.server, self.password, self.jcr, self.jnn, = jid.getNode(), jid.getDomain(), jps, jcr, jnn

    def connect(self):
        self.conn = xmpp.Client(self.server, debug=[])
        return self.conn.connect()

    def auth(self):
        return self.conn.auth(self.user, self.password)

    def joinroom(self):
        self.conn.sendInitPresence(1)
        self.conn.send(xmpp.Presence(to="%s/%s" % (self.jcr, self.jnn)))

    def proc(self):
        self.conn.Process(1)

    def send_msg(self, msg):
        self.conn.send(xmpp.protocol.Message(self.jcr, msg, 'groupchat'))

    def disconnect(self):
        self.conn.send(xmpp.Presence(typ='unavailable'))

    def is_alive(self):
        try:
            self.conn.send(xmpp.Presence(status=None, show=None))
            alive = True
        except IOError:
            alive = False
        return alive
