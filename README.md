# WoodSDA 
An end-to-end computational tool to automate seismic design, analysis, and loss assessment of woodframe buildings

### Implementation Details
WoodSDA tool is composed of four modules: 1) Design Module, 2) Ground motion selection module, 3) Modeling and analysis module, and 4) Loss assessment module. Except for ground motion selection module (which was developed by former BRG member, Mehrdad), the folder "Codes" contains codes for design, modeling, and loss assessment modules.

### Running the codes
 - **Step 1**: Prepare the building info for the building archetypes that you want to run woodSDA for. There's an example .xlsx file that might be helpful to create required input .txt files in "BuildingInfo" folder
 - **Step 2**: Select Ground motion records and put it in "GM_sets" subfolder within "BuildingModels" folder
 - **Step 3**: Run woodSDA_driver.ipynb file to run end-to-end workflow

