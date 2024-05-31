# -*- coding: utf-8 -*-
"""
Created on Sat Aug 15 13:26:32 2020

@author: Laxman
"""

import pandas as pd 
import os 

cwd = os.path.dirname(__file__)
code_dir = os.path.dirname(cwd)
root_dir = os.path.dirname(code_dir)

# from Codes.designModule.MaterialProperties1 import WoodMaterial


shearwall_database = pd.read_csv(os.path.join(root_dir, 'Databases', 'shearwall_database.csv'))

diaphragm_database = pd.read_csv(os.path.join(root_dir, 'Databases', 'diaphragm_database.csv'))

tiedown_database = pd.read_csv(os.path.join(root_dir, 'Databases', 'tie_down_database.csv'))

