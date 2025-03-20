
# coding: utf-8

####################################################### Extract Maximum EDP ##################################################################
# This script is used for extracting multiple cases' maximum EDP (PFA, SDR & RDR) when using parallel computing on the cluster.
# The maximum EDP will be used for generating collapse and demolition fragility, also as input of SP3.
# The output of this part will be served as the sub-class 'Building Model Information' of class 'Building'.
# Author: Laxman Dahal
# Contributor: Zhengxiang Yi
##############################################################################################################################################




# Import packages
import numpy as np
import math
import os
import pandas as pd
import sys

from scipy.stats import lognorm
from scipy.stats import binom
from scipy.stats import norm
from scipy.stats import truncnorm
from scipy.stats import uniform
from scipy.optimize import minimize



# Data extraction 

# INPUTS:
# Eigen/DynamicDirectory    1x1   String   Specify the path to eigen/dynamic model 
# HazardLevel               1x20           Sas of hazard levels (20 in Peer-CEA project)
# NumGM                     1xn            Number of ground motion pairs, which should be 2 x number of records to match the SP3 input format
# NumStory                  1x1            Number of stories for each model (2 (including cripple wall) in Peer-CEA project)

# OUTPUTS (in SP3 input form):
# Period                    1x3            DataFrame    First 3 modal periods of model
# SDR                       nx(NumStory+3) DataFrame    Maximum story drift ratio among all leaning columns 
# RDR                       nx4            DataFrame    Maximum residual story drift ratio among all leaning columns
# PFA                       nx(NumStory+4) DataFrame    Peak story acceleration among all leaning columns
                                                        # 1st column: Hazard Level
                                                        # 2nd column: Direction
                                                        # 3rd column: GM number 
                                                        # 4th to end: MaxSDR / MaxPFA / MaxRDR
# Attention: 
# 1. Number of hazard levels should be the same as number of ground motion sets, because each hazard level corresponding to a GM set
# 2. Hazard levels in scale g, corresponding to Sas

                
def ExtractPeriod (EigenDirectory):
    EigenResultsDirectory = os.path.join(EigenDirectory, 'Modes')
    os.chdir(EigenResultsDirectory)
    period = pd.DataFrame(0, index=range(1), columns=range(3))
    f = np.loadtxt(r'periods.out') 
    
    period.loc[0,0] = f[0]
    period.loc[0,1] = f[1]
    period.loc[0,2] = f[2]
    
    return period
    
