"""
This file implements Generalized Linear Models (GLM) to fit the collapse fragility function. Utilizing statsmodel API, it builds
on GLM fit to quantify uncertainty in the parameter estimates using the Fishers' Information Matrix. In addition, it also computes 
Huber-White's Sandwich estimators as the appropriate variance estimator with an assumption that the probability model is not 
correctly specified. Methods to implement sampling (Monte Carlo simulation) or resampling (Bootstrapping) are also provided. 

Developed by: Laxman Dahal, UCLA
Created on: Feb 2021 

Relevant Publication to cite
Dahal, L., Burton, H., & Onyambu, S. (2022). Quantifying the effect of probability model misspecification in seismic collapse risk assessment. Structural Safety, 96, 102185.
"""

__author__ = "Laxman Dahal"


import numpy as np 
import pandas as pd
from scipy.stats import norm
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline
import statsmodels.api as sm 



class GLMProbitClass():
    '''
    This class implements GLM with Probit Link function. Statsmodel.api python package is used. 

    :param hazardLevel: Intensity Measures (IM) used to conduct nonlinear dynamic analysis. type: array
    :param collapseCount: the count of collapses at each hazard level. type: array
    :param numGM: the total number of ground motion records at each hazard level. type: array
    :param collapseRate: the mean annual frequency of exceedance of hazard level IM. Also given by reciprocal of return period
    i.e 1/Return period. type: array
    :param varType: type of variance. type: str. Options: ['observedHessian', 'expectedHessian', 'nonrobust' ]
    '''

    def __init__(self, hazardLevel, collpaseCount, numGM, collapseRate, varType='observedHessian'):
        self.logIM = np.log(hazardLevel) 
        self.collapseCount = collpaseCount
        self.numGM = numGM
        self.varType = varType
        self.collapseRate = collapseRate 
        self.IMrange = np.linspace(0.01, int(max(np.exp(self.logIM))) + 1, 500)
        self.ProbitFit()
        self.getProbCollapse()
        self.MAFC()
        self.simulatedCollapseRateCov(self.vcov)
        
    def ProbitFit(self):
        '''
        Fragility Curve Fit with Probit link function
        '''

        nonCollapseCount = self.numGM - self.collapseCount
        data = pd.DataFrame({ 'logIM':self.logIM, 'numCollapse':self.collapseCount, 'nonCollapse':nonCollapseCount })
        formula = 'numCollapse + nonCollapse ~  logIM'
     
        model = sm.GLM.from_formula( formula = formula, data = data, 
                            family=sm.families.Binomial(link = sm.families.links.probit()))
        
        if self.varType == "observedHessian":
            self.fit = model.fit(cov_type = 'hc0', optim_hessian= 'oim')
            self.summaryReport = self.fit.summary()
            self.hessian = model.hessian(self.fit.params)
            self.score = model.score(self.fit.params)[:,None]
            self.B = self.score * self.score.T
            Ainv = np.linalg.inv(-self.hessian)
            self.sandwich = Ainv * self.B * Ainv
            self.vcov  = self.fit.cov_params()
        elif self.varType == "expectedHessian":
            self.fit = model.fit(cov_type = 'hc0', optim_hessian= 'eim')
            self.summaryReport = self.fit.summary()
            self.vcov  = self.fit.cov_params()
            self.hessian = model.hessian(self.fit.params)
            self.score = model.score(self.fit.params)[:,None]
            self.B = self.score * self.score.T
            Ainv = np.linalg.inv(-self.hessian)
            self.sandwich = Ainv * self.B * Ainv
        else:
            self.fit = model.fit()  #nonrobust 
            self.summaryReport = self.fit.summary()
            self.vcov  = self.fit.cov_params()
            self.hessian = model.hessian(self.fit.params)
            self.score = model.score(self.fit.params)[:,None]
            self.B = self.score * self.score.T
            Ainv = np.linalg.inv(-self.hessian)
            self.sandwich = Ainv * self.B * Ainv
            
        self.fittedProbCollapse = norm.cdf(self.fit.params[0] + self.fit.params[1] * self.logIM)
            
            
    def getProbCollapse(self):
        '''
        Getter method that returns the probability of collapse conditioned on IM level 
        '''
        return norm.cdf(self.fit.params[0] + self.fit.params[1] * self.logIM)

        
    def plotParamsDispersion(self):
        '''
        Method to plot the dispersion in parameter estimates
        ''' 
        beta0 = self.fit.params[0]
        beta1 = self.fit.params[1]
        
        Var_beta0 = self.vcov['Intercept'][0]
        Var_beta1 = self.vcov['logIM'][1]

        np.random.seed(42)
        sample_beta0 = np.random.normal(beta0, np.sqrt(Var_beta0), 10000)
        sample_beta1 = np.random.normal(beta1, np.sqrt(Var_beta1), 10000)

        fig, (ax1, ax2) = plt.subplots(1,2)
        fig.set_figheight(7)
        fig.set_figwidth(14)
        count, bins, ignored = ax1.hist(sample_beta0, 30, density=True, histtype = 'step')
        ax1.plot(bins, 1/(np.sqrt(Var_beta0) * np.sqrt(2 * np.pi)) * np.exp( - (bins - beta0)**2 / (2 * Var_beta0) ),
                 linewidth=3, color='r')
        ax1.title.set_text(r'Dispersion in $\beta_0$')
        count, bins, ignored = ax2.hist(sample_beta1, 30, density=True, histtype = 'step')
        ax2.plot(bins, 1/(np.sqrt(Var_beta1) * np.sqrt(2 * np.pi)) * np.exp( - (bins - beta1)**2 / (2 * Var_beta1) ),
                 linewidth=3, color='r')
        ax2.title.set_text(r'Dispersion in $\beta_1$') 
        
    def plotCollapseFragility(self):
        '''
        Method to plot the collapse fragility curve
        '''
        self.IMrange = np.linspace(0.01, int(max(np.exp(self.logIM))) + 1, 500)
        
        ProbCollapse_IMrange = norm.cdf(self.fit.params[0] + self.fit.params[1] * np.log(self.IMrange))
           
        plt.figure(figsize = (10,6))
        plt.plot(self.IMrange, ProbCollapse_IMrange, color = 'red', label = 'GLM Fit w/ Probit Link')
        plt.scatter(np.exp(self.logIM), self.collapseCount / self.numGM, color = 'green', marker = 's', 
                    label = 'Fraction of Collapse')
        plt.scatter(np.exp(self.logIM), self.fittedProbCollapse, color = 'black', marker = '*', s = 80,  
                    label = 'Fitted Probability of Collapse')
        
        plt.title('Collapse Fragility Curve')
        plt.xlabel('IM(Sa)')
        plt.ylabel('Probability of Collapse')
        plt.legend()
        plt.grid(linewidth = 0.5)
        
    def plotConfidenceInterval(self, lowerBound=0.025, upperBound=0.975): 
        '''
        Method to plot the confidence interval on the collapse fragility curve. 
        :param: lowerbound: Lower bound of the confidence interval. type: float
        :param: upperbound: Upper bound of the confidence interval. type: float
        Notes
        ----
        The difference between the upper and lower bound is typically 95%
        '''
        
        meanEta = self.fit.params[0] + self.fit.params[1] * np.log(self.IMrange)
        varEta = self.vcov['Intercept'][0] + self.vcov['logIM'][1] * np.log(self.IMrange)**2 + \
                2 * self.vcov['Intercept'][1] * np.log(self.IMrange)

        stdEta = np.sqrt(varEta)

        muPc = norm.cdf(meanEta)
        muPc_upper = norm.cdf(norm.ppf(upperBound)*np.sqrt(varEta) + meanEta)
        muPc_lower = norm.cdf(norm.ppf(lowerBound)*np.sqrt(varEta) + meanEta)

        plt.figure(figsize = (10,6))
        plt.plot(self.IMrange, muPc, color = 'red' , label = '50 Percentile' )
        plt.plot(self.IMrange, muPc_lower, color = 'blue',linestyle='dashed', label = '2.5 Percentile' )
        plt.plot(self.IMrange, muPc_upper, color = 'black',linestyle='dashed', label = '97.5 Percentile' )

        # plt.scatter(hazardLevel, numCount1/numGM, color = 'green', marker = 's', label = 'Fraction of Collapse')
        plt.title('Collapse Fragility Curve')
        plt.xlabel('IM(Sa)')
        plt.ylabel('Probability of Collapse')
        plt.legend()
        plt.grid(linewidth = 0.5)
        
    def MAFC(self):
        '''
        Method to estimate the Mean Annual Frequency of Collapse (MAFC) using Reimann's Sum.
        It also estimates the variance around MAFC using Taylor approximation method
        '''
        
        interpolationFunc = CubicSpline(np.exp(self.logIM), self.collapseRate)
        lambdaRange = interpolationFunc(self.IMrange)
        
        lambdaCollapse_temp = []
        
        for i in range(len(self.IMrange)-1):
    
            midIM = (self.IMrange[i] + self.IMrange[i+1]) / 2
    
            pc_temp = norm.cdf(self.fit.params[0] + self.fit.params[1] * np.log(midIM))
            lamC = pc_temp * np.abs(lambdaRange[i] - lambdaRange[i+1]) 
    
            lambdaCollapse_temp.append(lamC)
    
        self.meanLambdaCollapse = np.sum(lambdaCollapse_temp)
        
        meanEta = self.fit.params[0] + self.fit.params[1] * np.log(self.IMrange)
        stdEta = np.sqrt(self.vcov['Intercept'][0] + self.vcov['logIM'][1] * np.log(self.IMrange)**2 + \
                2 * self.vcov['Intercept'][1] * np.log(self.IMrange))
        
        sigmaProbCollapse = norm.pdf(meanEta) * stdEta

        sigmaCollapse = np.zeros((len(self.IMrange), len(self.IMrange)))
        for i in range(len(self.IMrange)-1):
            for j in range (len(self.IMrange) - 1):
                sigmaCollapse[i,j] = np.abs(lambdaRange[i] - lambdaRange[i+1])\
                            * np.abs(lambdaRange[j] - lambdaRange[j+1]) * sigmaProbCollapse[i] * sigmaProbCollapse[j]
        
        self.sigmaLambdac = np.sqrt(sum(sum(sigmaCollapse)))
        
        
    def getProbCollapse_years(self, numYear): 
        '''
        Getter method that returns the probability of collapse over a specified time period

        :param numYear: number of year. type: int/float
        '''
        return 1 - np.exp(-numYear * self.meanLambdaCollapse)
    
    

    
    def simulatedCollapseRateCov(self, vcov, numSamples=500, period=50, seed = 42, resamplingFlag = False):
        '''
        This method implements sampling and/or resampling technique to quantify paramters uncertainty.
        When resampling flag is set to `False`, the sample are simply draws from Monte Carlo Simulation but when it is set to 
        'True` bootstrapping samples are draws from the MC samples by resampling the MC samples. 
        :param: numSamples: Number of sample to be drawn. type: int 
        :param: period: Number of years to compute the probability of collapse for a given year. type: int or float
        :param seed: Method used to initialize the random number generator. type: int 
        :param resamplingFalg: Flag to indicate if bootstrapping is desired or not. type: str
        '''
        
        mean = np.array([self.fit.params[0],self.fit.params[1]])
        cov = np.array(vcov)

        lambdaCollapsehist = []
        samplePc_hist = []
        np.random.seed(seed)
        sampleBeta0, sampleBeta1 = np.random.multivariate_normal(mean, cov, size = numSamples).T
        
        
        for i in range(len(sampleBeta0)):
            simlambda_c, simProbCol_yrs = self.computeCollapseRate(sampleBeta0[i], sampleBeta1[i], period)
            
            lambdaCollapsehist.append(simlambda_c)
            samplePc_hist.append(simProbCol_yrs)
            
        
        self.varCollapseRate = np.std(lambdaCollapsehist)**2
        self.varProbCollapse = np.std(samplePc_hist)**2
            
        return lambdaCollapsehist, samplePc_hist


    def computeCollapseRate(self, beta0, beta1, period):
        '''
        Method to compute collapse rate given the parameter estimates, beta0 and beta1 from the GLM Probit fit. 
        Also see `simulatedCollapseRateCov` 
        
        :param beta0: Intercept of the GLM model. type: float 
        :param beta1: coefficient of the GLM model. type: float
        :param period: Number of years to compute the probability of collapse for a given year. type: int or float

        Note
        ------
        This is a pseudo-method which is implemented in method `simulatedCollapseRateCov`. The parameter estimates: beta0 and beta1
        are output of GLM fit and do not need to be provided or guessed. 
        '''
        
        interpolationFunc = CubicSpline(np.exp(self.logIM), self.collapseRate)
        lambdaRange = interpolationFunc(self.IMrange)

        lambdaCollapse_temp = []

        for i in range(len(self.IMrange)-1):

            midIM = (self.IMrange[i] + self.IMrange[i+1]) / 2

            pc_temp = norm.cdf(beta0 + beta1 * np.log(midIM))
            lamC = pc_temp * np.abs(lambdaRange[i] - lambdaRange[i+1]) 

            lambdaCollapse_temp.append(lamC)


        meanLambdaCollapse = np.sum(lambdaCollapse_temp)
        probCollapseGivenYears = 1 - np.exp(-meanLambdaCollapse*period)
        return meanLambdaCollapse, probCollapseGivenYears










