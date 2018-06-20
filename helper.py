# -*- coding: utf-8 -*-
import asyncio
import time
from contextlib import suppress
from threading import Thread
from importlib import reload

from mantra import mantra, logger
import ujson as json
from poseur import Server
import dataset

import processor


log = logger.get_logger("MantraServer")


async def noop(*args, **kwargs):
    pass


def expose(func):
    func.expose = True
    return func


class MantraHelper(mantra.Mantra):
    version = "0.1"
    grace_period = 259200
    operation = {}
    _procs = []

    def __init__(self, bind=None, password=None, loop=None):
        super().__init__(loop)
        self.server = Server(loop=loop, rpc_registry=self)
        self.server.bind(bind or "tcp://127.0.0.1:5555")
        self.stopped = True
        self.password = password

        self.instance = {}
        self.heartbeat = {}

        self._polling = False
        self._var = {"debug": False, "in_cmd": set()}
        try:
            self.loadSetting()
            key = self._setting["auth"]["key"]
            self.loop.run_until_complete(
                self.login(key=key, clientType="ios", ssl=False)
            )
        except mantra.service.ttypes.TalkService as e:
            log.error(f"Cannot login: {e}")
        except Exception:
            log.info("Generating default setting..")
            self._setting = {
                "auth": {
                    "cert": "",
                    "key": "u8cb9cc8ca2ba4d57730dd141371de08b:7llu2mRLufZnUxgWD21W",
                    "token": "",
                    "type": "ios",
                },
                "rank": {"u53f4ff41bc4acd14af7d064a8e5ba942": 9},
                "key": "mantra",
            }
            self.saveSetting()
        self.init_db()

    @property
    def key(self):
        return self._setting["key"]

    @expose
    def beat(self, instance):
        self.heartbeat[instance] = time.time()

    @expose
    async def register(self, instance, password):
        if password != self.password:
            return {"status": "err", "message": "DECLINED"}
        # elif instance in self.instance:
        #     return {"status": "err", "message": "ALREADY REGISTERED"}
        else:
            self.instance[instance] = self.server.client(instance)
            await self.instance[instance].sync_setting()
            self.beat(instance)
            log.info(f"{instance} - REGISTERED")
            users = self.db.load_table("users").find(instance=instance)
            return {"status": "ok", "message": list(users)}

    @expose
    def unregister(self, instance):
        try:
            del self.instance[instance]
            del self.heartbeat[instance]
        except KeyError:
            return {"status": "err", "message": "NOT REGISTERED YET"}
        else:
            log.info(f"{instance} - UNREGISTERED")
            return {"status": "ok", "message": "UNREGISTERED"}

    @expose
    def save_setting(self, instance, mid, setting):
        if isinstance(setting, dict):
            setting = json.dumps(setting)
        update = self.db.load_table("users").update(
            dict(mid=mid, instance=instance, setting=setting), ["mid", "instance"]
        )
        if update == 0:
            return {"status": "err", "message": "No data updated."}
        else:
            log.info(f"{mid} setting saved.")
            return {"status": "ok", "message": ""}

    def get(self, name):
        """RPC registry get method"""
        func = getattr(self, name)
        if hasattr(func, "expose"):
            return func
        else:
            # returning None will raise an exception on client side
            return None

    def debug(self):
        self._var["debug"] = not self._var["debug"]
        log.info("Debug {}".format(self._var["debug"]))

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._poll())
        self.stopped = True
        pending = asyncio.Task.all_tasks()
        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                self.loop.run_until_complete(task)

    def saveSetting(self):
        log.info("Saving all data to file..")
        try:
            with open("setting.json", "w+") as f:
                json.dump(self._setting, f, ensure_ascii=False)
                log.info("Setting saved!")
        except Exception as e:
            log.debug(f"saveSetting: {e}")

    def loadSetting(self):
        try:
            with open("setting.json", "r") as f:
                self._setting = json.load(f)
                log.info("Setting loaded!")
        except Exception as e:
            log.debug(f"loadSetting: {e}")

    def init_db(self):
        db = dataset.connect(
            "sqlite:///database.sqlite",
            engine_kwargs={"connect_args": {"check_same_thread": False}},
        )
        users_query = """CREATE TABLE IF NOT EXISTS users (
                         mid text PRIMARY KEY,
                         instance text NOT NULL,
                         setting text NOT NULL default ''
                        ) WITHOUT ROWID;"""
        db.query(users_query)
        self.db = db
        log.info("Database loaded.")

    def start(self):
        if self.authToken is None:
            try:
                if self._setting["auth"]["key"]:
                    key = self._setting["auth"]["key"]
                    self.loop.run_until_complete(
                        self.login(key=key, clientType="ios", ssl=False)
                    )
                else:
                    log.error("Authkey not found, please login manually.")
                    return
                self.start()
                return
            except Exception:
                log.warn("Mantra not logged in")
        if self.stopped:
            self.stopped = False
            t = Thread(target=self.run)
            t.daemon = True
            t.start()
            log.info("Mantra Started!")
        else:
            log.warn("Mantra Already started!")

    def stop(self):
        self._polling = False

    async def _poll(self):
        self._polling = True
        while self._polling:
            try:
                ops = await self.stream()
                for op in ops:
                    asyncio.ensure_future(self._processor(op))
            except EOFError:
                pass
            except Exception as e:
                log.error("_loop: {}".format(e))
        log.info("Goodbye!")

    async def _processor(self, op):
        if self._var["debug"]:
            print("")
            log.debug(op)
            print("")

        await self.operation.get(op.type, noop)(self, op)

    @staticmethod
    def load_processor(proc):
        proc.setup(MantraHelper)
        MantraHelper._procs.append(proc)

    @staticmethod
    def reload_processor():
        for proc in MantraHelper._procs:
            p = reload(proc)
            p.setup(MantraHelper)


MantraHelper.load_processor(processor)