def ExtractSDR (DynamicDirectory, HazardLevel, NumGM, NumStory):
    NumHazardLevel = len(HazardLevel)
    TotalNumGM = np.sum(NumGM)*2 # Number of rows
    TotalFeatures = NumStory+3 # Number of columns 
    
    # Follow the input pattern of SP3
    SDR = pd.DataFrame(0, index=range(TotalNumGM), columns=range(TotalFeatures))
    NumGM_temp1 = np.insert(NumGM,0,0)*2
    NumGM_temp2 = np.cumsum(NumGM_temp1)
    
    for i in range(NumHazardLevel):
        CurrentHazardlevel = i+1
        SDR.loc[NumGM_temp2[i]:NumGM_temp2[i+1]-1,0] = CurrentHazardlevel # Hazard level index

        SDR.loc[NumGM_temp2[i]:NumGM_temp2[i]+NumGM_temp1[i+1]/2-1,1] = 1 # Direction index: direction 1
        SDR.loc[NumGM_temp2[i]+NumGM_temp1[i+1]/2:NumGM_temp2[i+1]-1,1] = 2 # Direction index: direction 2


        SDR.loc[NumGM_temp2[i]:NumGM_temp2[i]+NumGM_temp1[i+1]/2-1,2] = np.arange(1,NumGM[i]+1) # GM pair index: direction 1
        SDR.loc[NumGM_temp2[i]+NumGM_temp1[i+1]/2:NumGM_temp2[i+1]-1,2] = np.arange(1,NumGM[i]+1) # GM pair index: direction 2

        # Loop over all ground motions in one hazard level
        for j in range(NumGM[i]):
            # print('Hazard Level %i GM number %i'%(i+1,j))
            SDRDirectory = os.path.join(DynamicDirectory, 'ModelSingleScaleOutputBiDirection', 'HazardLevel%d'%CurrentHazardlevel, 'EQ_%d'%(j+1), 'StoryDrifts')
            sys.path.append(SDRDirectory)

            XMidDrift = np.abs(np.loadtxt(os.path.join(SDRDirectory, 'MidLeaningColumnXDrift.out')))
            XCorDrift = np.abs(np.loadtxt(os.path.join(SDRDirectory,'CornerLeaningColumnXDrift.out')))
            ZMidDrift = np.abs(np.loadtxt(os.path.join(SDRDirectory,'MidLeaningColumnZDrift.out')))
            ZCorDrift = np.abs(np.loadtxt(os.path.join(SDRDirectory,'CornerLeaningColumnZDrift.out')))
            
            # XMidDrift = XMidDrift[:, [0] + [2*i+1 for i in range(int(XMidDrift.shape[1]/2))]]
            # XCorDrift = XCorDrift[:, [0] + [2*i+1 for i in range(int(XCorDrift.shape[1]/2))]]
            # ZMidDrift = ZMidDrift[:, [0] + [2*i+1 for i in range(int(ZMidDrift.shape[1]/2))]]
            # ZCorDrift = ZCorDrift[:, [0] + [2*i+1 for i in range(int(ZCorDrift.shape[1]/2))]]

            # XDrift = np.abs(np.loadtxt(r'LeaningColumnXDrift.out'))
            # ZDrift = np.abs(np.loadtxt(r'LeaningColumnZDrift.out'))

            # Loop over all stories 
            for k in range(NumStory):
                SDR.loc[NumGM_temp2[i]+j,k+3] = max(max(XMidDrift[:,3*k+1]),max(XMidDrift[:,3*k+2]),max(XMidDrift[:,3*k+3]),\
                                                   max(XCorDrift[:,4*k+1]),max(XCorDrift[:,4*k+2]),max(XCorDrift[:,4*k+3]),max(XCorDrift[:,4*k+4]))
                SDR.loc[NumGM_temp2[i]+NumGM_temp1[i+1]/2+j,k+3] = max(max(ZMidDrift[:,3*k+1]),max(ZMidDrift[:,3*k+2]),max(ZMidDrift[:,3*k+3]),\
                                                                      max(ZCorDrift[:,4*k+1]),max(ZCorDrift[:,4*k+2]),max(ZCorDrift[:,4*k+3]),max(ZCorDrift[:,4*k+4]))

                # SDR.loc[NumGM_temp2[i]+j,k+3] = max(max(XDrift[:,3*k+1]),max(XDrift[:,3*k+2]),max(XDrift[:,3*k+3]))
                # SDR.loc[NumGM_temp2[i]+NumGM_temp1[i+1]/2+j,k+3] = max(max(ZDrift[:,3*k+1]),max(ZDrift[:,3*k+2]),max(ZDrift[:,3*k+3]))

            
    return SDR

    
