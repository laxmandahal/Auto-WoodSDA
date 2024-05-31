# -*- coding: utf-8 -*-
"""
This file is used to design shear wall for strength and compute story drift.
This file also designs diaphragms and anchorage (tie-downs)

Developed by: Laxman Dahal, UCLA

Created on: Aug 2020, 

Last Modified: Oct 2020

"""

__author__ = "Laxman Dahal"


import numpy as np
import pandas as pd
import os
import re
import sys

from global_variables import shearwall_database
from global_variables import tiedown_database
from ComputeDesignForce import ComputeSeismicForce
# from Codes.designModule.ComputeDesignForce import ComputeSeismicForce

class DesignShearWall:
    ''' 
    This is the main class for shear-wall design (at a given floor) based on the demand. It instantiates "ComputeDesignForce" class 
    to get shear demand.Based on the shear demand, shear wall is selected from the database. Tie-downs are also designed. 
    If design iteration is required, this class is instantiated again. 

    :param caseID: the name of the building, type: str
    :param BaseDirectory: the master directory that contains model inputs, base tcl files and other files, type: str
    :param direction: direction used to run Pushover Analysis (X, Y), type: str 
    :param wallIndex: Index of the wall line given there are multiple shear wall lines in a given direction (X or Y), type: int
    :param floorIndex: index of the wall to be designed. [0, 1, 2,,...] --> [floor1, floor2, ...], type: int
    :param counter: counter to keep track of shearwall assembly in shearwall_database, type: int 
    :param wall_line_name: Name of the wall line to be designed, type: str
    :param Ss and S1: Design parameters, type: float
    :param userDefinedDetailingTag: flag to indicate of user-defined shear wall detailing is desired, type:bool 
    :param reDesignFlag: Flag to redesign, if True wall length increased by 0.5ft type: bool
    :param userDefinedDriftTag: Flag to indicate if user-defined drift limit is desired, type: bool 
    :param userDefinedDCTag: Flag to indicate of Demand(D)/Capacity(C) ratio is desired, type: bool 
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
        Ss, 
        S1,
        weight_factor = 1.0,
        seismic_design_level = 'Extreme',
        designScheme = 'LRFD',
        userDefinedDetailingTag = False,
        reDesignFlag = False,
        userDefinedDriftTag = False,
        userDefinedDCTag = False,
        iterateFlag = False,
        envelopeAnalysis = False
    ):
        self.caseID = caseID
        self.BaseDirectory = BaseDirectory
        self.direction = direction
        self.wall_line_name = wall_line_name
        self.userDefinedDetailingTag = userDefinedDetailingTag
        self.reDesignFlag = reDesignFlag
        self.userDefinedDriftTag = userDefinedDriftTag
        self.userDefinedDCTag = userDefinedDCTag
        self.wallIndex = wallIndex
        self.envelopeAnalysis = envelopeAnalysis
        self.designScheme = designScheme
        self.seismic_design_level = seismic_design_level
        self.seismic_weight_factor = weight_factor

        self.iterateFlag = iterateFlag
        self.counter = counter
        self.floorIndex = floorIndex

        self.Ss = Ss
        self.S1 = S1
        #instantiate ComputeSeismicForce class to be able to extract shear wall and tie-down demands
        ModelClass = ComputeSeismicForce(
            self.caseID,
            self.BaseDirectory,
            self.direction,
            self.wall_line_name,
            self.wallIndex,
            self.Ss,
            self.S1,
            self.seismic_weight_factor,
            self.seismic_design_level,
            self.designScheme,
            self.reDesignFlag,
            self.envelopeAnalysis,
        )
        # self.loads = ModelClass.loads
        # self.loadRatio = ModelClass.loadRatio
        self.Fx = ModelClass.SeismicDesignParameter["story_force"]
        self.Cd = ModelClass.SeismicDesignParameter["Cd"]
        self.Ie = ModelClass.SeismicDesignParameter["Ie"]
        self.numFloors = ModelClass.numberOfStories
        # print(self.numFloors, ModelClass.floorArea)
        self.no_of_walls = ModelClass.no_of_walls
        # print(self.no_of_walls)

        if self.designScheme == 'ASD':
            self.baseShear = ModelClass.SeismicDesignParameter["ELF Base Shear"] * 0.7
        else:
            self.baseShear = ModelClass.SeismicDesignParameter["ELF Base Shear"]
        # print(ModelClass.target_unit_shear)
        self.target_unit_shear = ModelClass.target_unit_shear[self.floorIndex]

        self.tension_demand = ModelClass.tension_demand[self.floorIndex]
        self.story_force_per_wall = ModelClass.story_force_per_wall[self.floorIndex]
        self.overturning_moment = ModelClass.overturning_moment[self.floorIndex]
        
        # self.asdDesignTag = ModelClass.asdDesignTag
        if ModelClass.numberOfStories == 1:
            self.wallLength = ModelClass.wallLength
            self.story_height = ModelClass.storyHeights / 12
            self.counter_moment = ModelClass.counter_moment
        else:
            self.wallLength = ModelClass.wallLength[self.floorIndex]
            self.story_height = ModelClass.storyHeights[self.floorIndex] / 12
            self.counter_moment = ModelClass.counter_moment[self.floorIndex]

        self.totalArea = ModelClass.floorArea
        self.allowableDrift = ModelClass.allowableDrift


        # if self.asdDesignTag:
        #     self.loadType = "ASD"
        # else:
        #     self.loadType = "LRFD"


        self.sw_dict = {}
        self.td_dict = {}

        self.read_sw_user_inputs()
        self.find_shearwall_candidate(shearwall_database)
        self.anchorage_design(tiedown_database, E=29000)
        self.calculate_assembly_deflection()
        self.calculate_SW_deflection()
        self.calculate_story_drift()
        self.calculate_drift_limit()
        # self.increaseLength()
        self.check_Drift()

        self.drift_check = None
        self.dfCheck = None

    def read_sw_user_inputs(self):
        """
        This method is used to read all the needed shear wall user inputs.
        The input files should be .txt files in respective directories
        
        :return: instantiates required class variables and attributes 
        """

        # read in the geometric properties
        os.chdir(
            self.BaseDirectory
            + "/%s_direction_wall" % self.direction
            + "/%s" % self.wall_line_name
            + "/Geometry"
        )
        # self.wallLength = np.genfromtxt('wallLengths.txt')

        # self.story_height = np.genfromtxt("storyHeights.txt")[self.floorIndex]
        # each column represents each SW line in X direction
        # tribWidth = np.genfromtxt("tribuitaryWidth.txt")
        # no_of_walls = tribWidth.size / tribWidth.shape[0] 
        if self.no_of_walls > 1:
            if self.numFloors == 1:
                self.tribuitaryWidth = np.genfromtxt("tribuitaryWidth.txt")[self.wallIndex]
            # each column represents each SW line in Y direction
                self.tribuitaryLength = np.genfromtxt("tribuitaryLength.txt")[self.wallIndex]
            else:
                self.tribuitaryWidth = np.genfromtxt("tribuitaryWidth.txt")[:, self.wallIndex]
                # each column represents each SW line in Y direction
                self.tribuitaryLength = np.genfromtxt("tribuitaryLength.txt")[:, self.wallIndex]
        else:
            self.tribuitaryWidth = np.genfromtxt("tribuitaryWidth.txt")
            # each column represents each SW line in Y direction
            self.tribuitaryLength = np.genfromtxt("tribuitaryLength.txt")
        # wall stiffness of each wall segment
        # self.totalArea = np.genfromtxt("floorAreas.txt") 
        # number of walls per shear wall line. Used to distribute load 
        # self.wallsPerLine = np.genfromtxt("wallsPerLine.txt")
        #allowable drift limit
        # self.allowableDrift = np.genfromtxt("allowableDrift.txt")

        # read in shear wall lineal load
        # os.chdir(
        #     self.BaseDirectory
        #     + "/%s_direction_wall" % self.direction
        #     + "/%s" % self.wall_line_name
        #     + "/Loads"
        # )
        # self.loads = np.genfromtxt("shearWall_load.txt")
        # self.loadRatio = np.genfromtxt("tribuitaryLoadRatio.txt")[self.wallIndex]

        # reading material inputs
        os.chdir(
            self.BaseDirectory
            + "/%s_direction_wall" % self.direction
            + "/%s" % self.wall_line_name
            + "/MaterialProperties"
        )

        #initial moisture content of the wood (stud/frame). Used to compute shrinkage due to differential Unit: percent (%) 
        self.initial_moisture_content = np.genfromtxt("initial_moisture_content.txt").astype(float)
        #final moisture content of the wood. Unit: percent
        self.final_moisture_content = np.genfromtxt("final_moisture_content.txt").astype(float)
        #elastic modulus of the wood (stud/frame)
        self.elastic_modulus = np.genfromtxt("wood_modulusOfElasticity.txt").astype(int)

        ## NOTE: Nail size and spacing, and panel thickness are selected by program (default). Only specify these quantities if those
        #specific specification is desired

        #desired nail spacing
        # self.nailSpacing = open("preferred_nail_spacing.txt").read()[self.wallIndex]
        nailspacing = np.genfromtxt('preferred_nail_spacing.txt')
        #desired nail size
        nailsize = open("preferred_nail_size.txt", "r").read()
        #desired panel thickness
        panelthickness = open("preferred_panel_thickness.txt", "r").read()
        takeup_deflection = np.genfromtxt("takeUpDeflection.txt")
        chord_area = np.genfromtxt("chordArea.txt")

        if self.no_of_walls > 1:
            if self.numFloors == 1:
                self.nailSpacing = nailspacing[self.wallIndex].astype(int)
                self.nailSize = nailsize[self.wallIndex]
                # self.nailSize = np.array(nailsize.split()).reshape(int(self.numFloors), int(self.no_of_walls))#[self.wallIndex]
                # self.panelThickness = np.array(panelthickness.split()).reshape(int(self.numFloors), int(self.no_of_walls))[self.wallIndex]
                self.panelThickness = panelthickness[self.wallIndex]
                self.takeup_deflection = takeup_deflection
                self.chordArea = chord_area
            else:
                self.nailSpacing = nailspacing[:, self.wallIndex][self.floorIndex].astype(int)
                self.nailSize = np.array(nailsize.split()).reshape(int(self.numFloors), int(self.no_of_walls))[:, self.wallIndex][self.floorIndex]
                self.panelThickness = np.array(panelthickness.split()).reshape(int(self.numFloors), int(self.no_of_walls))[:, self.wallIndex][self.floorIndex]
                self.takeup_deflection = takeup_deflection[self.floorIndex]
                self.chordArea = chord_area[self.floorIndex]
        else:
            if self.numFloors == 1:
                self.nailSpacing = nailspacing.astype(int)
                self.nailSize = np.array(nailsize.split()).reshape(int(self.numFloors), int(self.no_of_walls))
                self.panelThickness = np.array(panelthickness.split()).reshape(int(self.numFloors), int(self.no_of_walls))
                self.takeup_deflection = takeup_deflection
                self.chordArea = chord_area
            else:
                self.nailSpacing = nailspacing[self.floorIndex].astype(int)
                self.nailSize = np.array(nailsize.split()).reshape(int(self.numFloors), int(self.no_of_walls))[self.floorIndex]
                self.panelThickness = np.array(panelthickness.split()).reshape(int(self.numFloors), int(self.no_of_walls))[self.floorIndex]
                self.takeup_deflection = takeup_deflection[self.floorIndex]
                self.chordArea = chord_area[self.floorIndex]
        
        
        
        ##takeup_deflection (inches) often provided by manufacturers
        # self.takeup_deflection = np.genfromtxt("takeUpDeflection.txt")[self.floorIndex]
        # ##chord area (in^2) often provided by manufacturer
        # self.chordArea = np.genfromtxt("chordArea.txt").astype(list)[self.floorIndex]
        #M aterial type of the sheathing. Options: Plywood or OSB
        self.sheathingMaterial = open("sheathingMaterialType.txt", "r").read()
        # Grade of the sheathing. Options: Structural I or WSP. Note Str I is higher grade sheathing.
        self.sheathingType = open("sheathingType.txt", "r").read()

        # reading user imposed design constraints
        os.chdir(
            self.BaseDirectory
            + "/%s_direction_wall" % self.direction
            + "/%s" % self.wall_line_name
            + "/DesignConstraints"
        )
        #user-defined drift limit criteria. Often specified if stricter requirement than ASCE is deisred (less than 2%)
        self.userDefinedDrift = np.loadtxt("userDefinedDriftLimit.txt")
        #user-defined D/C ratio. Often desired to be less than 90% 
        self.userDefinedDCRatio = np.loadtxt("userDefinedDCRatio.txt")
        # Flag to indicate if D/C ratio is desired fot Tie-downs 
        self.userDefinedDCRatioFlag_TieDown = np.loadtxt("userDefinedDCRatioFlag_TieDown.txt")
        #Desired D/C ratio for tie-down tesign
        self.userDefinedDCRatio_TieDown = np.loadtxt("userDefinedDCRatio_TieDown.txt")

        self.tieDownSystemTag = np.loadtxt("tieDownSystemFlag.txt")
        # self.Fx = np.genfromtxt('Fx_ToTestTheCode.txt')
        

        # reading properties for Rigid Diaphragm Assumption
        os.chdir(
            self.BaseDirectory
            + "/%s_direction_wall" % self.direction
            + "/%s" % self.wall_line_name
            + "/RigidDiaphragmAssumption"
        )
        self.accidentalTorsion = np.genfromtxt('AccidentalTorsion(ex).txt') / 12 #unit: inches converted to ft 
        self.torsionalIrregularity = np.genfromtxt('TorsionalIrregularity(Ax).txt')
        self.redundancyFactor = np.genfromtxt('RedundancyFactor.txt')
        if self.no_of_walls > 1: 
            self.momentArm = np.genfromtxt('MomentArm.txt')[self.wallIndex] / 12
        else:
            self.momentArm = np.genfromtxt('MomentArm.txt') / 12
        # self.pinching4IndexShearWall = np.genfromtxt("pinching4Index_ShearWall.txt")
        # self.pinching4IndexNonStructural = np.genfromtxt("pinching4Index_nsc.txt")

        # os.chdir(self.BaseDirectory + "/StructuralProperties" + "/%sWoodPanels")
        # self.pinching4MaterialNumber = np.genfromtxt("Pinching4MaterialNumber.txt")


    def find_shearwall_candidate(self, shearwall_database):
        """
        This method is used to find the most economical shear wall that satisfies the demand
        computed in method SW_shear_demand().
        :param shearwall_database: a dataframe read from shearwall_database.csv in Library folder
        :attribute target_unit_shear: unit shear deman on the shear wall. Units: klf
        :return: a pandas dataframe of shear wall design for every floor
        """
        # instantiate a dummy list for the purpose of creating a dataframe later
        d = []
        # length of the self.target_unit_shear gives the number of stories
        # loop through the number of stories to design shear wall at each story individually
        # check if user has specified D/C ratio.
        # if the D/C ratio is specified, multiply LRFD capacity with D/C ratio such that the code selects...
        # ...shear wall with higher strength
        if len(self.sheathingMaterial) >=2:
            shearwall_database = shearwall_database.loc[(shearwall_database["Material"] == "%s" % self.sheathingMaterial)]

        if len(self.sheathingType) >=2:
            shearwall_database = shearwall_database.loc[(shearwall_database["Sheathing Type"] == "%s" % self.sheathingType)]

        if self.userDefinedDCTag:
            df = shearwall_database[
                shearwall_database["%s(klf)" % self.designScheme] * self.userDefinedDCRatio
                >= self.target_unit_shear
            ]
            # if D/C ratio is not specified, filter the database with capacity greater than the demand
        else:
            df = shearwall_database[shearwall_database["%s(klf)" % self.designScheme] >= self.target_unit_shear]
            # make copy of the filtered database for later use
        df1 = shearwall_database[shearwall_database["%s(klf)" % self.designScheme] >= self.target_unit_shear]
        # check if user has specified shear wall assembly detailing input
        if self.userDefinedDetailingTag:
            # if all three detailing specifications (nail spacing, nail size, and panel thickness) are user input
            if (
                (len(self.panelThickness) >= 2)
                & (len(self.nailSize) >= 2)
                & (len(str(self.nailSpacing)) >= 1)
            ):
                # filter database that meets user input requirements
                df = df.loc[
                    (df["panel thickness"] == "%s" % self.panelThickness)
                    & (df["nail spacing"] == self.nailSpacing)
                    & (df["nail size"] == "%s" % self.nailSize)
                ]
                # if only one or two (out of 3) detailing are user inputs filter the database to meet criteria
            else:
                # if panel thickness and nail size are user inputs
                if (
                    (len(self.panelThickness) >= 2)
                    & (len(self.nailSize) >= 2)
                    & (len(self.nailSpacing) < 1)
                ):
                    df = df.loc[
                        (df["panel thickness"] == "%s" % self.panelThickness)
                        & (df["nail size"] == "%s" % self.nailSize)
                    ]
                    # if nail spacing and nail size are user inputs
                if (
                    (len(self.panelThickness) < 2)
                    & (len(self.nailSize) >= 2)
                    & (len(self.nailSpacing) >= 1)
                ):
                    df = df.loc[
                        (df["nail spacing"] == int(self.nailSpacing))
                        & (df["nail size"] == "%s" % self.nailSize)
                    ]
                    # if panel thickness and nail spacing are user inputs
                if (
                    (len(self.panelThickness) >= 2)
                    & (len(self.nailSize) < 2)
                    & (len(self.nailSpacing) >= 1)
                ):
                    df = df.loc[
                        (df["nail spacing"] == int(self.nailSpacing))
                        & (df["panel thickness"] == "%s" % self.panelThickness)
                    ]
                    # if only panel thickness is the user input
                if (
                    (len(self.panelThickness) >= 2)
                    & (len(self.nailSize) < 2)
                    & (len(self.nailSpacing) < 1)
                ):
                    df = df.loc[df["panel thickness"] == "%s" % self.panelThickness]
                    # if only nail size is the user input
                if (
                    (len(self.panelThickness) < 2)
                    & (len(self.nailSize) >= 2)
                    & (len(self.nailSpacing) < 1)
                ):
                    df = df.loc[df["nail size"] == "%s" % self.nailSize]
                    # if only nai spacing is the user input
                if (
                    (len(self.panelThickness) < 2)
                    & (len(self.nailSize) < 2)
                    & (len(self.nailSpacing) >= 1)
                ):
                    df = df.loc[df["nail spacing"] == int(self.nailSpacing)]
        else:
            pass

        if (not self.userDefinedDetailingTag) & (not self.userDefinedDCTag):

            # self.counter = 0
            df = shearwall_database[shearwall_database["%s(klf)" % self.designScheme] >= self.target_unit_shear]

            if self.iterateFlag:
                # try:
                df = shearwall_database[shearwall_database["%s(klf)" % self.designScheme]>= self.target_unit_shear]
                df = df.iloc[self.counter]
                df = pd.DataFrame([df])

        level = self.numFloors - self.floorIndex
        # print(df)
        # print('Shear demand at level {} of {} wall number {} is {}'.format(self.floorIndex, self.wall_line_name, self.wallIndex, self.target_unit_shear))
        # get the shear wall detailing at the first index
        try:
            self.sw_dict = {
                "Shear Wall Assembly": df["Assembly"].iloc[0],
                "Ga(k/in)": df["Ga(OSB)(kips/in)"].iloc[0],
                "level": level,
                "%s(klf)" % self.designScheme: df["%s(klf)" % self.designScheme].iloc[0],
                "Drift(in)": "NaN",
                "D/C Ratio": self.target_unit_shear
                / df["%s(klf)" % self.designScheme].iloc[0],
                "OpenSees Tag": df["OpenSeesTag"].iloc[0],
            }
            # if no shear wall exists (might happen if detailing specification is desired), user the dataframe
            # that does not filter based on detailing specificatin

        except IndexError:
            if (
                not self.target_unit_shear
                >= shearwall_database["%s(klf)" % self.designScheme].iloc[-1]
            ):

                print(
                    "No shearwall found. Please try different detailing/DCR or use default values @ level %d"
                    % level
                )
                self.sw_dict = {
                    "Shear Wall Assembly": df1["Assembly"].iloc[0],
                    "Ga(k/in)": df1["Ga(OSB)(kips/in)"].iloc[0],
                    "level": level,
                    "%s(klf)" % self.designScheme: df1["%s(klf)" % self.designScheme].iloc[0],
                    "Drift(in)": "NaN",
                    "D/C Ratio": self.target_unit_shear
                    / df1["%s(klf)" % self.designScheme].iloc[0],
                    "OpenSees Tag": df1["OpenSeesTag"].iloc[0],
                }
            else:
                print(
                    "Cannot find the shear wall assembly for the demand of {} kips".format(
                        self.target_unit_shear
                    )
                )
                sys.exit(1)

        d.append(self.sw_dict)
        # create a database
        self.sw_design = pd.DataFrame(d)
        # return self.sw_design
        return self.sw_dict


    def anchorage_design(self, tiedown_database, E=29000):
        """
        This method is user to design anchorage
        :param tiedown_database: database compiled based on AISC Manual Table 7-17
        :param E: Youngs Modulus of steel. Set to be 29000 as default
        :returns: dataframe of tie down design for each floor 
        """
        # calculate overturning moment due to the seismic force
        # overturning_moment = np.cumsum(np.cumsum(self.story_force_per_wall * self.story_height))
        # #calculate counter-balancing moment due to the gravity load
        # counter_moment = 0.72 * self.loads * self.wallLength /2
        # instantiate a dummy list for the purpose of creating a dataframe later
        d = []
        # loop over the number of stories as tie down is designed for each floor
        # for i in range (0, len(self.story_height)):
        #     #check if overturning moment exceeds the counter moment
        df = tiedown_database[tiedown_database["Capacity(kips)"]* self.userDefinedDCRatio_TieDown >= self.tension_demand]
        
        if self.tieDownSystemTag:
            # print(self.overturning_moment, self.counter_moment)
            if self.overturning_moment > self.counter_moment:
                # if tie down is needed, calculate the tension demand
                # if D/C ratio is desired for tie-down, multiply the capacity by the ratio
                if self.userDefinedDCRatioFlag_TieDown:
                    # filter the database such that only the ones that meet demand is left
                    df = tiedown_database[
                        tiedown_database["Capacity(kips)"]
                        * self.userDefinedDCRatio_TieDown
                        >= self.tension_demand
                    ]
                else:
                    # if no D/C ratio is specified, database is not multiplied by the anything
                    df = tiedown_database[
                        tiedown_database["Capacity(kips)"] >= self.tension_demand
                    ]
            else:
                ##if no tiedown is required, do nothing
                df = tiedown_database[tiedown_database["Capacity(kips)"] >= self.tension_demand] 

                  # make this a default tiedown design
                # pass
        else:
            pass
            # df = tiedown_database.iloc[-1]
            # df = pd.DataFrame(df)
            # print(df)
            # keep track of level for each loop
        level = self.numFloors - self.floorIndex
        # calculate rod elongation due to the tension demand

        if self.tieDownSystemTag:
            deflection = (
                self.tension_demand
                * self.story_height
                * 12
                / (E * df["Ae(in^2)"].iloc[0])
            )
            self.td_dict = {
                "Tie-down Assembly": df["Assembly"].iloc[0],
                "Rod Elongation(in)": deflection,
                "Capacity(kips)": df["Capacity(kips)"].iloc[0],
                "level": level,
                "D/C Ratio": self.tension_demand / df["Capacity(kips)"].iloc[0],
            }
        else:
            deflection = 0
            self.td_dict = {
                "Tie-down Assembly": "Tie-down not desired/ required",
                "Rod Elongation(in)": deflection,
                "Capacity(kips)": "N/A",
                "level": level,
                "D/C Ratio": "N/A",
            }

        # self.td_dict = {'Tie-down Assembly':df['Assembly'].iloc[0], 'Rod Elongation(in)':deflection,
        #                 'Capacity(kips)': df['Capacity(kips)'].iloc[0], 'level':level,
        #                 'D/C Ratio': self.tension_demand / df['Capacity(kips)'].iloc[0]}
        d.append(self.td_dict)
        # create a dataframe for tiedown design
        self.tiedown_design = pd.DataFrame(d)
        # return self.tiedown_designs
        return self.td_dict

    def calculate_assembly_deflection(self):
        """
        This method calculates the assembly deflection of the shear wall
        :return: total assembly delection of the shearwall, often referred to as "delta a""
        """
        # calulate tension demand in terms of ASD
        # tension_demand = np.cumsum(self.target_unit_shear * (self.story_height -1))
        # convert ASD demand to LRFD
        compressive_demand = self.tension_demand
        # if self.designScheme == 'ASD':
        #     compressive_demand = self.tension_demand
        # else:
        #     compressive_demand = self.tension_demand / 0.7
        # calculate compressive force
        compressive_force = compressive_demand / self.chordArea
        # calculate deflection due to sill plate crushing
        # assumptions:
        crushing = 1.75 * (0.04 - 0.02 * (1 - compressive_force / 0.625) / 0.27)

        # calculate deflection due to shrinkage of the wood due to moisture content
        # shrinkage = np.full(len(self.story_height), 0.0025 * 1.5 * \
        #                     (self.initial_moisture_content - self.final_moisture_content)) #uses 2X sill

        shrinkage = (
            0.0025 * 1.5 * (self.initial_moisture_content - self.final_moisture_content)
        )

        # get deflection due to rod elongation from previous method
        rod_elongation = self.tiedown_design["Rod Elongation(in)"].values
        # combine all the deflections
        #only including half of rod elongation because, take up deflection already in part includes rod elongation as well
        self.total_assembly_deflection = (
            crushing + shrinkage + self.takeup_deflection + rod_elongation / 2
        )
        # print(self.total_assembly_deflection)
        return self.total_assembly_deflection

    def calculate_SW_deflection(self):
        """
        This method calculates the total shear wall deflection. 
        It considers deflection due to chord bending, shear, and rotation
        It uses 3-term deflection equation per SDPWS 2015
        
        :return: total shear wall deflection 
        """
        # get the per story shear demand (not the seismic force), for each story
        # shear_demand = np.concatenate((np.array(self.target_unit_shear[0]).reshape(1,), \
        #                                 np.diff(self.target_unit_shear)))*1000
        shear_demand = self.story_force_per_wall * 1000 / self.wallLength
        # create a length array if self.wallLength attribute is an integer instead of an array
        # length = np.full(shape = len(self.story_height), fill_value = self.wallLength)
        # calculate EA for simplicity
        EA = self.chordArea * self.elastic_modulus
        # Get apparent shear stiffness from the designed shear walls for each floor
        Ga = self.sw_design["Ga(k/in)"].values
        # calculate deflection due to chord bending
        del_bending = (
            8
            * shear_demand
            * np.power(self.story_height, 3)
            / ((EA/1000) * self.wallLength)
            / 1000
        )
        # calculate due to apparent shear failure ( nail slipping and shear deformation)
        del_shear = shear_demand * self.story_height / (1000 * Ga)
        # calculate deflection due to rotation
        del_rotation = (
            self.total_assembly_deflection * self.story_height / (self.wallLength - 1)
        )
        # create an instance of the deflecton
        # print([del_bending, del_rotation, del_shear])
        self.sw_deflection = np.abs(del_bending + del_shear + del_rotation)
        # print(self.sw_deflection)
        return self.sw_deflection

    def calculate_story_drift(self):
        """
        This method calculates story drift for the designed shear wall and tie down
        :return: story drift for each story. Units: inches
        """
        # calculate story drift per ASCE 07-16
        self.story_drift = self.sw_deflection * self.Cd / self.Ie
        # print(self.story_drift)
        return self.story_drift

    def calculate_drift_limit(self):
        """
        This method returns the drift limit to be considered to design the building for 
        :return: drift limit imposed by either code or the user 
        """
        # check if user has impose a drift limit
        if self.userDefinedDriftTag:
            # if yes, return the drift limit based on user's input
            self.driftLimit = self.story_height * 12 * self.userDefinedDrift
        else:
            # if not, return the drift limit based on code (eg: 2%)
            self.driftLimit = self.story_height * 12 * self.allowableDrift
        return self.driftLimit

    def check_Drift(self):
        # self.driftLimit = self.calculate_drift_limit()
        # self.story_drift = self.calculate_story_drift()

        self.drift_check = self.driftLimit >= self.story_drift
        # print(self.drift_check)
        return self.drift_check

    # def increaseLength(self):
    #     """
    #     This method is used to increase the lenght of the shear wall if
    #     redesign tag is True

    #     returns: updated wallLenght attribute

    #     """
    #     if self.reDesignFlag:
    #         self.wallLength += 0.5
    #     else:
    #         pass

    #     return self.wallLength


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

#     sw_design = DesignShearWall(caseID, baseline_info_dir, 'X', wallIndex=0, floorIndex=1, 
#                                 counter=counter, wall_line_name='gridA', Ss=2, S1=0.7,
#                                 weight_factor=1, seismic_design_level='High'
#                                 )
#     # print(sw_design.find_shearwall_candidate(shearwall_database))
