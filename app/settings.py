import os

from envparse import Env

env = Env()

DB_DSN = env.str('DB_DSN')
METRICS_URL = 'https://ratesjson.fxcm.com/DataDisplayer'
