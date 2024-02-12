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



import numpy as np 
import pandas as pd 
import os 
import pickle


from ShearWallDriftCheck import ShearWallDriftCheck
from FinalShearWallDesign_allFloors import FinalShearWallDesign

class RDADesignIterationClass():
    ''' 
    This class iterates the shear wall design such that the drift limit (code-based or user-defined) is met. In addition, this 
    class also designs for the shear wall along the height not only a single floor. 

    :param caseID: the name of the building, type: str
    :param BaseDirectory: the master directory that contains model inputs, base tcl files and other files, type: str
    :param direction: direction used to run Pushover Analysis (X, Y), type: str/list
    :param numWallsPerLine: number of shear wall per shear wall line, type: int/list
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
                numWallsPerLine, 
                counter, 
                wall_line_name,
                weight_factor = 1.0, 
                seismic_design_level = 'Extreme',
                designScheme = 'LRFD',
                mat_ext_int = 'Stucco_GWB',
                userDefinedDetailingTag = False, 
                reDesignFlag = False, 
                userDefinedDriftTag = False, 
                userDefinedDCTag = False, 
                iterateFlag = False , 
                envelopeAnalysis = False
                ):
        
        self.caseID = caseID
        self.BaseDirectory = BaseDirectory 
        self.direction = direction 
        self.wall_line_name = wall_line_name
        self.userDefinedDetailingTag = userDefinedDetailingTag
        self.reDesignFlag = reDesignFlag
        self.userDefinedDCTag = userDefinedDCTag
        self.numWallsPerLine = numWallsPerLine
        self.envelopeAnalysis = envelopeAnalysis
        self.designScheme = designScheme
        self.seismic_design_level = seismic_design_level
        self.mat_nsc_ext_int = mat_ext_int
        self.seismic_weight_factor = weight_factor
        
        self.iterateFlag = iterateFlag
        self.counter = counter
        
        self.userDefinedDriftTag = userDefinedDriftTag 


        floorIndex = 0
        globals()['%s_wall%d'%(self.wall_line_name[0],0)] = ShearWallDriftCheck(self.caseID, self.BaseDirectory, self.direction[0], 0, floorIndex, self.counter, 
                                                                                self.wall_line_name[0],self.seismic_weight_factor, self.seismic_design_level, 
                                                                                self.designScheme,
                                                                                self.userDefinedDetailingTag, 
                                                                                self.reDesignFlag, self.userDefinedDriftTag, self.userDefinedDCTag, 
                                                                                self.iterateFlag, envelopeAnalysis = False)
        self.Fx = globals()['%s_wall%d'%(self.wall_line_name[0],0)].wallName.Fx  #first line = first story
        #print('All Fx is',self.Fx)
        self.storyShear = np.cumsum(self.Fx)
        #print('story shear is', self.storyShear)
        self.baseShear = globals()['%s_wall%d'%(self.wall_line_name[0],0)].wallName.baseShear

        self.numStory = globals()['%s_wall%d'%(self.wall_line_name[0],0)].wallName.numFloors
        self.BatchDesign(wall_line_name, numWallsPerLine, floorIndex)
        #self.DesignAlongHeight()
        
        designShearDemandX, designShearDemandY, totalStoryForceX, totalStoryForceY = self.BatchDesign(wall_line_name, numWallsPerLine, floorIndex)
        self.shearWallShearX_AllFloor = np.zeros([self.numStory, designShearDemandX.size])
        self.shearWallShearY_AllFloor = np.empty([self.numStory, designShearDemandY.size])

        self.totalStoryForceX_All = np.zeros([self.numStory, totalStoryForceX.size])
        self.totalStoryForceY_All = np.empty([self.numStory, totalStoryForceY.size])

        for x in range(self.numStory):
            self.shearWallShearX_AllFloor[x], self.shearWallShearY_AllFloor[x], self.totalStoryForceX_All[x], self.totalStoryForceY_All[x] = self.BatchDesign(wall_line_name, numWallsPerLine, x)

        # for x in range(self.numStory):
        #     self.shearWallShearX_AllFloor[x], self.shearWallShearY_AllFloor[x] = self.BatchDesign(wall_line_name, numWallsPerLine, x)
        
        self.saveData()
        self.UltimateDesign()

    def BatchDesign(self, wall_line_name, numWallsPerLine, floorIndex):
        self.GaValX = []
        self.wallLengthX = []
        self.momentArmX = []
        self.GaValY = []
        self.wallLengthY = []
        self.momentArmY = []
        self.perLinealShearDemandX_Flexible = []
        self.perLinealShearDemandY_Flexible = []


        for i in range(len(self.wall_line_name)):
            for j in range(numWallsPerLine[i]):
                globals()['%s_wall%d'%(self.wall_line_name[i],j)] = ShearWallDriftCheck(self.caseID, self.BaseDirectory, self.direction[i], j, floorIndex, 
                                                                                        self.counter, wall_line_name[i], self.seismic_weight_factor,
                                                                                        self.seismic_design_level, 
                                                                                        self.designScheme,
                                                                                        self.userDefinedDetailingTag, self.reDesignFlag, 
                                                                                        self.userDefinedDriftTag, self.userDefinedDCTag, 
                                                                                        self.iterateFlag, envelopeAnalysis = False)
                if self.direction[i] == 'X':
                    self.GaValX.append(globals()['%s_wall%d'%(self.wall_line_name[i],j)].getApparentStiffness())
                    self.wallLengthX.append(globals()['%s_wall%d'%(self.wall_line_name[i],j)].wallLength)

                    #self.Fx = globals()['%s_wall%d'%(self.wall_line_name[0],0)].wallName.Fx[::-1][[floorIndex]]
                    #self.Fx = globals()['%s_wall%d'%(self.wall_line_name[0],0)].wallName.Fx[[floorIndex]]
                    #print(self.GaValX)
                    #print('this at level %s is %s'%(floorIndex, self.Fx))
                    self.ex = globals()['%s_wall%d'%(self.wall_line_name[i],j)].wallName.accidentalTorsion
                    self.Ax = globals()['%s_wall%d'%(self.wall_line_name[i],j)].wallName.torsionalIrregularity
                    self.rhoX = globals()['%s_wall%d'%(self.wall_line_name[i],j)].wallName.redundancyFactor
                    self.momentArmX.append(globals()['%s_wall%d'%(self.wall_line_name[i],j)].wallName.momentArm)
                    self.perLinealShearDemandX_Flexible.append(globals()['%s_wall%d'%(self.wall_line_name[i],j)].wallName.target_unit_shear)
                    #self.torsionalMomentX = self.ex * self.Fx[[floorIndex]] * self.Ax * self.rhoX
                    #print('inside loop', self.torsionalMomentX)
                else:
                    self.GaValY.append(globals()['%s_wall%d'%(self.wall_line_name[i],j)].getApparentStiffness())
                    #self.Fx = globals()['%s_wall%d'%(self.wall_line_name[0],0)].wallName.Fx[::-1][floorIndex] 
                    self.wallLengthY.append(globals()['%s_wall%d'%(self.wall_line_name[i],j)].wallName.wallLength)
                    self.ey = globals()['%s_wall%d'%(self.wall_line_name[i],j)].wallName.accidentalTorsion
                    self.Ay = globals()['%s_wall%d'%(self.wall_line_name[i],j)].wallName.torsionalIrregularity
                    self.rhoY = globals()['%s_wall%d'%(self.wall_line_name[i],j)].wallName.redundancyFactor
                    self.momentArmY.append(globals()['%s_wall%d'%(self.wall_line_name[i],j)].wallName.momentArm)
                    self.perLinealShearDemandY_Flexible.append(globals()['%s_wall%d'%(self.wall_line_name[i],j)].wallName.target_unit_shear)
                    # self.torsionalMomentY = self.ey[0] * self.baseShear

        self.torsionalMomentX = self.ex * self.Fx[[floorIndex]] * self.Ax * self.rhoX
        #print('Fx after the loop is', self.Fx[[floorIndex]])
        #print('Torsional Moment is', self.torsionalMomentX)
        self.torsionalMomentY = self.ey * self.Fx[[floorIndex]] * self.Ay * self.rhoY
        self.KxDy = np.array(self.GaValX) * np.array(self.momentArmX)
        self.KyDx = np.array(self.GaValY) * np.array(self.momentArmY)

        self.polarMomentOfInertia = np.sum(np.array(self.GaValX) * np.square(np.array(self.momentArmX))) + \
                                    np.sum(np.array(self.GaValY) * np.square(np.array(self.momentArmY)))

        self.torsionalForceX = self.torsionalMomentX * self.KxDy / self.polarMomentOfInertia
        self.torsionalForceY = self.torsionalMomentY * self.KyDx / self.polarMomentOfInertia
        #print('torsional shear at level %s is %s'%(floorIndex, self.torsionalForceX))
        
        self.storyForcePerWallX = self.Fx[[floorIndex]] * np.array(self.GaValX) / np.sum(self.GaValX)
        self.storyForcePerWallY = self.Fx[[floorIndex]] * np.array(self.GaValY) / np.sum(self.GaValY)
        #print('direct shear at level %s is %s'%(floorIndex, self.directShearX))

        self.directShearX = self.storyShear[[floorIndex]] * np.array(self.GaValX) / np.sum(self.GaValX)
        self.directShearY = self.storyShear[[floorIndex]] * np.array(self.GaValY) / np.sum(self.GaValY)
        self.totalWallShearX = self.torsionalForceX + self.directShearX
        self.totalWallShearY = self.torsionalForceY + self.directShearY

        self.totalStoryForceX = self.torsionalForceX + self.storyForcePerWallX
        self.totalStoryForceY = self.torsionalForceY + self.storyForcePerWallY
        #print(self.totalStoryForceX)
        self.perLinealShearDemandX = self.totalWallShearX / np.array(self.wallLengthX)
        self.perLinealShearDemandY = self.totalWallShearY / np.array(self.wallLengthY)
        #print(self.perLinealShearDemandX)
        self.designShearDemandX = np.maximum(self.perLinealShearDemandX, self.perLinealShearDemandX_Flexible)
        self.designShearDemandY = np.maximum(self.perLinealShearDemandY, self.perLinealShearDemandY_Flexible)

        return self.designShearDemandX, self.designShearDemandY , self.totalStoryForceX, self.totalStoryForceY
      
    def saveData(self):

        allshearwall = np.concatenate((self.shearWallShearX_AllFloor, self.shearWallShearY_AllFloor), axis = 1)
        total_walls = np.insert(np.cumsum(self.numWallsPerLine), 0, 0)

        for ii in range(len(self.wall_line_name)):
            temp = np.zeros([self.numStory, self.numWallsPerLine[ii]], dtype= float)
            os.chdir(self.BaseDirectory + "/%s_direction_wall" % self.direction[ii] + "/%s" % self.wall_line_name[ii])

            startIndex = total_walls[ii]
            endIndex = total_walls[ii + 1]

            temp[:] = allshearwall[:,startIndex:endIndex]
            # print(temp)
            # print('sw line {}, shearwall no {}, start-end index {}'.format(self.wall_line_name[ii], ii, [startIndex, endIndex]))
            np.savetxt('envelopeShearWallDemand.txt', temp, delimiter=' ')    
                #with open ('sehsh.txt', 'wb') as f: pickle.dump(temp, f)

    def UltimateDesign(self):
        d = []
        wallname = []
        #dflist = {}
        for ii in range(len(self.wall_line_name)):
            for jj in range(self.numWallsPerLine[ii]):
                globals()['swDesign%s_wall%d'%(self.wall_line_name[ii],jj)] = FinalShearWallDesign(self.caseID, self.BaseDirectory, self.direction[ii], jj, 
                                                                                                   self.numStory, self.counter, self.wall_line_name[ii],
                                                                                                   self.seismic_weight_factor, self.seismic_design_level,
                                                                                                   self.designScheme, self.mat_nsc_ext_int,
                                                                                                   self.userDefinedDetailingTag, 
                                                                                                   self.reDesignFlag, self.userDefinedDriftTag, 
                                                                                                   self.userDefinedDCTag, 
                                                                                                   self.iterateFlag, self.envelopeAnalysis)
                name = 'swDesign_%s_wall%d'%(self.wall_line_name[ii],jj+1)
                wallname.append(name)
                df = globals()['swDesign%s_wall%d'%(self.wall_line_name[ii],jj)].sw_design
                d.append(df)
        
        self.maindf = pd.concat(d, keys = wallname) #.reset_index(level = 1, drop = True)