def ExtractRDR (DynamicDirectory, HazardLevel, NumGM, NumStory):
    
    NumHazardLevel = len(HazardLevel)
    TotalNumGM = np.sum(NumGM)*2 # Number of rows
    TotalFeatures = 4 # Number of columns 
    
    
    # Follow the input pattern of SP3
    RDR = pd.DataFrame(0, index=range(TotalNumGM), columns=range(TotalFeatures))
    NumGM_temp1 = np.insert(NumGM,0,0)*2
    NumGM_temp2 = np.cumsum(NumGM_temp1)
    
    for i in range(NumHazardLevel):
        CurrentHazardlevel = i+1
        RDR.loc[NumGM_temp2[i]:NumGM_temp2[i+1]-1,0] = CurrentHazardlevel # Hazard level index

        RDR.loc[NumGM_temp2[i]:NumGM_temp2[i]+NumGM_temp1[i+1]/2-1,1] = 1 # Direction index: direction 1
        RDR.loc[NumGM_temp2[i]+NumGM_temp1[i+1]/2:NumGM_temp2[i+1]-1,1] = 2 # Direction index: direction 2


        RDR.loc[NumGM_temp2[i]:NumGM_temp2[i]+NumGM_temp1[i+1]/2-1,2] = np.arange(1,NumGM[i]+1) # GM pair index: direction 1
        RDR.loc[NumGM_temp2[i]+NumGM_temp1[i+1]/2:NumGM_temp2[i+1]-1,2] = np.arange(1,NumGM[i]+1) # GM pair index: direction 2

        # Loop over all ground motions in one hazard level
        for j in range(NumGM[i]):
            RDRDirectory = os.path.join(DynamicDirectory, 'ModelSingleScaleOutputBiDirection', 'HazardLevel%d'%CurrentHazardlevel, 'EQ_%d'%(j+1), 'StoryDrifts')
            sys.path.append(RDRDirectory)
            # os.chdir(RDRDirectory)

            XMidDrift = np.abs(np.loadtxt(os.path.join(RDRDirectory, 'MidLeaningColumnXDrift.out')))
            XCorDrift = np.abs(np.loadtxt(os.path.join(RDRDirectory, 'CornerLeaningColumnXDrift.out')))
            ZMidDrift = np.abs(np.loadtxt(os.path.join(RDRDirectory, 'MidLeaningColumnZDrift.out')))
            ZCorDrift = np.abs(np.loadtxt(os.path.join(RDRDirectory, 'CornerLeaningColumnZDrift.out')))

            # XMidDrift = XMidDrift[:, [0] + [2*i+1 for i in range(int(XMidDrift.shape[1]/2))]]
            # XCorDrift = XCorDrift[:, [0] + [2*i+1 for i in range(int(XCorDrift.shape[1]/2))]]
            # ZMidDrift = ZMidDrift[:, [0] + [2*i+1 for i in range(int(ZMidDrift.shape[1]/2))]]
            # ZCorDrift = ZCorDrift[:, [0] + [2*i+1 for i in range(int(ZCorDrift.shape[1]/2))]]

            # XDrift = np.abs(np.loadtxt(r'LeaningColumnXDrift.out'))
            # ZDrift = np.abs(np.loadtxt(r'LeaningColumnZDrift.out'))
            # RDR.loc[NumGM_temp2[i]+j,3] = max(XDrift[-1,1:3*NumStory])
            # RDR.loc[NumGM_temp2[i]+NumGM_temp1[i+1]/2+j,3] = max(ZDrift[-1,1:3*NumStory])

                        
            RDR.loc[NumGM_temp2[i]+j,3] = max(max(XMidDrift[-1,1:3*NumStory+1]),max(XCorDrift[-1,1:4*NumStory+1]))
            RDR.loc[NumGM_temp2[i]+NumGM_temp1[i+1]/2+j,3] = max(max(ZMidDrift[-1,1:3*NumStory+1]),max(ZCorDrift[-1,1:4*NumStory+1]))
               
    return RDR



def ExtractPGA (GMDirectory, HazardLevel, NumGM):
    NumHazardLevel = len(HazardLevel)
    TotalNumGM = np.sum(NumGM)*2 # Number of rows
    NumGM_temp1 = np.insert(NumGM,0,0)*2
    NumGM_temp2 = np.cumsum(NumGM_temp1)
    
    PGA = pd.DataFrame(0, index=range(np.sum(TotalNumGM)), columns=range(1))


    for i in range(NumHazardLevel):
        # Define ground motion information stored directory, the information of ground motion of each hazard level shouled be stored in 
        # seperate folder. 

        GMHistoryDirectory =  os.path.join(GMDirectory, '%s'%(i+1), 'histories')
        GMInfoDirectory = os.path.join(GMDirectory, '%s'%(i+1), 'GroundMotionInfo')
        
        sys.path.append(GMInfoDirectory)
        sys.path.append(GMHistoryDirectory)

        # os.chdir (GMInfoDirectory)
        ScalingFactor = np.loadtxt(os.path.join(GMInfoDirectory, 'BiDirectionMCEScaleFactors.txt'))
        GMName = np.loadtxt(os.path.join(GMInfoDirectory, 'GMFileNames.txt'), dtype=str)

        # We have 2 perpendicular directions, also consider the responses in each direction respectively
        for j in range(NumGM[i]):
            # os.chdir(GMHistoryDirectory)
            XPGA = max(np.abs(np.loadtxt(os.path.join(GMHistoryDirectory, GMName[2*j]), dtype = float)))*ScalingFactor[j]
            ZPGA = max(np.abs(np.loadtxt(os.path.join(GMHistoryDirectory, GMName[2*j+1]), dtype = float)))*ScalingFactor[j]
            # XPGA = max(np.abs(np.loadtxt('%s'%GMName[2*j], dtype = float)))
            # ZPGA = max(np.abs(np.loadtxt('%s'%GMName[2*j+1], dtype = float)))
            PGA.loc[j+NumGM_temp2[i],0] = XPGA
            PGA.loc[j+NumGM_temp2[i]+NumGM[i],0] = ZPGA
            PGA.loc[j+NumGM[i]+NumGM_temp2[i],0] = ZPGA
            PGA.loc[j+NumGM[i]+NumGM_temp2[i]+NumGM[i],0] = XPGA
    return PGA

