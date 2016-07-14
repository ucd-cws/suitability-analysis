Installation Instructions

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