# -*- coding: utf-8 -*-
"""
Created on Sat Aug 15 13:26:32 2020

@author: Laxman
"""

import pandas as pd 
import numpy as np 
import os 

from MaterialProperties import WoodMaterial

## changing the directory to DesignTool is essential for the modules to load shearwall database
file_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(file_path)

shearwall_database = pd.read_csv(r'shearwall_database.csv')

# shearwall_database = pd.read_csv(r'shearwall_database_complete.csv')


diaphragm_database = pd.read_csv(r'diaphragm_database.csv')

tiedown_database = pd.read_csv(r'tie_down_database.csv')

# baseDirectory = BuildingModel.BaseDirectory 


# materialDirectory = baseDirectory + '/MaterialProperties'

# os.chdir(materialDirectory)


# initial_moisture_content = np.genfromtxt('initial_moisture_content.txt')
# final_moisture_content = np.genfromtxt('final_moisture_content.txt')
# elastic_modulus = np.genfromtxt('wood_modulusOfElasticity.txt')

# wood = WoodMaterial(initial_moisture_content, final_moisture_content, shear_stress = 270,
#                     compression_stress = 15000 , elastic_modulus = 1.7e6, elastic_modulus_min = 6.2e5)