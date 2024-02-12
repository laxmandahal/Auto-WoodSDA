# -*- coding: utf-8 -*-
"""
Created on Sat Aug 15 11:54:12 2020

@author: Laxman
"""

class WoodMaterial():
    
        
    def __init__(self, initial_moisture_content, final_moisture_content, shear_stress, 
                 compression_stress, elastic_modulus, elastic_modulus_min):
        '''
        tension, shear and compression stress values are parallel to the grain [AWC NDS 2018 Table 4A]
        input units: psf 
        output units: ksi
        '''
        self.initial_moisture_content = initial_moisture_content
        self.final_moisture_content = final_moisture_content
        self.shear_stress = shear_stress/1000 
        self.compression_stress = compression_stress/1000
        self.elastic_modulus = elastic_modulus 
        self.elastic_modulus_min = elastic_modulus_min
        
    
    # def Sheathing(self):

# a = WoodMaterial(bending_stress = 1450, tension_stress=  1500, shear_stress= 270, 
#                      compression_stress=1500, elastic_modulus=1.7e6, elastic_modulus_min= 6.2e5)
# print(a.bending_stress)