# def ExtractPGA (GMDirectory, GMHistoryDirectory, HazardLevel, NumGM, FEMA_P695=False):
# # def ExtractPGA (GMHistoryDirectory, GMInfoDirectory, HazardLevel, NumGM): 
#     numRecords = np.array(NumGM, dtype=int) * 2
#     NumHazardLevel = len(HazardLevel)
#     TotalNumGM = np.sum(numRecords)*2 # Number of rows
#     NumGM_temp1 = np.insert(numRecords,0,0)*2
#     NumGM_temp2 = np.cumsum(NumGM_temp1)
    
#     pga_all = []

#     for i in range(NumHazardLevel):
#         if FEMA_P695:
#             GMHistoryDirectory =  os.path.join(GMDirectory, '%s'%(i+1), 'histories')
#             GMInfoDirectory_fp = os.path.join(GMDirectory, '%s'%(i+1), 'GroundMotionInfo')
#         else:
#             GMInfoDirectory_fp = os.path.join(GMDirectory, '%s'%(i+1))
#         # if the ground motion set is intensity-agnostic
#         # il_str = str(HazardLevel[i]).replace('.', 'p')
        

#        # if NumHazardLevel == 1:
#         #    GMHistoryDirectory =  os.path.join(GMDirectory, 'histories')
#          #   GMInfoDirectory = os.path.join(GMDirectory, 'GroundMotionInfo')
        
#         sys.path.append(GMInfoDirectory_fp)
#         sys.path.append(GMHistoryDirectory)
        
#         if FEMA_P695:
#             ScalingFactor = np.loadtxt(os.path.join(GMInfoDirectory_fp, 'BiDirectionMCEScaleFactors.txt'))
#         else:
#             ScalingFactor = np.loadtxt(os.path.join(GMInfoDirectory_fp, 'ScaleFactors.txt'))
#         GMName = np.loadtxt(os.path.join(GMInfoDirectory_fp, 'GMFileNames.txt'), dtype=str)

#         # We have 2 perpendicular directions, also consider the responses in each direction respectively
#         xpga = []
#         zpga = []
#         for j in range(NumGM[i]):
#             # os.chdir(GMHistoryDirectory)
#             if FEMA_P695:
#                 XPGA = max(np.abs(np.loadtxt(os.path.join(GMHistoryDirectory, f'{GMName[::2][j]}.txt'), dtype = float)))*ScalingFactor[j]
#                 ZPGA = max(np.abs(np.loadtxt(os.path.join(GMHistoryDirectory, f'{GMName[1::2][j]}.txt'), dtype = float)))*ScalingFactor[j]
#             else:
#                 XPGA = max(np.abs(np.loadtxt(os.path.join(GMHistoryDirectory, GMName[::2][j]), dtype = float)))*ScalingFactor[j]
#                 ZPGA = max(np.abs(np.loadtxt(os.path.join(GMHistoryDirectory, GMName[1::2][j]), dtype = float)))*ScalingFactor[j]
#             xpga.append(XPGA)
#             zpga.append(ZPGA)
        

#         pga_all.append(xpga)
#         pga_all.append(xpga)
#         pga_all.append(zpga)
#         pga_all.append(zpga)
    
#     d = {0:np.array(pga_all).flatten()}
#     PGA = pd.DataFrame(d)
#     return PGA
    
