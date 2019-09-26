# Suitability Analysis for Relocation

## Installation Instructions
Here is a quick overview of how to install and work with this code

1. Install ArcGIS Pro 2.3+ (version needed for advanced conda package management)
2. Clone this repository to your desired location
3. Copy FloodMitigation/local_settings_template.py to local_settings.py and configure parameters in local_settings.py as needed.
4. Set up a conda environment within ArcGIS Pro. [ArcGIS' documentation](https://pro.arcgis.com/en/pro-app/arcpy/get-started/installing-python-for-arcgis-pro.htm)
 includes the best way to handle this, but in brief:
    1. Open ArcGIS Pro
    2. Go to Settings, then switch to the Python tab
    3. Clone the default conda environment
    4. Activate the new environment and restart ArcGIS Pro
5. Install dependencies within the new conda environment:
    1. `Django`
    2. `scikit-learn`
    3. `arrow`
6. Create a new scratch geodatabase (may need to happen by default - Nick to flesh out)
7. Run `python manage.py migrate` from the command line with the appropriate conda environment activated (or use the path
 to `propy` instead of calling `python`). This will create and populate the local data structures.
8. Can now load data and run the model (see functions in `relocation/management/load.py`)


## Installation Instructions for ArcGIS Pro 1.x

1. Install ArcGis Pro, log in, and upgrade to version 1.3

2. Clone the repository to a desired location.

4. You need to obtain a secrets.py and local_settings.py from Nick and copy it into the FloodMitigation folder

5. Set up a conda environment. Instructions are at: http://help.watershed.ucdavis.edu/setting-up-your-own-conda-env-with-arcgis-pro-1-3-switching-from-virtualenv/

6. In the installation folder run act.bat to switch to the created conda environment and then run install_dependencies.bat. The directories used are installation defaults and need to be changed if you installed ArcGis Pro elsewhere.

7. Create a folder in the project folder called "scratch" and create a gdb in ArcGis in that location

8. You can now run the project. You can do this by:
a. Activating the virtual environment by running: "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\activate.bat" myenv
b. Running python manage.py runserver
c. Opening a browser and going to 127.0.0.1:8000

Note: Some packages may install into C:\Program Files\ArcGIS\Pro\bin\Python\Lib\site-packages instead of your conda environment. If you are missing dependencies copy the module folder from that location into your conda environment.
