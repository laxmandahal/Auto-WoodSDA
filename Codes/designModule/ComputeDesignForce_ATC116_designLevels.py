# -*- coding: utf-8 -*-
"""
This file is used to calculate seismic base shear using ELF procedure per ASCE 07-16 section 12,
seismic story forces (horizontal force distribution), shear wall demand and tension demand for
anchorage design. The shear wall demand and tension demand calculation are based on equations
provided on SPDWS

Developed by: Zhengxiang Yi and Xingquan Guan, UCLA
Modified by: Laxman Dahal, UCLA

Created on: Aug 2020, 

Last Modified: Oct 2020

"""

__author__ = "Laxman Dahal"


import numpy as np
import os
import sys


class ComputeSeismicForce(object):
    ''' 
    A class to compute seismic forces (base shear, story force distribution, story shear distribution) using ELF procedures 
    per ASCE 07-16 section 12. Within the class, required properties of the building are read from .txt files stored within a
    specified folder. Please ensure the required inputs are stored in the designated directory for the code to run. 

    :param caseID: the name of the building, type: str
    :param BaseDirectory: the master directory that contains model inputs, base tcl files and other files, type: str
    :param direction: direction used to run Pushover Analysis (X, Y), type: str 
    :param wall_line_name: Name of the wall line to be designed, type: str
    :param wallIndex: Index of the wall within a given grid/ wall line given there are multiple walls, type: int
    :param seismic_design_level: Design levels per ATC 116 Project. Options:[Extreme, High, Moderate]
    :param designScheme: Design Scheme to be used. Options: ['LRFD', 'ASD']. Default: 'LRFD'
    :param reDesignFlag: Flag to redesign, if True wall length increased by 0.5ft type: bool
    :param envelopeAnalysis: FLag to indicate if the design is . Used to distinguish between load-based vs stiffness-based design,
    :type: bool
    :param SeismicDesignParamterFlag: If the seismic design paramters are predefined, use "False", type: bool

    '''
    def __init__(
        self,
        CaseID,
        BaseDirectory,
        direction,
        wall_line_name,
        wallIndex,
        weight_factor = 1.0,
        seismic_design_level = 'Extreme',
        designScheme = 'LRFD',
        reDesignFlag = False,
        envelopeAnalysis = False,
        SeismicDesignParameterFlag=True,
    ):

        self.direction = direction
        self.wall_line_name = wall_line_name
        self.reDesignFlag = reDesignFlag
        self.wallIndex = wallIndex
        self.designScheme = designScheme
        self.envelopeAnalysis = envelopeAnalysis
        self.BaseDirectory = BaseDirectory   
        self.seismic_design_level = seismic_design_level
        self.seismic_weight_factor = weight_factor

        if (designScheme != 'ASD') and (designScheme != 'LRFD'):
            print("Invalid design scheme. Choose between ['ASD', 'LRFD']")
            sys.exit(1)
        else: pass

        # call the methods
        self.read_in_txt_inputs(CaseID, BaseDirectory)
        self.SW_shear_demand()
        self.Anchorage_demand()

    def read_in_txt_inputs(
        self, CaseID, BaseDirectory, SeismicDesignParameterFlag=True
    ):
        '''
        Method to read required inputs (building properties) from different folders to be used to design and create openSEES models

        :param caseID: the name of the building, type: str
        :param BaseDirectory: the master directory that contains model inputs, base tcl files and other files, type: str
        :param SeismicDesignParamterFlag: If the seismic design paramters are predefined, use "False", type: bool
        '''

        self.ID = CaseID
        ##################################################################################################
        # Read in Geometry
        os.chdir(os.path.join(BaseDirectory, 'Geometry'))
        # os.chdir(BaseDirectory + "/Geometry")
        self.numberOfStories = np.genfromtxt("numberOfStories.txt").astype(int)
        self.storyHeights = np.genfromtxt("storyHeights.txt")#.tolist() #height of each floor in inches
        #height of a floor that starts with [0, h1, h2,..., hn]
        self.floorHeights = np.cumsum(np.insert(self.storyHeights, 0, 0))
        #height of a floor that starts with [h1, h2,..., hn]
        self.floor_heights = np.cumsum(self.storyHeights)
        if self.numberOfStories == 1:
            self.storyHeights = int(self.storyHeights)

        self.floorMaximumXDimension = np.genfromtxt("floorMaximumXDimension.txt")
        self.floorMaximumZDimension = np.genfromtxt("floorMaximumZDimension.txt")
        self.floorArea = np.genfromtxt("floorAreas.txt")

        self.leaningColumnNodesOpenSeesTags = np.genfromtxt("leaningColumnNodesOpenSeesTags.txt").astype(int)
        self.leaningColumnNodesXCoordinates = np.genfromtxt("leaningColumnNodesXCoordinates.txt")
        self.leaningColumnNodesZCoordinates = np.genfromtxt("leaningColumnNodesZCoordinates.txt")

        self.numberOfXDirectionWoodPanels = np.genfromtxt(
            "numberOfXDirectionWoodPanels.txt"
        ).astype(int)
        self.numberOfZDirectionWoodPanels = np.genfromtxt(
            "numberOfZDirectionWoodPanels.txt"
        ).astype(int)

        self.XDirectionWoodPanelsXCoordinates = np.genfromtxt(
            "XDirectionWoodPanelsXCoordinates.txt"
        )
        self.XDirectionWoodPanelsZCoordinates = np.genfromtxt(
            "XDirectionWoodPanelsZCoordinates.txt"
        )
        self.ZDirectionWoodPanelsXCoordinates = np.genfromtxt(
            "ZDirectionWoodPanelsXCoordinates.txt"
        )
        self.ZDirectionWoodPanelsZCoordinates = np.genfromtxt(
            "ZDirectionWoodPanelsZCoordinates.txt"
        )

        # temp1 = np.zeros(
        #     [
        #         self.XDirectionWoodPanelsXCoordinates.shape[0],
        #         self.XDirectionWoodPanelsXCoordinates.shape[1],
        #     ]
        # )
        # temp2 = np.zeros(
        #     [
        #         self.XDirectionWoodPanelsXCoordinates.shape[0],
        #         self.XDirectionWoodPanelsXCoordinates.shape[1],
        #     ]
        # )

        # temp3 = np.zeros(
        #     [
        #         self.ZDirectionWoodPanelsZCoordinates.shape[0],
        #         self.ZDirectionWoodPanelsZCoordinates.shape[1],
        #     ]
        # )
        # temp4 = np.zeros(
        #     [
        #         self.ZDirectionWoodPanelsZCoordinates.shape[0],
        #         self.ZDirectionWoodPanelsZCoordinates.shape[1],
        #     ]
        # )

        # for i in range (self.numberOfStories):

        #     for j in range(self.numberOfXDirectionWoodPanels[i]):

        #         temp1[i,j] = (i+1)*10000+1000+(j+1)*10+1
        #         temp2[i,j] = (i+1)*10000+1000+(j+1)*10+2
        #     self.XDirectionWoodPanelsBotTag = temp1
        #     self.XDirectionWoodPanelsTopTag = temp2

        # for i in range (self.numberOfStories):
        #   for j in range(self.numberOfZDirectionWoodPanels[i]):

        #     temp3[i,j] = (i+1)*10000+3000+(j+1)*10+1
        #     temp4[i,j] = (i+1)*10000+3000+(j+1)*10+2
        # self.ZDirectionWoodPanelsBotTag = temp3
        # self.ZDirectionWoodPanelsTopTag = temp4

        ##################################################################################################
        # Read in Loads
        # os.chdir(BaseDirectory + "\Loads")
        os.chdir(os.path.join(BaseDirectory, 'Loads'))
        self.floorWeights = np.genfromtxt("floorWeights.txt") * self.seismic_weight_factor # (kips)
        self.liveLoads = np.genfromtxt("liveLoads.txt") * self.seismic_weight_factor # (kips per square inch)
        self.leaningcolumnLoads = np.genfromtxt("leaningcolumnLoads.txt") * self.seismic_weight_factor # (kips)
        self.interiorWallWeight = np.genfromtxt("interiorWallWeights.txt") * self.seismic_weight_factor #(psf)

        if self.numberOfStories == 1:
            self.leaningcolumnLoads = self.leaningcolumnLoads.reshape(1, -1)
            self.floorWeights = self.floorWeights.reshape(-1,)
        ################################################################################################
        # Read in Pushover Analysis Parameters
        # os.chdir(BaseDirectory + "\AnalysisParameters\StaticAnalysis")
        os.chdir(os.path.join(BaseDirectory, *['AnalysisParameters', 'StaticAnalysis']))
        Increment = np.genfromtxt("PushoverIncrementSize.txt")
        XDriftLimit = np.genfromtxt("PushoverXDrift.txt")
        ZDriftLimit = np.genfromtxt("PushoverZDrift.txt")

        self.PushoverParameter = {
            "Increment": Increment,
            "PushoverXDrift": XDriftLimit,
            "PushoverZDrift": ZDriftLimit,
        }

        ##################################################################################################
        # Read in Dynaimic Analysis Parameters
        # os.chdir(BaseDirectory + "\AnalysisParameters\DynamicAnalysis")
        os.chdir(os.path.join(BaseDirectory, *['AnalysisParameters', 'DynamicAnalysis']))
        DriftLimit = np.genfromtxt("CollapseDriftLimit.txt")
        DemolitionLimit = np.genfromtxt("DemolitionDriftLimit.txt")

        with open("dampingModel.txt", "r") as myfile:
            dampingModel = myfile.read()  # For now, just use Rayleigh damping
            dampingRatio = np.genfromtxt("dampingRatio.txt")

        self.DynamicParameter = {
            "CollapseLimit": DriftLimit,
            "DemolitionLimit": DemolitionLimit,
            "DampingModel": dampingModel,
            "DampingRatio": dampingRatio,
        }

        ##################################################################################################
        # Read in Structural Material Property
        # os.chdir(BaseDirectory + "\StructuralProperties\Pinching4Materials")
        os.chdir(os.path.join(BaseDirectory, *['StructuralProperties', 'Pinching4Materials']))

        # For now, Pinching4 material is used
        MaterialLabel = np.genfromtxt("materialNumber.txt")
        d1 = np.genfromtxt("d1.txt")
        d2 = np.genfromtxt("d2.txt")
        d3 = np.genfromtxt("d3.txt")
        d4 = np.genfromtxt("d4.txt")

        f1 = np.genfromtxt("f1.txt")
        f2 = np.genfromtxt("f2.txt")
        f3 = np.genfromtxt("f3.txt")
        f4 = np.genfromtxt("f4.txt")

        gD1 = np.genfromtxt("gD1.txt")
        gDlim = np.genfromtxt("gDlim.txt")

        gK1 = np.genfromtxt("gK1.txt")
        gKlim = np.genfromtxt("gKlim.txt")

        rDisp = np.genfromtxt("rDisp.txt")
        rForce = np.genfromtxt("rForce.txt")
        uForce = np.genfromtxt("uForce.txt")

        self.MaterialProperty = {
            "MaterialLabel": MaterialLabel,
            "d1": d1,
            "d2": d2,
            "d3": d3,
            "d4": d4,
            "f1": f1,
            "f2": f2,
            "f3": f3,
            "f4": f4,
            "gD1": gD1,
            "gDlim": gDlim,
            "gK1": gK1,
            "gKlim": gKlim,
            "rDisp": rDisp,
            "rForce": rForce,
            "uForce": uForce,
        }

        ######  ############################################################################################
        # Read in Structural Panel Property
        # os.chdir(BaseDirectory + "/StructuralProperties/XWoodPanels")
        os.chdir(os.path.join(BaseDirectory, *['StructuralProperties', 'XWoodPanels']))
        self.XPanelLength = np.genfromtxt("length.txt")
        self.XPanelHeight = np.genfromtxt("height.txt")
        # self.XPanelMaterial = np.genfromtxt("Pinching4MaterialNumber.txt")

        # os.chdir(BaseDirectory + "/StructuralProperties/YWoodPanels")
        os.chdir(os.path.join(BaseDirectory, *['StructuralProperties', 'YWoodPanels']))
        self.ZPanelLength = np.genfromtxt("length.txt")
        self.ZPanelHeight = np.genfromtxt("height.txt")
        # self.ZPanelMaterial = np.genfromtxt("Pinching4MaterialNumber.txt")

        if self.numberOfStories == 1:
            self.XPanelLength = self.XPanelLength.reshape(1, -1)
            self.XPanelHeight = self.XPanelHeight.reshape(1, -1)
            self.ZPanelLength = self.ZPanelLength.reshape(1, -1)
            self.ZPanelHeight = self.ZPanelHeight.reshape(1, -1)
        ##################################################################################################

       # os.chdir(self.BaseDirectory+ "/%s_direction_wall" % self.direction+ "/%s" % self.wall_line_name+ "/Geometry")

        os.chdir(os.path.join(BaseDirectory, *["%s_direction_wall" % self.direction, "%s" % self.wall_line_name,"Geometry"]))

        # self.story_height = np.genfromtxt("storyHeights.txt")
        #self.tribuitaryWidth = np.genfromtxt("tribuitaryWidth.txt")[:, self.wallIndex]  # each column represents each SW line in X direction
        self.wallLength = np.genfromtxt("wallLengths.txt") #.astype(float)[:, self.wallIndex] / 12
        # self.no_of_walls = self.wallLength.size / self.wallLength.shape[0]
        if self.numberOfStories == 1:
            # print(self.wallLength, self.wallLength.dtype)
            self.no_of_walls = self.wallLength.size
        else:
            self.no_of_walls = self.wallLength.size / self.wallLength.shape[0]
        
        # print(self.no_of_walls)
        if self.no_of_walls > 1: 
            #self.wallLength = (np.genfromtxt("wallLengths.txt").astype(float)[:, self.wallIndex] / 12)[::-1]
            if self.numberOfStories == 1:
                self.wallLength = (np.genfromtxt("wallLengths.txt").astype(float)[self.wallIndex] / 12)#[::-1]
            else:
                self.wallLength = (np.genfromtxt("wallLengths.txt").astype(float)[:, self.wallIndex] / 12)[::-1]
                
            # print(self.wallLength)
        else:
            if self.numberOfStories == 1:
                # self.wallLength = (np.genfromtxt("wallLengths.txt").astype(list)[self.wallIndex] / 12)#[::-1]
                self.wallLength = np.genfromtxt("wallLengths.txt") / 12 #.astype(list)[self.wallIndex] / 12)#[::-1]
            else:
                self.wallLength = (np.genfromtxt("wallLengths.txt").astype(list)[:,None][:, self.wallIndex] / 12)[::-1]
           

            # self.wallLength = (np.genfromtxt("wallLengths.txt").astype(list)[:,None][:, self.wallIndex] / 12)[::-1]
        if self.reDesignFlag:
            self.wallLength += 0.5
        else:
            pass
        
        #self.tribuitaryLength = np.genfromtxt("tribuitaryLength.txt")[:, self.wallIndex]  # each column represents each SW line in Y direction
        # self.totalArea = np.genfromtxt("floorAreas.txt")  # wall stiffness of each wall segment
        # self.wallsPerLine = np.genfromtxt("wallsPerLine.txt")
        # self.allowableDrift = np.genfromtxt("allowableDrift.txt")
        

        # read in shear wall lineal load
        #os.chdir(self.BaseDirectory + "/%s_direction_wall" % self.direction + "/%s" % self.wall_line_name + "/Loads")
        os.chdir(os.path.join(BaseDirectory, *["%s_direction_wall" % self.direction, "%s" % self.wall_line_name,"Loads"]))
        if self.no_of_walls > 1:
            if self.numberOfStories == 1:
                self.loads = np.genfromtxt("shearWall_load.txt")[self.wallIndex] * self.seismic_weight_factor
            else:
                self.loads = np.genfromtxt("shearWall_load.txt")[:, self.wallIndex] * self.seismic_weight_factor

            # self.loads = np.genfromtxt("shearWall_load.txt")[:, self.wallIndex] * self.seismic_weight_factor
            self.loadRatio = np.genfromtxt("tribuitaryLoadRatio.txt")[self.wallIndex]

        else:
            if self.numberOfStories == 1:
                self.loads = np.genfromtxt("shearWall_load.txt") * self.seismic_weight_factor
            else:
                self.loads = np.genfromtxt("shearWall_load.txt")[:,None][:, self.wallIndex] * self.seismic_weight_factor
            self.loadRatio = np.genfromtxt("tribuitaryLoadRatio.txt")
        # self.asdDesignTag = np.loadtxt("asdDesignFlag.txt")
        

        # reading material inputs
        # os.chdir(self.BaseDirectory+ "/%s_direction_wall" % self.direction+ "/%s" % self.wall_line_name+ "/MaterialProperties")
        os.chdir(os.path.join(BaseDirectory, *["%s_direction_wall" % self.direction, "%s" % self.wall_line_name,"MaterialProperties"]))
        #   self.userInputFlag = np.loadtxt('userInputFlagShearWall.txt')
        self.initial_moisture_content = np.genfromtxt(
            "initial_moisture_content.txt"
        ).astype(float)
        self.final_moisture_content = np.genfromtxt(
            "final_moisture_content.txt"
        ).astype(float)
        self.elastic_modulus = np.genfromtxt("wood_modulusOfElasticity.txt").astype(int)
        self.nailSpacing = open("preferred_nail_spacing.txt").read()
        # self.nailSpacing = np.genfromtxt('preferred_nail_spacing.txt').astype(int)

        self.nailSize = open("preferred_nail_size.txt", "r").read()
        self.panelThickness = open("preferred_panel_thickness.txt", "r").read()
        self.takeup_deflection = np.genfromtxt("takeUpDeflection.txt")
        self.chordArea = np.genfromtxt("chordArea.txt")

        # self.userDefinedDrift = np.loadtxt("userDefinedDriftLimit.txt")
        # self.userDefinedDCRatio = np.loadtxt("userDefinedDCRatio.txt")
        # self.userDefinedDCRatioFlag_TieDown = np.loadtxt(
        #     "userDefinedDCRatioFlag_TieDown.txt"
        # )
        # self.userDefinedDCRatio_TieDown = np.loadtxt("userDefinedDCRatio_TieDown.txt")

        # self.Fx = np.genfromtxt("Fx_ToTestTheCode.txt")

        ##################################################################################################
        # Define read in Seismic Design Parameter
        # Seismic design parameter calculation follows ASCE 7-10 Chapter 12
        # In current wood frame building models, only used in defining pushover loading protocal
        # os.chdir(BaseDirectory + "/SeismicDesignParameters")
        os.chdir(os.path.join(BaseDirectory, 'SeismicDesignParameters'))
        # self.allowableDrift = np.genfromtxt("allowableDrift.txt")
        designLevel = np.genfromtxt('DesignLevel_%s.txt'%self.seismic_design_level, dtype=None, encoding = None)
        site_class = str(designLevel[0])
        # if SeismicDesignParameterFlag == 0:
        #     self.SeismicDesignParameter = None

        # else:
        #     with open("SiteClass.txt", "r") as myfile:
        #         site_class = myfile.read()
        # Ss = np.genfromtxt("Ss.txt")
        # S1 = np.genfromtxt("S1.txt")
        Ss = float(designLevel[1])
        S1 = float(designLevel[2])
        Fa = self.determine_Fa_coefficient(site_class, Ss)
        Fv = self.determine_Fv_coefficient(site_class, S1)
        SMS, SM1, SDS, SD1 = self.calculate_DBE_acceleration(Ss, S1, Fa, Fv)
        Cu = self.determine_Cu_coefficient(SD1)
        self.SDS = SDS
        # R = np.genfromtxt("R.txt")
        # Ie = np.genfromtxt("I.txt")
        # Cd = np.genfromtxt("Cd.txt")
        # TL = np.genfromtxt("TL.txt")
        R = float(designLevel[3])
        Ie = float(designLevel[4])
        Cd = float(designLevel[5])
        TL = float(designLevel[6])
        self.allowableDrift = float(designLevel[7])
        x = 0.75  # for 'All other structural systems' specified in ASCE 7-16 Table 12.8-2
        Ct = 0.02  # for 'All other structural systems' specified in ASCE 7-16 Table 12.8-2
        if self.numberOfStories == 1:
            hn = self.storyHeights / 12  # transfer unit to ft
        else:
            hn = sum(self.storyHeights) / 12  # transfer unit to ft
        Tu = (
            Cu * Ct * hn ** x
        )  # Pay attention to the differences between ASCE and FEMA, here use upper bound period specified per ASCE 7-16 as code estimated period in the following calculation
        Cs = self.calculate_Cs_coefficient(SDS, SD1, S1, Tu, TL, R, Ie)
        k = self.determine_k_coeficient(Tu)
        TotalWeight = sum(self.floorWeights)
        self.Cvx = self.calculate_Cvx(
            TotalWeight * Cs, self.floorWeights, self.floorHeights, k
        )
        seismic_force, story_shear = self.calculate_seismic_force(TotalWeight * Cs, self.floorWeights, self.floor_heights, k)

        self.SeismicDesignParameter = {
            "Ss": Ss,
            "S1": S1,
            "Fa": Fa,
            "Fv": Fv,
            "SMS": SMS,
            "SM1": SM1,
            "SDS": SDS,
            "SD1": SD1,
            "Cu": Cu,
            "R": R,
            "Cd": Cd,
            "Ie": Ie,
            "TL": TL,
            "x": x,
            "Ct": Ct,
            "Tu": Tu,
            "Cs": Cs,
            "ELF Base Shear": TotalWeight * Cs,
            "Cvx": self.Cvx,
            "story_force": seismic_force,
            "story_shear": story_shear,
            "k": k,
            'Seismic Design Level': self.seismic_design_level
        }

    def read_in_json_inputs(
        self, CaseID, BaseDirectory, SeismicDesignParameterFlag=True
    ):
        pass

    def determine_Fa_coefficient(self, site_class, Ss):

        """
        This function is used to determine Fa coefficient, which is based on ASCE 7-10 Table 11.4-1
        :param Ss: a scalar given in building class
        :param site_class: a string: 'A', 'B', 'C', 'D', or 'E' given in building information
        :return: a scalar which is Fa coefficient
        """
        if site_class == "A":
            Fa = 0.8
        elif site_class == "B":
            Fa = 1.0
        elif site_class == "C":
            if Ss <= 0.5:
                Fa = 1.2
            elif Ss <= 1.0:
                Fa = 1.2 - 0.4 * (Ss - 0.5)
            else:
                Fa = 1.0
        elif site_class == 'D':
            if Ss <= 0.25:
                Fa = 1.6
            elif Ss <= 0.75:
                Fa = 1.6 - 0.8 * (Ss - 0.25)
            elif Ss <= 1.25:
                Fa = 1.2 - 0.4 * (Ss - 0.75)
            else:
                Fa = 1.0
        elif site_class == "E":
            if Ss <= 0.25:
                Fa = 2.5
            elif Ss <= 0.5:
                Fa = 2.5 - 3.2 * (Ss - 0.25)
            elif Ss <= 0.75:
                Fa = 1.7 - 2.0 * (Ss - 0.5)
            elif Ss <= 1.0:
                Fa = 1.2 - 1.2 * (Ss - 0.75)
            else:
                Fa = 0.9
        else:
            Fa = None
            print("Site class is entered with an invalid value")

        return Fa

    def determine_Fv_coefficient(self, site_class, S1):
        """
        This function is used to determine Fv coefficient, which is based on ASCE 7-10 Table 11.4-2
        :param S1: a scalar given in building class
        :param site_class: a string 'A', 'B', 'C', 'D' or 'E' given in building class
        :return: a scalar which is Fv coefficient
        """
        if site_class == "A":
            Fv = 0.8
        elif site_class == "B":
            Fv = 1.0
        elif site_class == "C":
            if S1 <= 0.1:
                Fv = 1.7
            elif S1 <= 0.5:
                Fv = 1.7 - 1.0 * (S1 - 0.1)
            else:
                Fv = 1.3
        elif site_class == "D":
            if S1 <= 0.1:
                Fv = 2.4
            elif S1 <= 0.2:
                Fv = 2.4 - 4 * (S1 - 0.1)
            elif S1 <= 0.4:
                Fv = 2.0 - 2 * (S1 - 0.2)
            elif S1 <= 0.5:
                Fv = 1.6 - 1 * (S1 - 0.4)
            else:
                Fv = 1.5
        elif site_class == "E":
            if S1 <= 0.1:
                Fv = 3.5
            elif S1 <= 0.2:
                Fv = 3.5 - 3 * (S1 - 0.1)
            elif S1 <= 0.4:
                Fv = 3.2 - 4 * (S1 - 0.2)
            else:
                Fv = 2.4
        else:
            Fv = None
            print("Site class is entered with an invalid value")

        return Fv

    def calculate_DBE_acceleration(self, Ss, S1, Fa, Fv):
        """
        This function is used to calculate design spectrum acceleration parameters,
        which is based ASCE 7-10 Section 11.4
        Note: All notations for these variables can be found in ASCE 7-10.
        :param Ss: a scalar given in building information (problem statement)
        :param S1: a scalar given in building information (problem statement)
        :param Fa: a scalar computed from determine_Fa_coefficient
        :param Fv: a scalar computed from determine_Fv_coefficient
        :return: SMS, SM1, SDS, SD1: four scalars which are required for lateral force calculation
        """
        SMS = Fa * Ss
        SM1 = Fv * S1
        SDS = 2 / 3 * SMS
        SD1 = 2 / 3 * SM1
        return SMS, SM1, SDS, SD1

    def determine_Cu_coefficient(self, SD1):
        """
        This function is used to determine Cu coefficient, which is based on ASCE 7-10 Table 12.8-1
        Note: All notations for these variables can be found in ASCE 7-10.
        :param SD1: a scalar calculated from funtion determine_DBE_acceleration
        :return: Cu: a scalar
        """
        if SD1 <= 0.1:
            Cu = 1.7
        elif SD1 <= 0.15:
            Cu = 1.7 - 2 * (SD1 - 0.1)
        elif SD1 <= 0.2:
            Cu = 1.6 - 2 * (SD1 - 0.15)
        elif SD1 <= 0.3:
            Cu = 1.5 - 1 * (SD1 - 0.2)
        elif SD1 <= 0.4:
            Cu = 1.4
        else:
            Cu = 1.4

        return Cu

    def calculate_Cs_coefficient(self, SDS, SD1, S1, T, TL, R, Ie):
        """
        This function is used to calculate the seismic response coefficient based on ASCE 7-10 Section 12.8.1
        Unit: kips, g (gravity constant), second
        Note: All notations for these variables can be found in ASCE 7-10.
        :param SDS: a scalar determined using Equation 11.4-3; output from "calculate_DBE_acceleration" function
        :param SD1: a scalar determined using Equation 11.4-4; output from "calculate_DBE_acceleration" function
        :param S1: a scalar given in building information (problem statement)
        :param T: building period; a scalar determined using Equation 12.8-1 and Cu;
                    implemented in "BuildingInformation" object attribute.
        :param TL: long-period transition
        :param R: a scalar given in building information
        :param Ie: a scalar given in building information
        :return: Cs: seismic response coefficient; determined using Equations 12.8-2 to 12.8-6
        """
        # Equation 12.8-2
        Cs_initial = SDS / (R / Ie)

        # Equation 12.8-3 or 12.8-4, Cs coefficient should not exceed the following value
        if T <= TL:
            Cs_upper = SD1 / (T * (R / Ie))
        else:
            Cs_upper = SD1 * TL / (T ** 2 * (R / Ie))

        # Equation 12.8-2 results shall be smaller than upper bound of Cs
        if Cs_initial <= Cs_upper:
            Cs = Cs_initial
        else:
            Cs = Cs_upper

        # Equation 12.8-5, Cs shall not be less than the following value
        Cs_lower_1 = np.max([0.044 * SDS * Ie, 0.01])

        # Compare the Cs value with lower bound
        if Cs >= Cs_lower_1:
            pass
        else:
            Cs = Cs_lower_1

        # Equation 12.8-6. if S1 is equal to or greater than 0.6g, Cs shall not be less than the following value
        if S1 >= 0.6:
            Cs_lower_2 = 0.5 * S1 / (R / Ie)
            if Cs >= Cs_lower_2:
                pass
            else:
                Cs = Cs_lower_2
        else:
            pass

        return Cs

    def determine_k_coeficient(self, period):
        """
        This function is used to determine the coefficient k based on ASCE 7-10 Section 12.8.3
        :param period: building period;
        :return: k: a scalar will be used in Equation 12.8-12 in ASCE 7-10
        """
        if period <= 0.5:
            k = 1
        elif period >= 2.5:
            k = 2
        else:
            k = 1 + 0.5 * (period - 0.5)

        return k

    def calculate_Cvx(self, base_shear, floor_weight, floor_height, k):
        """
        This function is used to calculate the seismic story force for each floor level
        Unit: kip, foot
        :param base_shear: a scalar, total base shear for the building
        :param floor_weight: a vector with a length of number_of_story
        :param floor_height: a vector with a length of (number_of_story+1)
        :param k: a scalar given by "determine_k_coefficient"
        :return: Fx: a vector describes the lateral force for each floor level
        """
        # Calculate the product of floor weight and floor height
        # Note that floor height includes ground floor, which will not be used in the actual calculation.
        # Ground floor is stored here for completeness.
        weight_floor_height = np.multiply(floor_weight, floor_height[1:] ** k)
        # Equation 12.8-12 in ASCE 7-10
        Cvx = weight_floor_height / np.sum(weight_floor_height)
        # calculate story shear for each story: from top to bottom
        seismic_force = Cvx * base_shear
        story_shear = np.zeros([len(floor_weight), 1])
        for story in range(len(floor_weight) - 1, -1, -1):
            story_shear[story] = np.sum(seismic_force[story:])
        return Cvx

    def calculate_seismic_force(self, base_shear, floor_weight, floor_height, k):
        """
        This function is used to calculate the seismic story force for each floor level
        Unit: kip, foot
        :param base_shear: a scalar, total base shear for the building
        :param floor_weight: a vector with a length of number_of_story
        :param floor_height: a vector with a length of (number_of_story+1)
        :param k: a scalar given by "determine_k_coefficient"
        :return: Fx: a vector describes the lateral force for each floor level
        """
        # Calculate the product of floor weight and floor height
        # Note that floor height includes ground floor, which will not be used in the actual calculation.
        # Ground floor is stored here for completeness.
        # weight_floor_height = np.multiply(floor_weight, (floor_height[::-1] / 12) ** k)
        # Equation 12.8-12 in ASCE 7-10
        # Cvx = weight_floor_height / np.sum(weight_floor_height)
        # calculate the seismic force. even though it says Cvx*base_shear, base_shear is actually initialized as weight above
        seismic_force = self.Cvx * base_shear
        # calculate story shear for each story: from top to bottom
        story_shear = np.zeros([len(floor_weight), 1])
        for story in range(len(floor_weight) - 1, -1, -1):
            story_shear[story] = np.sum(seismic_force[story:])

        if self.designScheme == 'ASD': 
            seismic_force = seismic_force * 0.7
            story_shear = story_shear * 0.7
        else: 
            pass
        return seismic_force, story_shear

    def SW_shear_demand(self):
        """
        This method is used to calculate unit shear demand on shear wall in
        terms of klf
        :attribute Fx: Seismic Forces at each floor level. Unit: Kips 
        :attribute loadRatio: tribuitary load ratio taken by the wall 
        :attribute wallsPerLine: number of walls per shear wall line 
        
        :return: lineal shear demand on the shear wall. Unit: klf
        """

        if not self.envelopeAnalysis: 
            self.story_force_per_wall = (
                self.SeismicDesignParameter["story_force"]
                * self.loadRatio
                #/ self.wallsPerLine
            )
        else:
            # os.chdir(self.BaseDirectory + "/%s_direction_wall" % self.direction + "/%s" % self.wall_line_name)
            os.chdir(os.path.join(self.BaseDirectory, *["%s_direction_wall" % self.direction, "%s" % self.wall_line_name]))

            self.envelopeShearWallDemand = np.genfromtxt("envelopeShearWallDemand.txt")[:,self.wallIndex]
            self.story_force_per_wall = np.ediff1d(self.envelopeShearWallDemand, to_begin=self.envelopeShearWallDemand[0]) * self.wallLength


        self.target_unit_shear = np.cumsum(self.story_force_per_wall / self.wallLength)
        # print(self.target_unit_shear)
        return self.target_unit_shear

    def Anchorage_demand(self):
        """
        This method is used to calculate anchorage tension demand. Unit: kips. 
        
        :attribute story_force_per_wall: Seismic story force per wall. Unit: Kips
        :attribute story_height: floor height. unit: ft 
        :attribute wallLength: Length of the wall. unit: ft 
        :attribute target_unit_shear: shear demand per unit length on the wall. unit: klf
        
        :return: tension demand at the end of the shear wall. unit: kips
        """

        self.overturning_moment = np.cumsum(np.cumsum(self.story_force_per_wall * self.storyHeights / 12))
        #assume the height of the wall is 9 ft
        sw_self_wt = 9 * self.wallLength * self.interiorWallWeight / 1000 #unit: kips 
        #assume tribuitary dead load on sw to be 15 psf Ref: 3-story design example (FEMA P-750) page 11-14
        # assume trib width to be 8.5 ft
        wall_trib_dead_load = 8.5 * self.wallLength * 15 /1000 #unit:kips
        #assume there are at least two wall along the grid perpendicular to the one being designed
        trib_perp_dead_load = 9 * 8.5 * self.interiorWallWeight * 2 / 1000

        if self.designScheme != 'ASD':
            self.counter_moment = 0.72 * self.loads * self.wallLength / 2
            # if self.numberOfStories == 1:
            #     self.counter_moment = np.array([0.72 * self.loads * self.wallLength / 2])
            # else: 
            #     self.counter_moment = 0.72 * self.loads * self.wallLength / 2
            self.tension_demand = np.cumsum(
                self.target_unit_shear * (self.storyHeights - 2) / 12
            )
        else:
            self.counter_moment = self.loads * self.wallLength / 2
            # if self.numberOfStories == 1:
            #     self.counter_moment = np.array([self.loads * self.wallLength / 2])
            # else: 
            #     self.counter_moment = self.loads * self.wallLength / 2
            self.tension_demand = np.cumsum(self.overturning_moment / (1.4 * (self.storyHeights - 1) / 12)) + np.cumsum(self.target_unit_shear * 1 * 2)

        return self.tension_demand