def ExtractPFA (DynamicDirectory, HazardLevel, NumGM, NumStory, PGA, g = 386.4):   
    NumHazardLevel = len(HazardLevel)
    NumGM_temp1 = np.insert(NumGM,0,0)*2
    NumGM_temp2 = np.cumsum(NumGM_temp1)
    
    # Follow the input pattern of SP3
    TotalNumGM = np.sum(NumGM)*2 # Number of rows
    TotalFeatures = NumStory+4 # Number of columns 
    
    PFA = pd.DataFrame(0, index=range(TotalNumGM), columns=range(TotalFeatures)) # Initialize

    
    PFA.loc[:,3] = PGA.loc[:,0]
    
    for i in range(NumHazardLevel):
        CurrentHazardlevel = i+1
        PFA.loc[NumGM_temp2[i]:NumGM_temp2[i+1]-1,0] = CurrentHazardlevel # Hazard level index

        PFA.loc[NumGM_temp2[i]:NumGM_temp2[i]+NumGM_temp1[i+1]/2-1,1] = 1 # Direction index: direction 1
        PFA.loc[NumGM_temp2[i]+NumGM_temp1[i+1]/2:NumGM_temp2[i+1]-1,1] = 2 # Direction index: direction 2


        PFA.loc[NumGM_temp2[i]:NumGM_temp2[i]+NumGM_temp1[i+1]/2-1,2] = np.arange(1,NumGM[i]+1) # GM pair index: direction 1
        PFA.loc[NumGM_temp2[i]+NumGM_temp1[i+1]/2:NumGM_temp2[i+1]-1,2] = np.arange(1,NumGM[i]+1) # GM pair index: direction 2

        # Loop over all ground motions in one hazard level
        for j in range(NumGM[i]):
            # print('Hazard Level %i GM number %i'%(i,j))
            PFADirectory = os.path.join(DynamicDirectory, 'ModelSingleScaleOutputBiDirection', 'HazardLevel%d'%CurrentHazardlevel, 'EQ_%d'%(j+1), 'NodeAccelerations')
            os.chdir(PFADirectory)
            sys.path.append(PFADirectory)

            # Loop over all stories 
            for k in range(NumStory):
                
                XAcc = np.abs(np.loadtxt(r'LeaningColumnNodeXAbsoAccLevel%d.out'%(k+2)))
                ZAcc = np.abs(np.loadtxt(r'LeaningColumnNodeZAbsoAccLevel%d.out'%(k+2)))

                ## changelog. Date: 1/22/2024
                ## some of the HiFi runs resulted in "OverflowError: Python int too large to convert to C long" error
                max_val_x = np.max(np.array(XAcc[:,1], dtype=np.float64))
                if max_val_x > 10000:
                    max_val_x = 10 * g 

                PFA.loc[NumGM_temp2[i]+j,k+4] = max_val_x/g
                ## changelog. Date: 12/15/2023
                ## some of the HiFi runs resulted in "OverflowError: Python int too large to convert to C long" error
                max_val = np.max(np.array(ZAcc[:,1], dtype=np.float64))
                if max_val > 10000:
                    max_val = 10 * g 
                # print(max_val)
                PFA.loc[NumGM_temp2[i]+NumGM_temp1[i+1]/2+j,k+4] = max_val/g
            
    return PFA

def Count(EDP, Criteria, NumGM):
    # This function is used for counting the number of violations (collapse, exceed specific damage state, demolition) given criteria
    # Single criteria is used here, which can be modified to incorperate with multiple criteria
    # The input pattern follows standard SP3 input, which is done above
    NumGM_temp1 = np.insert(NumGM,0,0)*2
    NumGM_temp2 = np.cumsum(NumGM_temp1)
    
    NumCount = []
    for i in range(len(NumGM)):
        count = 0
        
        for j in range(NumGM[i]):           
            MaxResponse = max(max(EDP.loc[NumGM_temp2[i]+j,3:(EDP.shape[1]-1)]),max(EDP.loc[NumGM_temp2[i]+NumGM_temp1[i+1]/2+j,3:(EDP.shape[1]-1)]))
        
            if MaxResponse >= Criteria:
                count = count + 1
        
        NumCount.append(count)
        
    return NumCount

# This part is used for function fit (especially for lognoraml distribution) using MLE and SSE given EDP violations counting
# NumCount : Number of violations to specific criteria (collapse, damage state, demolition)
# HazardLevel: Sas of analysis
# NumGM: Number of ground motions in each hazard level

# Negative log-likelihood function
def neg_loglik(theta, HazardLevel, NumCount, NumGM):
    
    p_pred = norm.cdf(np.log(HazardLevel), loc = np.log(theta[0]), scale = np.log(theta[1]))
    likelihood = binom.pmf(NumCount, NumGM, p_pred)
    
    return -np.sum(np.log(likelihood))

# Square error function
def squareerror(theta, HazardLevel, NumCount, NumGM):
    
    p_real = NumCount/NumGM
    p_pred = norm.cdf(np.log(HazardLevel), loc = np.log(theta[0]), scale = np.log(theta[1]))
    
    return np.sum((p_real - p_pred)**2)


def lognormfit (HazardLevel, NumCount, NumGM, Method):
    
    theta_start = [2,3] # Initial guess, pay attention to initial guess to avoid log(0) and log (1)
    
    theta = []
    if Method == 'MLE':
        res = minimize(neg_loglik, theta_start, args = (HazardLevel, NumCount, NumGM), method = 'Nelder-Mead', options={'disp': True})
    else:
        res = minimize(squareerror, theta_start, args = (HazardLevel, NumCount, NumGM), method = 'Nelder-Mead', options={'disp': True})
    
    
    theta.append(res.x[0])
    theta.append(np.log(res.x[1]))
                 
    return theta # Return the mean and standard deviation 

