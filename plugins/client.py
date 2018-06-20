# -*- coding: utf-8 -*-
import json
import traceback

from mantra.mantra import Mantra
from mantra.logger import get_logger
from mantra.service.ttypes import TalkException

from .util.pl import plugin

log = get_logger("MantraServer")


async def send_qr(self, user):
    async def callback(verifier):
        await self.sendText(user["mid"], verifier)

    mantra = Mantra(loop=self.loop)

    # Load existing setting if exist, so we don't overwrite it later
    if user["setting"]:
        mantra._setting = json.loads(user["setting"])

    try:
        await mantra.login(qr=True, clientType="ipad", callback=callback)
        self.save_setting(user["instance"], user["mid"], mantra._setting)
    except Exception as e:
        traceback.print_exc()
        await self.sendText(user["mid"], "「 Login 」\nLogin failed!")
        return
    finally:
        await mantra.close()

    if mantra.mid == user["mid"]:
        data = self.db.load_table("users").find_one(mid=mantra.mid)
        result = await self.instance[user["instance"]].start_client(data)
        if result["status"] == "ok":
            log.info(f"{mantra.mid} started on instance {user['instance']}")
        else:
            log.warn(f"{mantra.mid} failed to start on instance {user['instance']}")

    await self.sendText(user["mid"], "「 Login 」\nLogin failed!")


@plugin(group="Client")
async def login(self, msg, args):
    if msg.from_ in self._var["in_cmd"]:
        await self.sendText(msg.sender, "「 Login 」\nAlready requested!")
        return
    user = self.db.load_table("users").find_one(mid=msg.from_)
    if user:
        check = await self.instance[user["instance"]].check(user["mid"])
        if check["status"] == "ok":
            await self.sendText(
                msg.sender, "「 Login 」\nYour service is already running!"
            )
        else:
            if msg.toType == 2:
                await self.sendText(msg.to, "「 Login 」\nCheckout your PM!")
            await self.sendText(
                msg.from_,
                (
                    "「 Login 」\n"
                    "Please login as soon as possible, the link only "
                    "last for 3 minutes!\n* The link is only works on your account!"
                ),
            )
            try:
                self._var["in_cmd"].add(msg.from_)
                await send_qr(self, user)
            except Exception:
                return
            finally:
                self._var["in_cmd"].remove(msg.from_)
