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

        self.numFloors = numFloors
        
        self.iterateFlag = iterateFlag
        self.counter = counter
        
        self.userDefinedDriftTag = userDefinedDriftTag 
        # self.wallLength = wallLength
        self.wallLengthHistory = []
        self.driftHistory = []
        
        #instantiate all the class methods so that the attributes can be used as class variables 
        self.read_inputs()
        self.DesignIteration()
        self.FinalDesign()
        # if self.numFloors == 1:
        # dummysw = ShearWallDriftCheck(self.caseID, self.BaseDirectory, self.direction, self.wallIndex,
        #                             0, self.counter, self.wall_line_name,self.seismic_weight_factor, self.seismic_design_level,
        #                             self.designScheme, self.userDefinedDetailingTag,               
        #                             self.reDesignFlag, self.userDefinedDriftTag, self.userDefinedDCTag, 
        #                             self.iterateFlag, self.envelopeAnalysis)
        # self.no_of_walls = dummysw.wallName.no_of_walls
        # print(self.no_of_walls)
        # self.getFinalWallLength()
        # self.getFinalWallHeight()
        # self.getOpenSeesTag()
    def read_inputs(self):
        """
        This method is used to read all the needed shear wall user inputs.
        The input files should be .txt files in respective directories
        
        :return: instantiates required class variables and attributes 
        """

        # os.chdir(
        #     self.BaseDirectory
        #     + "/%s_direction_wall" % self.direction
        #     + "/%s" % self.wall_line_name
        #     + "/MaterialProperties"
        # )
        # self.pinching4IndexShearWall = np.genfromtxt("pinching4Index_shearWall%d.txt"%self.wallIndex).astype(int)
        ##### Changelog (12/29/2021): Moving pinching4index into geometry folder. Trying to make it work with only one .txt file input 
        os.chdir(
            self.BaseDirectory
            + "/%s_direction_wall" % self.direction
            + "/%s" % self.wall_line_name
            + "/Geometry"
        )
        
        
        self.pinching4IndexShearWall = np.genfromtxt("pinching4Index.txt").astype(int)

        # if self.numFloors == 1:
        #     no_of_walls = self.no_of_walls
        # else:
        if self.numFloors == 1:
            # print(self.wallLength, self.wallLength.dtype)
            self.no_of_walls = self.pinching4IndexShearWall.size
        else:
            self.no_of_walls = self.pinching4IndexShearWall.size / self.pinching4IndexShearWall.shape[0]

        # no_of_walls = self.pinching4IndexShearWall.size / self.pinching4IndexShearWall.shape[0]
        if self.numFloors > 1: 
            if self.no_of_walls == 1:
                self.pinching4IndexShearWall = np.genfromtxt("pinching4Index.txt").astype(int)[:,None]
            else:
                self.pinching4IndexShearWall = np.genfromtxt("pinching4Index.txt").astype(int)
        else:
            if self.no_of_walls == 1:
                # self.pinching4IndexShearWall = [np.genfromtxt("pinching4Index.txt").astype(int)]
                self.pinching4IndexShearWall = np.array([[int(np.genfromtxt("pinching4Index.txt"))]])[:None]
            else:
                # self.pinching4IndexShearWall = np.genfromtxt("pinching4Index.txt").astype(int)[:,None]
                self.pinching4IndexShearWall = np.array([list(np.genfromtxt("pinching4Index.txt"))]).astype(int)[:None]

        # if int(self.no_of_walls) == 1: 
        #     self.pinching4IndexShearWall = np.genfromtxt("pinching4Index.txt").astype(int)[:,None]
        # print(self.pinching4IndexShearWall, self.pinching4IndexShearWall.shape)
        # self.pinching4IndexNonStructural = np.genfromtxt("pinching4Index_nsc%d.txt"%self.wallIndex).astype(int)
        # self.pinching4MaterialNumber_nsc = np.genfromtxt("pinching4MaterialNumber_nsc%d.txt"%self.wallIndex).astype(int)

        os.chdir(self.BaseDirectory + "/StructuralProperties" + "/%sWoodPanels"%self.direction)
        self.pinching4MaterialNumber = np.genfromtxt("Pinching4MaterialNumber_%s.txt"%self.mat_nsc_ext_int)

    def DesignIteration(self):
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
                                     i, self.counter, self.wall_line_name,self.seismic_weight_factor, self.seismic_design_level,
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

        tag = self.sw_design['OpenSees Tag'].values
        tag = tag[::-1] ## this makes first row of the output of the pinching4 number to be roof instead of first floor
        # print(self.wall_line_name, self.wallIndex, tag)
        for i in range(0, self.numFloors*2, 2):
                kk = 0 + i //2
                for j in range(len(self.pinching4IndexShearWall[[kk]])):
                    # print(i, self.pinching4IndexShearWall[[kk]][j])
                    self.pinching4MaterialNumber[i, self.pinching4IndexShearWall[[kk]][j][self.wallIndex]] = tag[kk]
                    # print(self.pinching4MaterialNumber)
                    # for idx in range(len(self.pinching4IndexShearWall[[kk]][j])):
                        # print(i, self.pinching4IndexShearWall[[kk]][j][idx])
                        # self.pinching4MaterialNumber[i, idx] = tag[kk]
                # for jj in range(len(self.pinching4IndexNonStructural)):
                #     self.pinching4MaterialNumber[i+1, self.pinching4IndexNonStructural[jj]] = 

        os.chdir(self.BaseDirectory + "/StructuralProperties" + "/%sWoodPanels"%self.direction)
        # print(self.pinching4MaterialNumber)
        ######## Logchange: 06/27/2022
        #### issue: in trying to save the pinching4 as pinching4MaterialNumber.txt, the program was overwriting the saved
        ####        pinching4 number after each loop thus resulting in the same values as the input pinching4 numbers
        np.savetxt("Pinching4MaterialNumber_%s.txt"%self.mat_nsc_ext_int, X = self.pinching4MaterialNumber.astype(int),
                    delimiter=" ", fmt="%i")
        np.savetxt('Pinching4MaterialNumber.txt', X = self.pinching4MaterialNumber.astype(int), delimiter=" ", fmt="%i")
        # self.driftRecord = pd.DataFrame(drift)
        # return self.sw_final_design
        return self.finalWallLength
        
    def FinalDesign(self):
        ''' Method to instantiate the ShearWallDriftCheck class with the final design length

        :return: shear wall and tie-down design that meets the specified drift demand 
        '''
        
        temp1 = []
        temp2 = []
        # self.DesignLength = np.array([max(self.finalWallLength)])
        self.DesignLength = max(self.finalWallLength)
        for i in range(0, self.numFloors):
            sw = ShearWallDriftCheck(self.caseID, self.BaseDirectory, self.direction, self.wallIndex, 
                                      i, self.counter, self.wall_line_name,self.seismic_weight_factor, self.seismic_design_level,
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
        
    #def savePinching4Number(self):



    # def getFinalWallLength(self):
    #     tempLen = [[max(self.finalWallLength)],]  # convert into a list for list manipulation
    #     length_ops = tempLen * int(self.numFloors)
    #     length_ops = np.array(length_ops)  #length for opensees modeling
    #     length_perWallLine = np.repeat(length_ops, int(self.wallsPerLine), axis = 1) 
    #     return length_perWallLine
        
    
    # def getFinalWallHeight(self):
    #     height_ops = self.finalWallHeight.reshape((-1,1))
    #     height_perWallLine = np.repeat(height_ops, int(self.wallsPerLine), axis = 1)
    #     return height_perWallLine
    
    
    # # # #define a getter method that returns the openseestag for wall modelling in opensees
    # def getOpenSeesTag(self):
        
    #     tag = self.sw_final_design['OpenSees Tag'].values  #extracts tag as an row array 
    #     tag = tag[::-1]  #changes first row from roof to first story
    #     tag = tag.reshape((-1,1))  #converts row array to column array
    #     tag = np.repeat(tag, 2, axis = 0)  #repeat array for x, and y coordinates per Zhengxiang's code input
    #     # tag = np.tile(tag, (1,2)) #double the rows 
    #     self.tagPerWall = np.tile(tag, (1, int(self.wallsPerLine)))
    #     return self.tagPerWall
    #     # return self.tag
        
        
        
        
        
        