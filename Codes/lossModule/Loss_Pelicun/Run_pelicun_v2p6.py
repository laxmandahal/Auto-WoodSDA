# -*- coding: utf-8 -*-
#
# Copyright (c) 2018 Leland Stanford Junior University
# Copyright (c) 2018 The Regents of the University of California
#
# This file is part of pelicun.
#
# Contributors:
# Adam Zsarnóczay
# Joanna J. Zou
# Last edited by: Laxman Dahal

from time import gmtime, strftime
from pathlib import Path
def log_msg(msg):

	formatted_msg = '{} {}'.format(strftime('%Y-%m-%dT%H:%M:%SZ', gmtime()), msg)

	print(formatted_msg)

log_msg('First line of DL_calculation')

import sys, os, json, ntpath, posixpath, argparse
import numpy as np
import pandas as pd

from scipy.stats import norm, binom
from scipy.optimize import minimize

idx = pd.IndexSlice

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from pelicun_2_6.base import str2bool
from pelicun_2_6.control import FEMA_P58_Assessment, HAZUS_Assessment
from pelicun_2_6.auto import auto_populate

# START temporary functions ----

# FUNCTION: neg_log_likelihood -------------------------------------------------
# objective function for evaluating negative log likelihood of observing the given collapses
# ------------------------------------------------------------------------------

def neg_log_likelihood(params, IM, num_records, num_collapses):
	theta = params[0]
	beta = params[1]

	log_IM = [np.log(m) for m in IM]
	p = norm.cdf(log_IM, loc=theta, scale=beta)

	# likelihood of observing num_collapse(i) collapses, given num_records observations, using the current parameter estimates
	likelihood = np.maximum(binom.pmf(num_collapses, num_records, p),
							np.nextafter(0,1))

	neg_loglik = -np.sum(np.log(likelihood))

	return neg_loglik

# FUNCTION: lognormal_MLE ------------------------------------------------------
# returns maximum likelihood estimation (MLE) of lognormal fragility function parameters
# ------------------------------------------------------------------------------
# algorithm obtained from Baker, J. W. (2015). “Efficient analytical fragility function fitting
# using dynamic structural analysis.” Earthquake Spectra, 31(1), 579-599.

def lognormal_MLE(IM,num_records,num_collapses):
	# initial guess for parameters
	params0 = [np.log(1.0), 0.4]
	#params = minimize(neg_log_likelihood, params0, args=(IM, num_records, num_collapses), method='Nelder-Mead',
    #					options={'maxfev': 400*2,
	#						 'adaptive': True})

	params = minimize(neg_log_likelihood, params0, args=(IM, num_records, num_collapses), bounds=((None, None), (1e-10, None)))
	theta = np.exp(params.x[0])
	beta = params.x[1]

	return theta, beta

# FUNCTION: update_collapsep ---------------------------------------------------
# creates copy of BIM.json for each IM with updated collapse probability
# ------------------------------------------------------------------------------

def update_collapsep(BIMfile, RPi, theta, beta, num_collapses):
	with open(BIMfile, 'r') as f:
		BIM = json.load(f)
		Pcol = norm.cdf(np.log(num_collapses/theta)/beta)
		BIM['DamageAndLoss']['BuildingResponse']['CollapseProbability'] = Pcol
	f.close()

	outfilename = 'BIM_{}.json'.format(RPi)
	with open(outfilename, 'w') as g:
		json.dump(BIM,g,indent=4)

	return outfilename

# END temporary functions ----

