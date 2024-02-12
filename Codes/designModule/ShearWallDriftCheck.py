# -*- coding: utf-8 -*-
"""
This file is used to check the story drift and redesign by iterating through the shear wall 
database until the design exceeds D/C ratio of 70%. If none of the higher strength shear wall 
assembly does not meet the drift limit, increase the length

Developed by: Laxman Dahal, UCLA

Created on: Aug 2020, 

Last Modified: Oct 2020

"""

__author__ = "Laxman Dahal"


from ShearWallDesignClass import DesignShearWall
from global_variables import shearwall_database
import sys
import pandas as pd

class ShearWallDriftCheck:
    ''' 
    This is the main class to check drift capacity of a shear wall at a given floor (floorIndex). If the drift limit is not met, 
    shear wall with higher apparent shear stiffness (Ga is selected from the shearwall_database. If the shear wall assembly with 
    D/C = 0.7 doesn't still satisfy the drift limit, shear wall lenght is increased at this point.

    :param caseID: the name of the building, type: str
    :param BaseDirectory: the master directory that contains model inputs, base tcl files and other files, type: str
    :param direction: direction used to run Pushover Analysis (X, Y), type: str 
    :param wallIndex: Index of the wall line given there are multiple shear wall lines in a given direction (X or Y), type: int
    :param floorIndex: index of the wall to be designed. [0, 1, 2,,...] --> [floor1, floor2, ...], type: int
    :param counter: counter to keep track of shearwall assembly in shearwall_database, type: int 
    :param wall_line_name: Name of the wall line to be designed, type: str
    :param userDefinedDetailingTag: flag to indicate of user-defined shear wall detailing is desired, type:bool 
    :param reDesignFlag: Flag to redesign, if True wall length increased by 0.5ft type: bool
    :param userDefinedDriftTag: Flag to indicate if user-defined drift limit is desired, type: bool 
    :param userDefinedDCTag: Flag to indicate of Demand/Capacity(D/C) ratio is desired, type: bool 
    :param iterateFlag: inactive flag to trigger design iteration if drift demands are not met, type bool. Default is False
    :param envelopeAnalysis: FLag to indicate if the design is . Used to distinguish between load-based vs stiffness-based design,
    :type: bool

    '''
    def __init__(
        self,
        caseID,
        BaseDirectory,
        direction,
        wallIndex,
        floorIndex,
        counter,
        wall_line_name,
        weight_factor = 1.0,
        seismic_design_level = 'Extreme',
        designScheme = 'LRFD',
        userDefinedDetailingTag = False,
        reDesignFlag = False,
        userDefinedDriftTag = False,
        userDefinedDCTag = False,
        iterateFlag=False, 
        envelopeAnalysis = False
    ):

        self.caseID = caseID
        self.BaseDirectory = BaseDirectory
        self.direction = direction
        self.wall_line_name = wall_line_name
        self.userDefinedDetailingTag = userDefinedDetailingTag
        self.reDesignFlag = reDesignFlag
        self.userDefinedDCTag = userDefinedDCTag
        self.designScheme = designScheme
        self.seismic_design_level = seismic_design_level
        self.seismic_weight_factor = weight_factor

        self.floorIndex = floorIndex
        self.wallIndex = wallIndex
        self.envelopeAnalysis = envelopeAnalysis

        self.iterateFlag = iterateFlag
        self.counter = counter

        self.userDefinedDriftTag = userDefinedDriftTag
        self.wallLengthHistory = []
        self.driftHistory = []

        # instantiate all the class methods so that the attributes can be used as class variables
        self.driftCheckAndRedesign()
        self.getShearWallDesign()
        self.getTieDownDesign()
        self.getFinalWallLength()
        # self.getOpenSeesTag()

    def driftCheckAndRedesign(self):
        """
        This method is used to check the story drift for each floor, and redesign  
        drift does not meet the drift limit (whether it is code or user imposed)
        
        :return: final shear wall and tiedown design that meets both strength and drift criteria
        """
        # initialize the DesignShearWall class to a variable with initial redesign flag set to False
        self.wallName = DesignShearWall(
            self.caseID,
            self.BaseDirectory,
            self.direction,
            self.wallIndex,
            self.floorIndex,
            self.counter,
            self.wall_line_name,
            self.seismic_weight_factor,
            self.seismic_design_level,
            self.designScheme,
            self.userDefinedDetailingTag,
            self.reDesignFlag,
            self.userDefinedDriftTag,
            self.userDefinedDCTag,
            self.iterateFlag,
            self.envelopeAnalysis,
        )
        self.wallLength = self.wallName.wallLength
        
        # self.loadType = self.wallName.loadType
        # get the drift
        self.drift = self.wallName.story_drift
        # get the drift limti
        self.driftLimit = self.wallName.driftLimit

        # story drift history to keep track as to how drift changes with each redesign step
        self.driftHistory.append(self.drift)

        # an array of Boolean. False if drift exceeds the limit
        self.driftCheck = self.drift <= self.driftLimit
        # print(self.wallName.target_unit_shear)
        self.dfCheck = self.wallName.dfCheck
        # check if any drift is not met over the height
        while not self.driftCheck:
            # while (not self.wallName.sw_design['LRFD(klf)'].values >= self.wallName.target_unit_shear/0.7) & (not self.driftCheck):

            # add the wall length if it doesnot meet the limit
            # NOTE: wall length is added every floor, not just the floor the drift exceeds

            if not (self.wallName.sw_design["%s(klf)" % self.designScheme].values == shearwall_database["%s(klf)" % self.designScheme].iloc[-1]):
                self.iterateFlag = True 
                self.counter += 1 
            else:
                print('None of the shearwall meets the drift limit @ level %s of %s, wall_%s. Please revise the shearwall length.'%(self.floorIndex, self.wall_line_name, self.wallIndex))
                print('Drift is {} at iteration no {} with unit shear demand{} & Ga:{}'.format(self.drift, self.counter, self.wallName.target_unit_shear, self.wallName.sw_dict["Ga(k/in)"]))
                print(self.driftHistory)
                sys.exit(1) 
                
            
            # if (
            #     self.wallName.sw_design["%s(klf)" % self.designScheme].values
            #     >= self.wallName.target_unit_shear / 0.7
            # ) | (
            #     self.wallName.sw_design["%s(klf)" % self.designScheme].values
            #     == shearwall_database["%s(klf)" % self.designScheme].iloc[-1]
            # ):
            #     print('This shouldnt be true')
            #     self.reDesignFlag = True
            #     self.wallLength += 0.5
            #     self.counter = 0

            # else:
            #     print('how about this')
            #     self.iterateFlag = True
            #     self.counter += 1

            # if self.dfCheck.all():
            #     break

            # keeping track of the length increase
            self.wallLengthHistory.append(self.wallName.wallLength)
            # set redesign tag to be True
            # self.reDesignFlag = True
            # initialize the DesignShearWall class again, but this time with redesign Tag set to True
            self.wallName = DesignShearWall(
                self.caseID,
                self.BaseDirectory,
                self.direction,
                self.wallIndex,
                self.floorIndex,
                self.counter,
                self.wall_line_name,
                self.seismic_weight_factor,
                self.seismic_design_level,
                self.designScheme,
                self.userDefinedDetailingTag,
                self.reDesignFlag,
                self.userDefinedDriftTag,
                self.userDefinedDCTag,
                self.iterateFlag,
                self.envelopeAnalysis,
            )
            # get the new drift after the redesign
            self.drift = self.wallName.story_drift
            # get the driftlimit
            self.driftLimit = self.wallName.driftLimit
            # perform drift check in terms of boolean
            self.driftCheck = self.drift <= self.driftLimit
            # keep track of the drift history
            self.driftHistory.append(self.drift)
            # exit the loop if all driftcheck is True
            self.dfCheck = self.wallName.dfCheck

            self.wallLength = self.wallName.wallLength
        
        
        self.wallName.sw_dict["Drift(in)"] = float(self.drift)
        # store the final shear wall design
        self.shearWallDesign = pd.DataFrame([self.wallName.sw_dict])
        # store the final tie down design
        self.tieDownDesign = self.wallName.tiedown_design

        # print(self.driftHistory)
        # return self.shearWallDesign, self.tieDownDesign

    # define a getter method that returns the final shear wall design dataframe
    def getShearWallDesign(self):
        return pd.DataFrame([self.wallName.sw_dict])

    # define a getter method that returns the final tie down design dataframe
    def getTieDownDesign(self):
        return self.tieDownDesign

    # define a getter method that returns the final wall length
    def getFinalWallLength(self):
        return self.wallLength

    def getApparentStiffness(self):
        return self.wallName.sw_dict["Ga(k/in)"]
    # #define a getter method that returns the openseestag for wall modelling in opensees
    # def getOpenSeesTag(self):

    #     tag = self.wallName.sw_design['OpenSees Tag'].values  #extracts tag as an row array
    #     tag = tag[::-1]  #changes first row from roof to first story
    #     tag = tag.reshape((-1,1))  #converts row array to column array
    #     tag = np.repeat(tag, 2, axis = 0)  #repeat array for x, and y coordinates per Zhengxiang's code input
    #     # tag = np.tile(tag, (1,2)) #double the rows
    #     self.tagPerWall = np.tile(tag, (1, int(self.wallName.wallsPerLine)))
    #     return self.tagPerWall
    #     # return self.tag

