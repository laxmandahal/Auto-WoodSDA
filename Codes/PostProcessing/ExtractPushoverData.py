import pandas as pd
import numpy as np 
import matplotlib.pyplot as plt
import os 
import math
from scipy import interpolate



def pushoverdata(ModelDirectory, Direction, Story, w, NumStory):
    Results = []
    BaseDirectory = ModelDirectory + 'Static-Pushover-Output-Model3D-' + Direction + 'PushoverDirection'
    BRDirectory = BaseDirectory + '\\BaseReactions\\'
    os.chdir(BRDirectory) # Change working directory to base reaction folder
    NodeBS = np.loadtxt(r'LeaningColumnBaseNode' + Direction + 'HorizontalReactions.out') 
    
    if min(NodeBS[:,0]) < 0:
        idx = [ n for n,i in enumerate(NodeBS[:,0]) if i < 0 ][0]
    else: idx = NodeBS.shape[0]

    NodeBS = NodeBS[0:idx,:]
    PanelBS = np.loadtxt(Direction + 'PanelBaseNodesHorizontalReactions.out') 
    PanelBS = PanelBS[0:idx,:]
    
    os.chdir(BaseDirectory)
    
    if os.path.isdir('./MFBaseReactions'):
        os.chdir('MFBaseReactions')
        if os.path.isfile('%sMFBaseNodesHorizontalReactions.out'%Direction):
            MFBS = np.loadtxt('%sMFBaseNodesHorizontalReactions.out'%Direction)
            MFBS = MFBS[0:idx,:]
            BR = np.asarray(np.sum(NodeBS[:,1:NodeBS.shape[1]]/w,axis=1).tolist() ) + np.sum(PanelBS[:,1:PanelBS.shape[1]]/w,axis=1).tolist() + np.sum(MFBS[:,1:MFBS.shape[1]]/w,axis=1).tolist()
        else: BR = np.asarray(np.sum(NodeBS[:,1:NodeBS.shape[1]]/w,axis=1).tolist() ) + np.sum(PanelBS[:,1:PanelBS.shape[1]]/w,axis=1).tolist()
    else: 
        BR = np.asarray(np.sum(NodeBS[:,1:NodeBS.shape[1]]/w,axis=1).tolist() ) + np.sum(PanelBS[:,1:PanelBS.shape[1]]/w,axis=1).tolist()
    
    Results.append(np.abs(BR))# Only base shear of master node should be considered, here the master node is center leaning column
    
    SDRDirectory = BaseDirectory + '\\StoryDrifts'
    os.chdir(SDRDirectory)
    DR = np.abs(np.loadtxt(r'LeaningColumn' + Direction + 'Drift.out'))
    DR = DR[0:idx,:]
    if str(Story) == 'roof': # roof drift ratio
        if NumStory == 1:
            Results.append(DR[:,4])
        else: Results.append(DR[:,-1])
            
    else: Results.append(DR[:,(Story-1)*3+1])
        
    return Results


def extractpushoverpoints(Results):
    peakstrength = np.max(Results[0])
    driftpeakstrength = Results[1][Results[0] == peakstrength][0]
    
    peakstregth_idx = Results[0].argmax()
    
    elasticStrength = Results[0][0:peakstregth_idx]
    elasticDrift = Results[1][0:peakstregth_idx]
    plasticStrength = Results[0][peakstregth_idx : -1]
    plasticDrift = Results[1][peakstregth_idx : -1]
    
    idx = (np.abs(elasticStrength - 0.8 * peakstrength)).argmin()
    elasticDrift_critical = elasticDrift[idx]
    elasticStrength_critical = elasticStrength[idx]
    
    idx = (np.abs(plasticStrength - 0.8 * peakstrength)).argmin()
    plasticDrift_critical = plasticDrift[idx]
    plasticStrength_critical = plasticStrength[idx]
    
    idx = (np.abs(plasticStrength - peakstrength)).argmin()
    totalidx = peakstregth_idx + idx 
    area = np.trapz(Results[0][0:totalidx], x = Results[1][0:totalidx])
    
    return peakstrength, driftpeakstrength, plasticDrift_critical
    
    
    
def compileDataframe(BaseDirectory, BuildingName, NumStory, SeismicWeight):
    cols = ['NumStory','SeismicWeight','peakstrength','drift@peakstrength','drift@80%peakstrength','drift@20%residualstrength','area']
    PushoverResultsX = pd.DataFrame(columns = cols, index = BuildingName)
    PushoverResultsZ = pd.DataFrame(columns = cols, index = BuildingName)
    PushoverResultsX['NumStory'] = NumStory
    PushoverResultsX['SeismicWeight'] = SeismicWeight
    PushoverResultsZ['NumStory'] = NumStory
    PushoverResultsZ['SeismicWeight'] = SeismicWeight

    for i in range(len(BuildingName)):

        PushoverX = pushoverdata(BaseDirectory + BuildingName[i]+'\OpenSees3DModels\PushoverAnalysis\\', 'X', 'roof',
                                 
                                 PushoverResultsX['SeismicWeight'][i], int(PushoverResultsX['NumStory'][i]))

        PushoverZ = pushoverdata(BaseDirectory + BuildingName[i]+'\OpenSees3DModels\PushoverAnalysis\\', 'Z', 'roof',
                                 PushoverResultsZ['SeismicWeight'][i], int(PushoverResultsZ['NumStory'][i]))

        PushoverResultsX.iloc[i,2:7] = extractpushoverpoints(PushoverX)
        PushoverResultsZ.iloc[i,2:7] = extractpushoverpoints(PushoverZ)
        
    return PushoverX, PushoverZ
        
        
        
        
        
        
        
        
        
        