def run_pelicun(DL_input_path, EDP_input_path,
	DL_method, realization_count, EDP_file, DM_file, DV_file,
	output_path=None, detailed_results=True, coupled_EDP=False,
	log_file=True, event_time=None, ground_failure=False,
	auto_script_path=None):

	DL_input_path = os.path.abspath(DL_input_path) # BIM file
	EDP_input_path = os.path.abspath(EDP_input_path) # dakotaTab

	# If the output dir was not specified, results are saved in the directory of
	# the input file.
	if output_path is None:
		output_path = ntpath.dirname(DL_input_path)

	# delete output files from previous runs
	files = os.listdir(output_path)
	for filename in files:
		if (filename[-3:] == 'csv') and (
			('DL_summary' in filename) or
			('DMG' in filename) or
			('DV_' in filename) or
			('EDP' in filename)
			):
			try:
				os.remove(posixpath.join(output_path, filename))
			except:
				pass

	# If the event file is specified, we expect a multi-stripe analysis...
	try:
		# Collect stripe and rate information for every event
		with open(DL_input_path, 'r') as f:
			event_list = json.load(f)['Events'][0]

		df_event = pd.DataFrame(columns=['name', 'stripe', 'rate', 'IM'],
								index=np.arange(len(event_list)))

		for evt_i, event in enumerate(event_list):
			df_event.iloc[evt_i] = [event['name'], event['stripe'], event['rate'], event['IM']]

		# Create a separate EDP input for each stripe
		EDP_input_full = pd.read_csv(EDP_input_path, sep='\s+', header=0,
									 index_col=0)

		# EDP_input_full.to_csv(EDP_input_path[:-4]+'_1.out', sep=' ')

		stripes = df_event['stripe'].unique()
		EDP_files = []
		IM_list = []
		num_events = []
		num_collapses = []
		for stripe in stripes:
			events = df_event[df_event['stripe']==stripe]['name'].values

			EDP_input = EDP_input_full[EDP_input_full['MultipleEvent'].isin(events)]

			EDP_files.append(EDP_input_path[:-4]+'_{}.out'.format(stripe))

			EDP_input.to_csv(EDP_files[-1], sep=' ')

			IM_list.append(df_event[df_event['stripe']==stripe]['IM'].values[0])

			# record number of collapses and number of events per stripe
			PID_columns = [col for col in list(EDP_input) if 'PID' in col] # list of column headers with PID
			num_events.append(EDP_input.shape[0])
			count = 0
			for row in range(num_events[-1]):
				print(row)
				for col in PID_columns:
					if EDP_input.iloc[row][col] >= 0.20: # TODO: PID collapse limit as argument
						count += 1
						break
			num_collapses.append(count)

		# fit lognormal distribution to all points by maximum likelihood estimation (MLE)
		theta, beta = lognormal_MLE(IM_list, num_events, num_collapses)
		beta_adj = np.sqrt(beta**2 + 0.35**2) # TODO: adjust dispersion by 0.35 to account for modeling uncertainty
		print("theta: " + str(theta))
		print("beta_adj: " + str(beta_adj))

		# write BIM file with new probability of collapse for each IM
		DL_files = []
		for i in range(len(stripes)):
			DL_input_stripe = update_collapsep(DL_input_path, stripes[i], theta, beta_adj, IM_list[i])
			DL_files.append(DL_input_stripe)

	except: # run analysis for single IM
		stripes = [1]
		EDP_files = [EDP_input_path]
		DL_files = [DL_input_path]

	# run the analysis and save results separately for each stripe
	#print(stripes, EDP_files)

	for s_i, stripe in enumerate(stripes):

		DL_input_path = DL_files[s_i]

		# read the type of assessment from the DL input file
		with open(DL_input_path, 'r') as f:
			DL_input = json.load(f)

		# check if the DL input file has information about the loss model
		if 'DamageAndLoss' in DL_input:
			pass
		else:
			# if the loss model is not defined, give a warning
			print('WARNING No loss model defined in the BIM file. Trying to auto-populate.')

			EDP_input_path = EDP_files[s_i]

			# and try to auto-populate the loss model using the BIM information
			DL_input, DL_input_path = auto_populate(DL_input_path, EDP_input_path,
													DL_method, realization_count,
													coupled_EDP, event_time,
													ground_failure,
													auto_script_path)


		DL_method = DL_input['DamageAndLoss']['_method']

		stripe_str = '' if len(stripes) == 1 else str(stripe)+'_'

		if DL_method == 'FEMA P58':
			A = FEMA_P58_Assessment(log_file=log_file)
		elif DL_method in ['HAZUS MH EQ', 'HAZUS MH', 'HAZUS MH EQ IM']:
			A = HAZUS_Assessment(hazard = 'EQ', log_file=log_file)
		elif DL_method == 'HAZUS MH HU':
			A = HAZUS_Assessment(hazard = 'HU', log_file=log_file)
		elif DL_method == 'HAZUS MH FL':
			A = HAZUS_Assessment(hazard = 'FL', log_file=log_file)

		A.read_inputs(DL_input_path, EDP_files[s_i], verbose=False) # make DL inputs into array of all BIM files

		A.define_random_variables()

		A.define_loss_model()

		A.calculate_damage()

		A.calculate_losses()

		A.aggregate_results()

		A.save_outputs(output_path, EDP_file, DM_file, DV_file, stripe_str,
					   detailed_results=detailed_results)

	return 0


if __name__ == '__main__':
	ID = 's4_96x48_High_Stucco_GWB'
	baseDir = r'/Users/laxmandahal/Desktop/UCLA/Phd/Research/SurrogateModeling/DGP/woodSDA'
	DL_input_path = os.path.join(baseDir, *['BuildingModels', ID, 'LossAnalysis', 'PelicunInput', 'Loss_model_config.json'])
	edp_input_path = os.path.join(baseDir, *['Results', ID, 'demands_2story.csv'])
	outputDir = os.path.join(baseDir, *['BuildingModels', ID, 'LossAnalysis', 'PelicunOutput'])
	Path(outputDir).mkdir(parents=True, exist_ok=True)
	run_pelicun(DL_input_path, edp_input_path,
	DL_method="FEMA P58", realization_count=None, EDP_file='EDP.csv', DM_file='DM.csv', DV_file='DV.csv',
	output_path=outputDir, detailed_results=True, coupled_EDP=False,
	log_file=True, event_time=None, ground_failure=False,
	auto_script_path=None)

