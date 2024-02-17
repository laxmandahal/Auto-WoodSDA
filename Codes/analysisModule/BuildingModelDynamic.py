
# Import packages
import numpy as np
import math
import os
import pandas as pd


# Import functionsYour location
from ExtractMaxEDP import ExtractSDR
from ExtractMaxEDP import ExtractRDR
from ExtractMaxEDP import ExtractPGA
from ExtractMaxEDP import ExtractPFA
from ExtractMaxEDP import Count
from ExtractMaxEDP import lognormfit
from ExtractMaxEDP import neg_loglik
from ExtractMaxEDP import squareerror 




class BuildingModelDynamic(object):
    
    def __init__(self, CaseID, modelDir, gm_hist_dir,
                 NumStory, HazardLevel, NumGM,
                 CollapseCriteria = 0.1, 
                 DemolitionCriteria = 0.01,
                 gm_FEMA_P695=True):
        self.ID = CaseID
        self.modelDir = modelDir
        
        # Directory info
        DynamicDirectory = os.path.join(modelDir, *[CaseID, 'DynamicAnalysis'])
        # EigenDirectory = BaseDirectory + ID + '/OpenSees3DModels/EigenValueAnalysis/'
        # GMDirectory = os.path.join(modelDir, *['GM_sets', 'BoelterHall'])
        # GMDirectory = os.path.join(modelDir, *['GM_sets', 'Miranda240GM'])
        # GMDirectory = os.path.join(modelDir, *['GM_sets', GM_name])
        # siteID = CaseID.split('_')[0]
        # GMDirectory = GM_name
        GMHistoryDirectory = os.path.join(gm_hist_dir, *['histories'])
        # GMInfoDirectory = os.path.join(modelDir, *['RegionalGroundMotions', siteID])
        if gm_FEMA_P695:
            GMDirectory = os.path.join(modelDir, *['GM_sets', 'FEMAP695_FarFault_ATC116Model'])
        else:
            GMDirectory = os.path.join(modelDir, *['GM_sets', 'site_agnostic_30GMs'])
        # GMHistoryDirectory = os.path.join(GMInfoDirectory, *['histories'])

        self.HazardLevel = HazardLevel
        self.NumGM = NumGM
        temp = NumGM / 2
        self.NumGM_for_PGA = temp.astype(int)
        self.NumStory = NumStory
        
        # Post-processing
        self.SDR = ExtractSDR (DynamicDirectory, self.HazardLevel, self.NumGM, self.NumStory)
        self.RDR = ExtractRDR (DynamicDirectory, self.HazardLevel, self.NumGM, self.NumStory)
        self.PGA = ExtractPGA (GMDirectory, GMHistoryDirectory, self.HazardLevel, self.NumGM_for_PGA, 
                               FEMA_P695=gm_FEMA_P695)
        # self.PGA = ExtractPGA (GMHistoryDirectory, self.HazardLevel, self.NumGM)
        self.PFA = ExtractPFA (DynamicDirectory, self.HazardLevel, self.NumGM, self.NumStory, 
                               self.PGA, 
                               g = 386.4)
        
        self.CollapseCount = pd.DataFrame(Count(self.SDR, CollapseCriteria, self.NumGM))
        # self.CollapseFragility = pd.DataFrame(lognormfit(self.HazardLevel, Count(self.SDR, CollapseCriteria, self.NumGM), self.NumGM, 'MLE'))
        # self.DemolitionFragility = pd.DataFrame(lognormfit(self.HazardLevel, Count(self.RDR, DemolitionCriteria, self.NumGM), self.NumGM, 'MLE'))

        
        

    

        
