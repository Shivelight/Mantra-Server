import time

from poseur import Server

import helper


def expose(func):
    func.expose = True
    return func


class MantraServer(object):

    def __init__(self, loop=None, bind=None):
        self.server = Server(loop=loop, rpc_registry=self)
        self.server.bind(bind or "tcp://127.0.0.1:5555")

        self.mantra = helper.MantraHelper(loop=loop, server=self)

        self.instance = {}
        self.heartbeat = {}

    @expose
    def beat(self, instance):
        self.heartbeat[instance] = time.time()

    @expose
    def register(self, instance):
        self.instance[instance] = self.server.client(instance)
        self.beat(instance)
        return f"{instance} - REGISTERED"

    @expose
    def unregister(self, instance):
        try:
            del self.instance[instance]
            del self.heartbeat[instance]
        except KeyError:
            return f"{instance} - NOT REGISTERED YET"
        else:
            return f"{instance} - UNREGISTERED"

    def start(self):
        self.mantra.start()

    def get(self, name):
        func = getattr(self, name)
        if hasattr(func, 'expose'):
            return func
        else:
            return None
