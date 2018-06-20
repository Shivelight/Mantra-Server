import argparse
import asyncio
import helper
import uvloop

parser = argparse.ArgumentParser()
parser.add_argument("--bind", help="Bind Mantra-Server to this address.")
args = parser.parse_args()
print(args)

loop = asyncio.new_event_loop()

serv = helper.MantraHelper(bind=args.bind, loop=loop)
serv.start()
