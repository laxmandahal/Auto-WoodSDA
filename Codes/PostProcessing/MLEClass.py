"""
This file Maximum Likelihood Estimation (MLE) to fit the collapse fragility function. Utilizing scipy pacakage and its built in
optimization routine, lognormal distribution parameters (Median and log-standard deviation) are estimated. Symbolic python package
is implemented to compute the score and hessian of the errof function-baded log-likelihood function. In addition, numdifftools 
package is utilized to verify the score and hessian computed using symbolic python. The score and hessian are used to compute 
Huber-White's Sandwich estimators as the appropriate variance estimator with an assumption that the probability model is not 
correctly specified. Methods to implement sampling (Monte Carlo simulation) or resampling (Bootstrapping) are also provided. 

Developed by: Laxman Dahal, UCLA
Created on: Feb 2021 

Relevant Publication to cite: 
Dahal, L., Burton, H., & Onyambu, S. (2022). Quantifying the effect of probability model misspecification in seismic collapse risk assessment. Structural Safety, 96, 102185.

"""

__author__ = "Laxman Dahal"


import numpy as np 
import math
import os
import pandas as pd
import random 

from scipy.stats import binom
from scipy.stats import norm
from scipy.optimize import minimize

import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline
import statsmodels.api as sm 
import sympy as sym
import numdifftools as ndt

from GLMClass import GLMProbitClass


class MaximumLikelihoodMethod():
    '''
    This class implements MLE which minimizes log-likelihood function.

    :param hazardLevel: Intensity Measures (IM) used to conduct nonlinear dynamic analysis. type: array
    :param collapseCount: the count of collapses at each hazard level. type: array
    :param numGM: the total number of ground motion records at each hazard level. type: array
    :param collapseRate: the mean annual frequency of exceedance of hazard level IM. Also given by reciprocal of return period
    i.e 1/Return period. type: array

    '''
    def __init__(self, hazardLevel, collpaseCount, numGM, collapseRate):
        
        self.hazardLevel = hazardLevel
        self.logIM = np.log(hazardLevel) 
        self.collapseCount = collpaseCount
        self.numGM = numGM
