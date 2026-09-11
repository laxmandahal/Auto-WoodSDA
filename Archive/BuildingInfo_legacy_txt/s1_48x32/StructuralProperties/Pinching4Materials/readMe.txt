This folder essentially is the pinching4 parameters database for single- and multi-family modern woodframe buildings. The database is assembled	as a part of the WoodSDA-3D automation computational platform. The Pinching4 material hysteresis model is a 22-parameter model. Each of the text file correspond to one of the 22-parameters. Note, there are only 15 parameters used. The parameters not included in this databased is by default set to 0, when creating OpenSees models.

Almost all of the parameters are calibrated with a few exceptions where values directly from PEER CEA project on cripple wall buildings are used. 

Units: ed1-4: inches
       f1-4: lbs/in

Author: Laxman Dahal
Date: 07/16/2021
Calibrated parameters for line items 1 through 16

UPDATE: 02/05/2022
1) Calibrated parameters for Non-structural Gypsum, Stucco, Siding, and Max-Gypsum directly using SAWS parameters from ATC-116 or FEMA P-2139-2 document. 

2) Also added pinching4 parameters for GWB, HWS, Stucco, Plaster on Lath and Stucco+ GWB from PEER-CEA draft reports. If CEA had two springs, backbone value was a combination of the two springs, and cyclic parameters were taken as the average of the two springs. 

3) There are total of 23 shear walls, interior/exterior walls in the database