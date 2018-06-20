# -*- coding: utf-8 -*-
from inspect import getmembers, isfunction
from importlib import reload, import_module
from os.path import basename
from collections import defaultdict
import glob

from multidict import CIMultiDict


async def NOTIFIED_ADD_CONTACT(self, op):
    if self._setting['autoadd']:
        await self.Talk.findAndAddContactsByMid(0, op.param1, 0, None)
    if self._setting['automsg']:
        await self.sendText(op.param1, self._setting['automsg'])


async def NOTIFIED_INVITE_INTO_GROUP(self, op):
    if self.mid in op.param3.split("\x1e"):
        if op.param2 in set(self._setting['rank']):
            await self.Talk.acceptGroupInvitation(0, op.param1)


async def RECEIVE_MESSAGE(self, op):
    try:
        lenn = len(self.key)
        if op.message.text[0:lenn].lower() == self.key:
            cmd = op.message.text[lenn:].split(maxsplit=2)
            op.message.sender = op.message.from_ if \
                op.message.toType == 0 else op.message.to
            try:
                await self.commands[cmd[0]](self, op.message, cmd)
            except (KeyError, IndexError):
                pass
            except Exception as e:
                print(e)
    except Exception:
        pass


def setup(cls):
    cls.operation.update({
        5: NOTIFIED_ADD_CONTACT,
        13: NOTIFIED_INVITE_INTO_GROUP,
        26: RECEIVE_MESSAGE,
    })
    # reload(commands)
    cls.commands = CIMultiDict()
    help_list = defaultdict(list)  # temp cmd categorizer
    helps = []  # formated help

    pls = glob.glob('./plugins/*.py')
    for pl in pls:
        try:
            mod = import_module(f"plugins.{basename(pl)[:-3]}")

            # remove all attribute so there is no duplicate in case any
            # of it is removed from the source
            for attr in dir(mod):
                if attr not in ('__name__', '__file__'):
                    delattr(mod, attr)

            module = reload(mod)
        except Exception as e:
            print("Cannot load plugin: ", pl)
            print(e)
            continue
        for name, fn in getmembers(module, isfunction):
            if not hasattr(fn, 'is_plugin'):
                continue

            name = fn.name if fn.name else fn.__name__
            cls.commands.update({name: fn})
            if not fn.in_help:
                continue

            group = fn.group if fn.group is not None else "General"
            help_list[group.title()].append(name)

    core = help_list.pop('General', [])
    if core:
        helps.append("・General\n")
        helps.append("\n".join([f"{{0}} {c}" for c in sorted(core)]))
        helps.append("\n")
    for cat, cmd in sorted(help_list.items()):
        helps.append(f"\n・{cat}\n")
        helps.append("\n".join([f"{{0}} {c}" for c in sorted(cmd)]))
        helps.append("\n")
    cls._help = ''.join(helps)