#         self.varType = varType
        self.collapseRate = collapseRate #mean annual frequency of collapse (\lambda_c)
        
        self.GLMmodel = GLMProbitClass(hazardLevel, collpaseCount, numGM, collapseRate, varType='nonrobust')
        self.GLMmodel_Sandwich = GLMProbitClass(hazardLevel, collpaseCount, numGM, collapseRate, varType='expectedHessian')
        
        
        self.IMrange = np.linspace(0.01, int(max(self.hazardLevel)) + 1, 500)
        
        self.fittedCollapseProbability()
        self.MAFC()
        self.varianceTaylorSeries()
        self.varianceErrorFunction()
        self.scoreErrorFunction()
        self.sandwichEstimators()
        self.simulatedCollapseRateCov(self.vcov_erf)
        
        
        
    def fittedCollapseProbability(self):
        '''
        This is the main method where optimization routine is compiled. It reads in the `lognormfit` function which returns the mean
        estimates of  median and log-standard deviation. 

        :param optim_algorithm: Optimization algorithm. 'MLE' is default but Sum of Squared Error (SSE) can also be implemented. 
        type: str  
        '''
        def neg_loglik(theta, HazardLevel, NumCount, NumGM):
            '''
        This method is a setup for negative log-likelihood function.

        :param theta: An array with median and log-standard deviation values. type: array
        :param hazardLevel: Intensity Measures (IM) used to conduct nonlinear dynamic analysis. type: array
        :param numCount: the count of collapses at each hazard level. type: array
        :param numGM: the total number of ground motion records at each hazard level. type: array
        '''
            p_pred = norm.cdf(np.log(HazardLevel), loc = np.log(theta[0]), scale = theta[1])
            likelihood = binom.pmf(NumCount, NumGM, p_pred)

            return -np.sum(np.log(likelihood))

        def computeJacobian(theta, HazardLevel, NumCount, NumGM):
            '''
        This Method returns first derivative (Jacobian) of the log-likelihood function. Uses numdifftool package.

        :param theta: An array with median and log-standard deviation values. type: array
        :param hazardLevel: Intensity Measures (IM) used to conduct nonlinear dynamic analysis. type: array
        :param numCount: the count of collapses at each hazard level. type: array
        :param numGM: the total number of ground motion records at each hazard level. type: array
        '''
            return ndt.Jacobian(lambda theta: neg_loglik(theta, HazardLevel, NumCount, NumGM), 
                                full_output = True)(theta)#.ravel()

        def computeHessian(theta, HazardLevel, NumCount, NumGM):
            '''
        This Method returns second derivative(Hessian) of the log-likelihood function. Uses numdifftool package.

        :param theta: An array with median and log-standard deviation values. type: array
        :param hazardLevel: Intensity Measures (IM) used to conduct nonlinear dynamic analysis. type: array
        :param numCount: the count of collapses at each hazard level. type: array
        :param numGM: the total number of ground motion records at each hazard level. type: array
        '''
            return ndt.Hessian(lambda theta: neg_loglik(theta, HazardLevel, NumCount, NumGM))(theta)


        # Square error function
        def squareerror(theta, HazardLevel, NumCount, NumGM):

            p_real = NumCount/NumGM
            p_pred = norm.cdf(np.log(HazardLevel), loc = np.log(theta[0]), scale = np.log(theta[1]))

            return np.sum((p_real - p_pred)**2)


        def lognormfit(HazardLevel, NumCount, NumGM, Method):
            '''
        This method initialized `minimize` optimization module of negative log-likelihood which is equivalent to maximizing the 
        log-likelihood function. 
        
        :param hazardLevel: Intensity Measures (IM) used to conduct nonlinear dynamic analysis. type: array
        :param numCount: the count of collapses at each hazard level. type: array
        :param numGM: the total number of ground motion records at each hazard level. type: array
        :param Method: Loss minimization algorigthm to be used. Options ['MLE', 'SSE']. type: str
        :returns: estimated lognormal distribution parameters
        
        '''

            theta_start = [2,3] # Initial guess, pay attention to initial guess to avoid log(0) and log (1)

            theta = []
            heiss = []
            if Method == 'MLE':
                res = minimize(neg_loglik, theta_start, args = (HazardLevel, NumCount, NumGM), 
                               method = 'Nelder-Mead', options={'disp': False})
            else:
                res = minimize(squareerror, theta_start, args = (HazardLevel, NumCount, NumGM), method = 'Nelder-Mead', 
                               options={'disp': True})


            theta.append(res.x[0])
            theta.append(res.x[1])
            #     heiss.append(res.hess_inv) # hessian inv only available for BFGS solver but needed funcion 
            #     print(heiss)


            return theta # Return the mean and standard deviation
        
        self.theta  = np.array(lognormfit(self.hazardLevel, self.collapseCount, self.numGM, 'MLE'))
        self.fittedProbCollapse = norm.cdf(self.logIM, loc = np.log(self.theta[0]), scale = self.theta[1])
        
    def varianceTaylorSeries(self):
        '''
        This method computes the variances in the parameter estimates using Taylor approximation. The Fisher's Information Matrix is
        utilized. 
        '''
        beta0 = self.GLMmodel.fit.params[0]
        beta1 = self.GLMmodel.fit.params[1]
        
        Var_beta0 = self.GLMmodel.vcov['Intercept'][0]
        Var_beta1 = self.GLMmodel.vcov['logIM'][1]
        Cov_beta0_beta1 = self.GLMmodel.vcov['Intercept'][1]

        firstDerivative_b0 = -np.exp(-beta0/beta1)/beta1
        firstDerivative_b1 = beta0 * np.exp(-beta0/beta1)/ beta1**2
        self.varTheta = Var_beta0*firstDerivative_b0**2 + Var_beta1*firstDerivative_b1**2 \
                    + 2 * Cov_beta0_beta1*firstDerivative_b0 *firstDerivative_b1
        
        self.varBeta = (-1/beta1**2)**2*Var_beta1
        
    def varianceErrorFunction(self):
        '''
        This method utilizes Sympy package to compute the Score and the Hessian which is used to compute the variance-covariance 
        matrix.  
        '''
        ###############################
        ## computing var(theta) 
        ###############################
        temp1 = []
