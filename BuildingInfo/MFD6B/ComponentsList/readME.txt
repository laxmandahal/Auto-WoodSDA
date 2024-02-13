Date created: 11/19/2022


Pelicun v2.6 requires configuration file (or performance models) as a JSON file. The components_list_marginals.csv file in this folder is one of the input files required to create the performance model. Refer to Pelicun's documentation page at https://nheri-simcenter.github.io/pelicun/common/user_manual/usage/pelicun/config.html for a performance model template.

-- Median quantity needs to be updated.



In Pelicun v3.0+, components input is a .csv file itself. However, in woodSDA, Pelicun v2.6 is used to be consistent with the version Dustin is using for ATC-138

Last Updated: 11/22/2022
Component D5012.013d was incomplete. Added 2.5g as median edp and 0.4 as beta

Last Updated: 10/09/2023
--> Updated median quantities of the components and added roof tiles to the components list. Also, updated FEMA IDs for light-frame walls to reflect the new designs. Some of the median capacities of the component fragility in the FEMA DB seemed way too low (less than 0.02% drift). Now the archetypes higher than 2 stories use the component with highest median capacity. 

--> Updated the locations the components are applicable to
--> Also updated direction of the components
--> Added total (net) component quantity as well as it appears pelicun 3.0+ required the net components. Need to check with Adam or check the code that the quantities are normalized internally. It seems so based on the example code but a confirmation from Adam would be nice