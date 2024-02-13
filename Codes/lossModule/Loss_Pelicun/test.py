import sys
import os
import numpy as np

import pandas as pd
idx = pd.IndexSlice
pd.options.display.max_rows = 30

from pelicun_3_1.base import convert_to_MultiIndex
from pelicun_3_1.assessment import Assessment

from Run_pelicun_v3p1 import compile_demand_data
from Run_pelicun_v3p1 import pelicun_assessment1

ID = 's4_96x48_High_Stucco_Plaster_Normal'
baseDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/SurrogateModeling/DGP/woodSDA'

# pfa = pd.read_csv(os.path.join(baseDir, *['Results', ID, 'edp_outputs', 'PFA.csv']), header=None)
# sdr = pd.read_csv(os.path.join(baseDir, *['Results', ID, 'edp_outputs', 'SDR.csv']), header=None)
# rdr = pd.read_csv(os.path.join(baseDir, *['Results', ID, 'edp_outputs', 'RDR.csv']), header=None)

pfa = pd.read_csv(os.path.join(baseDir, *['Results', 'Sampled_four_story', ID, 'EDP_data', 'PFA.csv']), header=None)
sdr = pd.read_csv(os.path.join(baseDir, *['Results', 'Sampled_four_story', ID, 'EDP_data', 'SDR.csv']), header=None)

sample_size = 1000
delta_y = 0.0075
stripe = 8
PAL = Assessment({"PrintLog": False, "Seed": 415,})
raw_demands = compile_demand_data([sdr, pfa], ['SDR', 'PFA'])
baselineID = 's4_96x48'

b = pelicun_assessment1(PAL, baseDir, baselineID, raw_demands, stripe, delta_y=0.0075, sample_size=1000)
print(b)

# print(raw_demands)