#         hazardLevel = self.hazardLevel
#         theta = self.theta[0]
#         beta = self.theta[1]
        for i in range(len(self.hazardLevel)):
            temp1.append(self.fprime_wrt_x(self.theta[0], self.theta[1], self.hazardLevel[i], 
                                           self.collapseCount[i], self.numGM[i], 2))

        hess_theta = np.sum(temp1)
        ###############################
        ## computing var(beta) 
        ###############################
        temp2 = []
        for i in range(len(self.hazardLevel)):
            temp2.append(self.fprime_wrt_y(self.theta[0], self.theta[1], self.hazardLevel[i], 
                                           self.collapseCount[i], self.numGM[i], 2))

        hess_beta = np.sum(temp2)
        ###############################
        ## computing cov(theta,beta) 
        ###############################
        temp3 = []
        for i in range(len(self.hazardLevel)):
            temp3.append(self.fprime_wrt_xy(self.theta[0], self.theta[1], self.hazardLevel[i], 
                                            self.collapseCount[i], self.numGM[i], 2))

        hess_theta_beta = np.sum(temp3)
        
        
        Hessian_erf = np.array([[hess_theta, hess_theta_beta],[hess_theta_beta, hess_beta]], dtype = np.float)
        self.A = Hessian_erf
        self.vcov_erf = np.linalg.inv(-Hessian_erf)

        self.varTheta_erf = self.vcov_erf[0,0]
        self.varBeta_erf = self.vcov_erf[1,1]
        
        
        
    def scoreErrorFunction(self):
        '''
        This method utilizes Sympy package to compute the Score and the Hessian which is used to compute the variance-covariance 
        matrix.  
        '''
        ###############################
        ## computing f'(theta) 
        ###############################
        temp1 = []
#         hazardLevel = self.hazardLevel
#         theta = self.theta[0]
#         beta = self.theta[1]
        for i in range(len(self.hazardLevel)):
            temp1.append(self.fprime_wrt_x(self.theta[0], self.theta[1], self.hazardLevel[i], 
                                           self.collapseCount[i], self.numGM[i], 1))

        jac_theta = np.sum(temp1)
        jac_theta = np.array(temp1)
        ###############################
        ## computing f'(beta) 
        ###############################
        temp2 = []
        for i in range(len(self.hazardLevel)):
            temp2.append(self.fprime_wrt_y(self.theta[0], self.theta[1], self.hazardLevel[i], 
                                           self.collapseCount[i], self.numGM[i], 1))
            
        jac_beta = np.sum(temp2)
        jac_beta = np.array(temp2)
        temp_score = np.array((jac_theta, jac_beta), dtype = np.float)
        self.score_erf = temp_score@temp_score.T
#         self.score_erf = np.array([jac_theta, jac_beta], dtype = np.float)
        
    def sandwichEstimators(self):
        '''
        This method implements Huber-White's Sandwich estimator. 
        '''
        Ainv = self.vcov_erf
