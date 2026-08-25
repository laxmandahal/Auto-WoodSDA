# -*- coding: utf-8 -*-
"""
This file is used to check the story drift and redesign by iterating through the shear wall 
database until the design exceeds D/C ratio of 70%. If none of the higher strength shear wall 
assembly does not meet the drift limit, increase the length

Developed by: Laxman Dahal, UCLA

Created on: Aug 2020, 

Last Modified: Oct 2020

"""

__author__ = 'Laxman Dahal'


import pandas as pd
import numpy as np
import os
import sys

cwd = os.path.dirname(__file__)
code_dir = os.path.dirname(cwd)
sys.path.append(os.path.join(code_dir, 'schema'))
from loader import load_building_config, save_building_config, as_matrix

from ShearWallDriftCheck import ShearWallDriftCheck

class FinalShearWallDesign():
    ''' 
    This class iterates the shear wall design such that the drift limit (code-based or user-defined) is met. In addition, this 
    class also designs for the shear wall along the height not only a single floor. 

    :param caseID: the name of the building, type: str
    :param BaseDirectory: the master directory that contains model inputs, base tcl files and other files, type: str
    :param direction: direction used to run Pushover Analysis (X, Y), type: str 
    :param wallIndex: Index of the wall line given there are multiple shear wall lines in a given direction (X or Y), type: int
    :param numFloors: number of floors in a building. type: int
    :param counter: counter to keep track of shearwall assembly in shearwall_database, type: int 
    :param wall_line_name: Name of the wall line to be designed, type: str
    :param userDefinedDetailingTag: flag to indicate of user-defined shear wall detailing is desired, type:bool 
    :param reDesignFlag: Flag to redesign, if True wall length increased by 0.5ft type: bool
    :param userDefinedDriftTag: Flag to indicate if user-defined drift limit is desired, type: bool 
    :param userDefinedDCTag: Flag to indicate of Demand(D)/Capacity(C) ratio is desired, type: bool 
    :param iterateFlag: inactive flag to trigger design iteration if drift demands are not met, type bool. Default is False
    :param envelopeAnalysis: FLag to indicate if the design is . Used to distinguish between load-based vs stiffness-based design,
    :type: bool

    '''
    
    def __init__(self, 
                caseID, 
                BaseDirectory, 
                direction, 
                wallIndex, 
                numFloors, 
                counter, 
                wall_line_name,
                # Ss, 
                # S1,
                df_inputs,
                weight_factor = 1.0,
                seismic_design_level = 'Extreme',
                designScheme = 'LRFD',
                mat_ext_int = 'Stucco_GWB',
                userDefinedDetailingTag = False,
                reDesignFlag = False, 
                userDefinedDriftTag=False,
                userDefinedDCTag=False,
                iterateFlag=False, 
                envelopeAnalysis=False ):
        
        self.caseID = caseID
        self.BaseDirectory = BaseDirectory 
        self.direction = direction 
        self.wall_line_name = wall_line_name
        self.userDefinedDetailingTag = userDefinedDetailingTag
        self.reDesignFlag = reDesignFlag
        self.userDefinedDCTag = userDefinedDCTag
        self.wallIndex = wallIndex
        self.envelopeAnalysis = envelopeAnalysis
        self.designScheme = designScheme
        self.seismic_design_level = seismic_design_level
        self.mat_nsc_ext_int = mat_ext_int
        self.seismic_weight_factor = weight_factor
        # self.Ss = Ss
        # self.S1 = S1
        self.numFloors = numFloors
        
        self.iterateFlag = iterateFlag
        self.counter = counter
        
        self.userDefinedDriftTag = userDefinedDriftTag 
        # self.wallLength = wallLength
        self.wallLengthHistory = []
        self.driftHistory = []
        
        #instantiate all the class methods so that the attributes can be used as class variables 
        self.read_inputs()
        self.DesignIteration(df_inputs)
        self.FinalDesign(df_inputs)
        # if self.numFloors == 1:

    def read_inputs(self):
        """
        This method is used to read all the needed shear wall user inputs.
        The input files should be .txt files in respective directories
        
        :return: instantiates required class variables and attributes 
        """

        # Sourced from the archetype's building_config.yaml (Codes/schema/) instead of the
        # BuildingInfo/<archetype>/*.txt tree. as_matrix reproduces the exact array shape
        # np.genfromtxt() would have produced, so the reshape branches below are unchanged.
        self.config = load_building_config(self.BaseDirectory)
        wall_lines = self.config.x_wall_lines if self.direction == "X" else self.config.y_wall_lines
        wl = next((w for w in wall_lines if w.name == self.wall_line_name), None)
        if wl is None:
            raise ValueError(
                f"No wall line named {self.wall_line_name!r} in {self.direction}_wall_lines "
                f"for {self.caseID!r}"
            )
        self.wl = wl

        self.pinching4IndexShearWall = as_matrix(wl.geometry.pinching4_index).astype(int)

        if self.numFloors == 1:
            self.no_of_walls = self.pinching4IndexShearWall.size
        else:
            self.no_of_walls = self.pinching4IndexShearWall.size / self.pinching4IndexShearWall.shape[0]

        if self.numFloors > 1:
            if self.no_of_walls == 1:
                self.pinching4IndexShearWall = as_matrix(wl.geometry.pinching4_index).astype(int)[:, None]
            else:
                self.pinching4IndexShearWall = as_matrix(wl.geometry.pinching4_index).astype(int)
        else:
            if self.no_of_walls == 1:
                self.pinching4IndexShearWall = np.array([[int(as_matrix(wl.geometry.pinching4_index))]])[:None]
            else:
                self.pinching4IndexShearWall = np.array([list(as_matrix(wl.geometry.pinching4_index))]).astype(int)[:None]

        self.panels = self.config.design_outputs.x_panels if self.direction == "X" else self.config.design_outputs.z_panels
        if self.panels.material_number is None or self.mat_nsc_ext_int not in self.panels.material_number:
            raise ValueError(
                f"design_outputs.material_number has no {self.mat_nsc_ext_int!r} entry for "
                f"{self.caseID!r} {self.direction} panels"
            )
        self.pinching4MaterialNumber = as_matrix(self.panels.material_number[self.mat_nsc_ext_int])

    def DesignIteration(self, df_inputs):
        '''
        Method to iterate the design along the height of the building. 

        :return: Final shear wall design length that meets the specified drift demand
        '''
        
        temp1 = []
        temp2 = []
        d = []
        h = []
        for i in range(0, self.numFloors):
            sw = ShearWallDriftCheck(self.caseID, self.BaseDirectory, self.direction, self.wallIndex,
                                     i, self.counter, self.wall_line_name,
                                     df_inputs,
                                     self.seismic_weight_factor, self.seismic_design_level,
                                     self.designScheme, self.userDefinedDetailingTag,               
                                     self.reDesignFlag, self.userDefinedDriftTag, self.userDefinedDCTag, 
                                     self.iterateFlag, self.envelopeAnalysis)
            # print(sw.driftHistory)
            
            temp1.append(sw.wallName.sw_dict)
            temp2.append(sw.wallName.td_dict)
            d.append(sw.getFinalWallLength())
            h.append(sw.wallName.story_height)
        self.finalWallLength = np.array(d)
        self.finalWallHeight = np.array(h)
        
        self.sw_design = pd.DataFrame(temp1)
        
        self.tiedown_design = pd.DataFrame(temp2)

        if self.panels.length is None or self.panels.height is None:
            raise ValueError(
                f"design_outputs.length/height missing for {self.caseID!r} {self.direction} panels -- "
                "cannot write final wall design back"
            )
        # length/height are always stored as real nested lists (never squeezed by np.genfromtxt's
        # single-row/column quirk the way as_matrix()'d reads are), so build plain 2-D arrays here
        # rather than reusing as_matrix -- these get indexed [row, col] below regardless of shape.
        length_matrix = np.array(self.panels.length, dtype=float)
        height_matrix = np.array(self.panels.height, dtype=float)

        tag = self.sw_design['OpenSees Tag'].values
        tag = tag[::-1] ## this makes first row of the output of the pinching4 number to be roof instead of first floor
        # print(self.wall_line_name, self.wallIndex, tag)
        for i in range(0, self.numFloors*2, 2):
                kk = 0 + i //2
                for j in range(len(self.pinching4IndexShearWall[[kk]])):
                    # print(i, self.pinching4IndexShearWall[[kk]][j])
                    col = self.pinching4IndexShearWall[[kk]][j][self.wallIndex]
                    self.pinching4MaterialNumber[i, col] = tag[kk]
                    # Closes the length/height staleness bug: previously only material_number
                    # got regenerated after a design run, while length/height sat unchanged even
                    # when reDesignFlag lengthened the wall. Same (floor, column) mapping as the
                    # material-number write above, but unreversed row order -- self.finalWallLength[kk]
                    # already corresponds to floor kk in the same bottom-up convention length.txt
                    # used on disk (only the *material* row order is intentionally roof-first, per
                    # the comment above). finalWallLength/finalWallHeight are in feet (design-side
                    # convention, e.g. ComputeDesignForce.py divides wallLengths.txt by 12); the
                    # design_outputs matrices are in inches, matching length.txt/height.txt on disk
                    # and every downstream consumer (BuildingModelClass.py, utils_opensees.py) --
                    # verified against a fresh migration of MFD6B's pre-existing length.txt/height.txt.
                    length_matrix[kk, col] = self.finalWallLength[kk] * 12
                    height_matrix[kk, col] = self.finalWallHeight[kk] * 12

        finish_key = self.mat_nsc_ext_int
        if self.panels.material_number is None:
            self.panels.material_number = {}
        self.panels.material_number[finish_key] = self.pinching4MaterialNumber.astype(int).tolist()
        self.panels.material_number["default"] = self.pinching4MaterialNumber.astype(int).tolist()
        self.panels.length = length_matrix.tolist()
        self.panels.height = height_matrix.tolist()

        save_building_config(self.config, self.BaseDirectory)
        # self.driftRecord = pd.DataFrame(drift)
        # return self.sw_final_design
        return self.finalWallLength
        
    def FinalDesign(self, df_inputs):
        ''' Method to instantiate the ShearWallDriftCheck class with the final design length

        :return: shear wall and tie-down design that meets the specified drift demand 
        '''
        
        temp1 = []
        temp2 = []
        # self.DesignLength = np.array([max(self.finalWallLength)])
        self.DesignLength = max(self.finalWallLength)
        for i in range(0, self.numFloors):
            sw = ShearWallDriftCheck(self.caseID, self.BaseDirectory, self.direction, self.wallIndex, 
                                      i, self.counter, self.wall_line_name, 
                                      df_inputs,
                                      self.seismic_weight_factor, self.seismic_design_level,
                                      self.designScheme, self.userDefinedDetailingTag,               
                                      self.reDesignFlag, self.userDefinedDriftTag, self.userDefinedDCTag, 
                                      self.iterateFlag, self.envelopeAnalysis)
            temp1.append(sw.wallName.sw_dict)
            temp2.append(sw.wallName.td_dict)
            
        # self.wallsPerLine = sw.wallName.wallsPerLine
        
        self.sw_final_design = pd.DataFrame(temp1)
        # print(self.sw_final_design)
        
        self.tiedown_final_design = pd.DataFrame(temp2)
        
        return self.sw_final_design, self.tiedown_final_design
        


        
# if __name__ == '__main__':
#     import json

#     cwd = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy/Codes/woodSDPA'
#     baseDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/RegionalStudy'
#     dataDir = os.path.join(baseDir, 'data')
#     woodSDPA_dir = os.path.join(baseDir, *['Codes', 'woodSDPA'])
#     baseline_BIM = json.load(open(os.path.join(dataDir, 'Baseline_archetype_info_w_periods.json')))
#     caseID = list(baseline_BIM.keys())[0]
#     baseline_info_dir = os.path.join(cwd, *['BuildingInfo', caseID])
#     direction = baseline_BIM[caseID]['Directions']
#     wall_line_name = baseline_BIM[caseID]['wall_line_names']
#     num_walls_per_line = baseline_BIM[caseID]['num_walls_per_wallLine']
#     counter = 0

#     sw_design = FinalShearWallDesign(caseID, baseline_info_dir, 'X', wallIndex=0, numFloors=int(caseID.split('_')[0][1]), 
#                                 counter=counter, wall_line_name='gridA', Ss=2, S1=0.7,
#                                 weight_factor=1, seismic_design_level='High'
#                                 )
        
        
        
        