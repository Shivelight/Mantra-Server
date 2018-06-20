# -*- coding: utf-8 -*-
import time

from sqlalchemy.exc import IntegrityError
from mantra.service.ttypes import TalkException

from .util.pl import plugin


@plugin(group="Admin")
async def instance(self, msg, args):
    if self._setting["rank"].get(msg.from_, 0) < 5:
        return
    strings = []
    current = time.time()
    for i in self.instance.keys():
        hb = current - self.heartbeat[i]
        if hb <= 5:
            heart = "Good"
        elif hb > 10:
            heart = "Bad"
        else:
            heart = "Ok"
        strings.append(f"- {i} ({heart}:{int(hb)})")
    avail = "\n".join(strings)
    await self.sendText(msg.sender, ("「 Mantra 」\n" f"Online Instance:\n{avail}"))


@plugin(group="Admin")
async def clientadd(self, msg, args):
    if self._setting["rank"].get(msg.from_, 0) < 5:
        return
    if len(args) == 1:
        await self.sendText(
            msg.sender, "「 Client 」\nCorrect Usage: clientadd <mid> <instance>"
        )
    else:
        try:
            contact = await self.Talk.getContact(args[1])
            instance = args[2]
            # days, instance = args[2].split(maxsplit=1)
            # subs = int(args[2])
        except TalkException:
            await self.sendText(msg.sender, "「 Client 」\nInvalid mid.")
            return
        except IndexError:
            await self.sendText(msg.sender, "「 Client 」\nInstance name needed.")
            return

        if instance not in self.instance:
            await self.sendText(msg.sender,
                                f"「 Client 」\nInstance {instance} is not registered.")
            return

        try:
            self.db.load_table("users").insert(dict(mid=contact.mid, instance=instance))
        except IntegrityError:
            await self.sendText(msg.sender, f"「 Client 」\n{contact.mid} already added.")
        else:
            await self.sendText(
                msg.sender, f"「 Client 」\n{contact.mid} has been added."
            )
            await self.sendContact(msg.sender, contact.mid)


@plugin(group='Admin')
async def clientdel(self, msg, args):
    if self._setting["rank"].get(msg.from_, 0) < 5:
        return
    if len(args) == 1:
        await self.sendText(
            msg.sender, "「 Client 」\nCorrect Usage: clientdel <mid>"
        )
    else:
        result = self.db.load_table("users").find_one(mid=args[1])
        if result:
            try:
                await self.instance[result["instance"]].stop_client(args[1])
            except Exception:
                pass
            finally:
                self.db.load_table("users").delete(mid=args[1])
                await self.sendContact(msg.sender, args[1])