#         score = self.score_erf[:,None]
        self.B = self.score_erf
        self.sandwich = Ainv * self.score_erf * Ainv

        
    def fprime_wrt_x(self, thetaVal, betaVal, hazardLevel, numCount, numGM, numdir):
        '''
        This method returns first derivative of log-likelihood function with respect to median value (theta)

        :param thetaVal: Median Collapse intensity obtained from MLE fit . type: float
        :param betaVal: log-standard deviation obtained from MLE fit. type: float
        :param hazardLevel: Intensity Measures (IM) used to conduct nonlinear dynamic analysis. type: array
        :param numCount: the count of collapses at each hazard level. type: array
        :param numGM: the total number of ground motion records at each hazard level. type: array
        :param numdir: the order of derivative to be computed. type: int 
        '''

        w = hazardLevel 
        k = numCount
        n = numGM
        y = betaVal
        x = sym.Symbol('x')
        f = k * sym.log((1 + sym.erf(sym.log(w/x)/(y * sym.sqrt(2))))/2) + \
            (n-k)* sym.log(1-(1 + sym.erf(sym.log(w/x)/(y * sym.sqrt(2))))/2)
        jac = sym.diff(f, x, numdir).evalf(subs = {x:thetaVal})
        return jac
    
    def fprime_wrt_y(self, thetaVal, betaVal, hazardLevel, numCount, numGM, numdir):
        '''
        This method returns first derivative of log-likelihood function with respect to log-standard deviation value (beta)

        :param thetaVal: Median Collapse intensity obtained from MLE fit . type: float
        :param betaVal: log-standard deviation obtained from MLE fit. type: float
        :param hazardLevel: Intensity Measures (IM) used to conduct nonlinear dynamic analysis. type: array
        :param numCount: the count of collapses at each hazard level. type: array
        :param numGM: the total number of ground motion records at each hazard level. type: array
        :param numdir: the order of derivative to be computed. type: int
        '''

        w = hazardLevel 
        k = numCount
        n = numGM
        x = thetaVal
        y = sym.Symbol('y')
        f = k * sym.log((1 + sym.erf(sym.log(w/x)/(y * sym.sqrt(2))))/2) + \
            (n-k)* sym.log(1-(1 + sym.erf(sym.log(w/x)/(y * sym.sqrt(2))))/2)
        jac = sym.diff(f,y, numdir).evalf(subs = {y:betaVal})
        return jac
    
    def fprime_wrt_xy(self, thetaVal, betaVal, hazardLevel, numCount, numGM,numdir):
        '''
        This method returns first derivative of log-likelihood function with respect to median value (theta) and standard deviation

        :param thetaVal: Median Collapse intensity obtained from MLE fit . type: float
        :param betaVal: log-standard deviation obtained from MLE fit. type: float
        :param hazardLevel: Intensity Measures (IM) used to conduct nonlinear dynamic analysis. type: array
        :param numCount: the count of collapses at each hazard level. type: array
        :param numGM: the total number of ground motion records at each hazard level. type: array
        '''

        w = hazardLevel 
        k = numCount
        n = numGM
        x, y = sym.symbols('x y')
        f = k * sym.log((1 + sym.erf(sym.log(w/x)/(y * sym.sqrt(2))))/2) + \
            (n-k)* sym.log(1-(1 + sym.erf(sym.log(w/x)/(y * sym.sqrt(2))))/2)
        jac = sym.diff(f,x, y).evalf(subs = {x: thetaVal, y:betaVal})
        return jac
    
    
    def plotCollapseFragility(self):
        '''
        Method to plot the collapse fragility curve
        '''
        
        ProbCollapse_IMrange = norm.cdf(np.log(self.IMrange), loc = np.log(self.theta[0]), scale = self.theta[1])
           
        plt.figure(figsize = (10,6))
        plt.plot(self.IMrange, ProbCollapse_IMrange, color = 'red', label = 'GLM Fit w/ Probit Link')
        plt.scatter(self.hazardLevel, self.collapseCount / self.numGM, color = 'green', marker = 's', 
                    label = 'Fraction of Collapse')
        plt.scatter(self.hazardLevel, self.fittedProbCollapse, color = 'black', marker = '*', s = 80,  
                    label = 'Fitted Probability of Collapse')
        
        plt.title('Collapse Fragility Curve')
        plt.xlabel('IM(Sa)')
        plt.ylabel('Probability of Collapse')
        plt.legend()
        plt.grid(linewidth = 0.5)
        
    def plotParamsDispersion(self):
        '''
        Method to plot the dispersion in parameter estimates
        '''  
        
        theta = self.theta[0]
        beta = self.theta[1]
        
        np.random.seed(42)
        sample_theta = np.random.normal(theta, np.sqrt(self.varTheta), 10000)
        sample_beta = np.random.normal(beta, np.sqrt(self.varBeta), 10000)

        fig, (ax1, ax2) = plt.subplots(1,2)
        fig.set_figheight(7)
        fig.set_figwidth(14)
        count, bins, ignored = ax1.hist(sample_theta, 30, density=True, histtype = 'step')
        ax1.plot(bins, 1/(np.sqrt(self.varTheta) * np.sqrt(2 * np.pi)) * np.exp( - (bins - theta)**2 / (2 * self.varTheta) ),
                 linewidth=3, color='r')
        ax1.title.set_text(r'Dispersion in median $\theta$')
        count, bins, ignored = ax2.hist(sample_beta, 30, density=True, histtype = 'step')
        ax2.plot(bins, 1/(np.sqrt(self.varBeta) * np.sqrt(2 * np.pi)) * np.exp( - (bins - beta)**2 / (2 * self.varBeta) ),
                 linewidth=3, color='r')
        # ax2.plot(bins, norm.pdf())
        ax2.title.set_text(r'Dispersion in log-standard deviation $\beta$')
        
        
        
    def MAFC(self, qmleTag = False):
        '''
        Method to estimate the Mean Annual Frequency of Collapse (MAFC) using Reimann's Sum.
        It also estimates the variance around MAFC using Taylor approximation method
        :param qmleTag: Tag to indicate if Sandiwich estimator is to be used. If tag is set to True, it uses sandwich estimator, 
        if set to False, asymptotic covariance matrix is used
        '''
        
        if qmleTag:
            covMat = np.array(self.GLMmodel_Sandwich.vcov)
        else:
            covMat = np.array(self.GLMmodel.vcov)
            
            
        interpolationFunc = CubicSpline(self.hazardLevel, self.collapseRate)
        lambdaRange = interpolationFunc(self.IMrange)
        
        lambdaCollapse_temp = []
        
        for i in range(len(self.IMrange)-1):
    
            midIM = (self.IMrange[i] + self.IMrange[i+1]) / 2
    
            pc_temp = norm.cdf(np.log(midIM), loc = np.log(self.theta[0]), scale = self.theta[1])
            lamC = pc_temp * np.abs(lambdaRange[i] - lambdaRange[i+1]) 
    
            lambdaCollapse_temp.append(lamC)
    
        self.meanLambdaCollapse = np.sum(lambdaCollapse_temp)
        
        
        meanEta = self.GLMmodel.fit.params[0] + self.GLMmodel.fit.params[1]* np.log(self.IMrange)
        varEta = covMat[0,0] + covMat[1,1]*np.log(self.IMrange)**2 + 2*covMat[0,1]*np.log(self.IMrange)
        stdEta = np.sqrt(varEta)
        
        sigmaProbCollapse = norm.pdf(meanEta) * stdEta

        sigmaCollapse = np.zeros((len(self.IMrange), len(self.IMrange)))
        for i in range(len(self.IMrange)-1):
            for j in range (len(self.IMrange) - 1):
                sigmaCollapse[i,j] = np.abs(lambdaRange[i] - lambdaRange[i+1])\
                            * np.abs(lambdaRange[j] - lambdaRange[j+1]) * sigmaProbCollapse[i] * sigmaProbCollapse[j]
        
        self.sigmaLambdac = np.sqrt(sum(sum(sigmaCollapse)))
        return self.sigmaLambdac
        
        
    def getProbCollapse_years(self, numYear): 
        return 1 - np.exp(-numYear * self.meanLambdaCollapse)
        
    

    def simulatedCollapseRateCov(self, cov, numSamples=100, period=50, seed = 42, resamplingFlag = False):
        
        
        lambdaCollapsehist = []
        samplePc_hist = []
        np.random.seed(seed)
        sampleBeta0 = np.random.normal(self.GLMmodel.fit.params[0], size = numSamples)
        sampleBeta1 = np.random.normal(self.GLMmodel.fit.params[1], size = numSamples)
        
        
        for i in range(len(sampleBeta0)):
            ## resampling
            sample_b0 = np.random.choice(sampleBeta0, size = 5)
            sample_b1 = np.random.choice(sampleBeta1, size = 5)
            
            simlambda_c, simProbCol_yrs = self.computeCollapseRateGLM(np.mean(sample_b0), np.mean(sample_b1), period)
            
            lambdaCollapsehist.append(simlambda_c)
            samplePc_hist.append(simProbCol_yrs)
            
        self.varCollapseRate = np.std(lambdaCollapsehist)**2
        self.varProbCollapse = np.std(samplePc_hist)**2
        return lambdaCollapsehist, samplePc_hist


    def computeCollapseRateGLM(self,beta0, beta1, period):
        
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
    

    
    def computeCollapseRate(self, theta, beta, period):
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

            pc_temp = norm.cdf(np.log(midIM), loc = np.log(theta), scale = beta)
            lamC = pc_temp * np.abs(lambdaRange[i] - lambdaRange[i+1]) 

            lambdaCollapse_temp.append(lamC)


        meanLambdaCollapse = np.sum(lambdaCollapse_temp)
        probCollapseGivenYears = 1 - np.exp(-meanLambdaCollapse*period)
        return meanLambdaCollapse, probCollapseGivenYears
   