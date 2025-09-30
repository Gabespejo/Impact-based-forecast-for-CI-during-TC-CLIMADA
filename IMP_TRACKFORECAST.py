"""
This file is part of CLIMADA under development.

Copyright (C) 2017 ETH Zurich, CLIMADA contributors listed in AUTHORS.

CLIMADA is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free
Software Foundation, version 3.

CLIMADA is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with CLIMADA. If not, see <https://www.gnu.org/licenses/>.

---

TRACKS FROM TIGGE DATASET for the 51 ensemble members of ECMWF
"""

# your_module/IMP_TRACKFORECAST.py

from climada_petals.hazard import TCForecast
import logging
from datetime import datetime, timedelta
import os
# Import necessary modules
import numpy as np
from climada.entity.exposures.base import Exposures
from climada.util import lines_polys_handler as u_lp

#####################################################################################
## This one is to fetch tracks but in format bufr4

from datetime import datetime, timedelta
import logging
import os

logging.getLogger('climada.hazard.tc_tracks_forecast').setLevel(logging.WARNING)

def fetch_multiple_ecmwf_data_bufr4(base_folder, start_date, end_date, event_name):
    current_date = start_date
    forecast_variables = {}  # Dictionary to store forecast variables

    while current_date <= end_date:
        for utc_hour in [0,12]:  # Only check 0 UTC and 12 UTC
            date_folder = current_date.replace(hour=utc_hour, minute=0, second=0).strftime("%Y%m%d%H%M%S")
            folder_path = os.path.join(base_folder, date_folder)

            if os.path.exists(folder_path):
                forecast = TCForecast()
                files_to_fetch = []
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if event_name in file:
                            files_to_fetch.append(os.path.join(root, file))

                if files_to_fetch:
                    print(f"Fetching data for {date_folder}")
                    forecast.fetch_ecmwf(files=files_to_fetch)
                    variable_name = f"{event_name}_{date_folder}"
                    forecast_variables[variable_name] = forecast
                else:
                    print(f"No data found for {date_folder}")
            else:
                print(f"Folder not found: {date_folder}")

        current_date += timedelta(days=1)

    return forecast_variables


# Set logger level to suppress unnecessary warnings
logging.getLogger('climada.hazard.tc_tracks_forecast').setLevel(logging.WARNING)

class DebugTCForecast(TCForecast):
    @classmethod
    def read_cxml(cls, cxml_path: str, xsl_path: str=None):
        print(f"Reading CXML file: {cxml_path}")
        # Call the original method to read the file and create an instance
        instance = super().read_cxml(cxml_path=cxml_path, xsl_path=xsl_path)
        # Print the initial data for debugging purposes
        print(f"Initial parsed data contains {len(instance.data)} tracks.")
        return instance

def fetch_multiple_ecmwf_data(base_folder, start_date, end_date, event_name):
    current_date = start_date
    forecast_variables = {}  # Dictionary to store forecast variables

    while current_date <= end_date:
        for utc_hour in [0, 12]:  # Only check 0 UTC and 12 UTC
            date_folder = current_date.replace(hour=utc_hour, minute=0, second=0).strftime("%Y%m%d%H%M%S")
            folder_path = os.path.join(base_folder, date_folder)

            if os.path.exists(folder_path):
                files_to_fetch = []
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if file.endswith('.xml'):  # Assuming XML files
                            files_to_fetch.append(os.path.join(root, file))

                if files_to_fetch:
                    print(f"Fetching data for {date_folder}")
                    for file_path in files_to_fetch:
                        forecast = DebugTCForecast.read_cxml(cxml_path=file_path)
                        
                        # Apply subsetting based on event_name and ensemble members
                        try:
                            print(f"Applying subsetting for event '{event_name}' and ensemble members.")
                            tc_name_data = forecast.subset({'name': event_name}).subset({'is_ensemble': True})
                            if tc_name_data.data:
                                variable_name = f"{event_name}_{date_folder}"
                                forecast_variables[variable_name] = tc_name_data
                            else:
                                print(f"No ensemble data found for event '{event_name}' in {date_folder}")
                        except Exception as e:
                            print(f"Error during subsetting: {e}")
                else:
                    print(f"No data found for {date_folder}")
            else:
                print(f"Folder not found: {date_folder}")

        current_date += timedelta(days=1)

    return forecast_variables

# Define a function to determine the level based on the criteria
# Suppose you have a GeoDataFrame named 'gdf' with columns 'amenity', 'building', 'healthcare', 'healthcare__hospital', 'healthcare__clinic', 'healthcare__doctor'

# Define a function to determine the level based on the criteria
def determine_level(row):
    if row['amenity'] == 'hospital':
        return 4
    elif row['amenity'] == 'clinic':
        return 2
    elif row['amenity'] == 'doctors':
        return 1
    elif row['building'] == 'hospital':
        return 4
    elif row['building'] == 'clinic':
        return 2
    elif row['building'] == 'doctor':
        return 1
    elif row['healthcare'] == 'hospital':
        return 4
    elif row['healthcare'] == 'clinic':
        return 2
    elif row['healthcare'] == 'doctor':
        return 1
    elif row['healthcare__hospital']:
        return 4
    elif row['healthcare__clinic']:
        return 2
    elif row['healthcare__doctor']:
        return 1
    else:
        return None
    
## FUNCTION TO CLEAN THE ROWS AS THAT HAS NAN IN THE NAME 
# Function to remove rows with NaN in the 'name' column
def remove_rows_with_nan(gdf):
    # Use dropna with subset parameter
    gdf_cleaned = gdf.dropna(subset=['name'])
    return gdf_cleaned

## Cleaning again the exposures

### CLEANING FOR MOZAMBIQUE VIA THE FUNCTION 
def determine_level_for_MOZ(row):
    name = str(row['name']).lower()  # Convert name to lowercase for case-insensitive matching

    if 'posto' in name or 'saude' in name:
        return 1
    elif 'rural' in name and 'hospital rural' not in name:
        return 1
    elif 'hospital rural' in name or 'distrital' in name:
        return 2
    elif 'provincial' in name:
        return 3
    elif 'central' in name:
        return 4
    else:
        return round(row['levels']) if not pd.isna(row['levels']) else None
    
### 
from climada.entity.impact_funcs.trop_cyclone import ImpactFunc

class ImpFuncsCIWindMoz():
    
    def __init__(self):
        self.tag = 'TC'
        self.health_Eberenz    = self.health_Eberenz()
        self.health_deltares =  self.health_deltares()
        self.cat1    = self.cat1()
        self.cat2 =  self.cat2()
        self.cat3 = self.cat3()
        self.cat4 = self.cat4()
    
    def health_Eberenz(self):
        from climada.entity.impact_funcs.trop_cyclone import ImpfSetTropCyclone
        impf_eberenz_TC = ImpfSetTropCyclone.from_calibrated_regional_ImpfSet()
        CI_wind_eberenz = ImpactFunc()
        CI_wind_eberenz = impf_eberenz_TC.get_func()['TC'][5]
        CI_wind_eberenz.name = 'Ebenrenz et.al (SI)'
        CI_wind_eberenz.id = 1
        CI_wind_eberenz.check()
        return CI_wind_eberenz
    
    def health_deltares(self):
        impf_deltares = ImpactFunc()
        impf_deltares.id = 2
        impf_deltares.haz_type = 'TC'
        impf_deltares.name = 'Deltares'
        impf_deltares.intensity_unit = 'm/s'
        impf_deltares.intensity = np.array([0,12, 18, 20, 40, 50, 60, 70, 90,100,120])
        impf_deltares.mdd = np.array([0, 0, 0.03, 0.3, 0.5, 0.6, 0.61, 0.61, 0.61,0.61,0.61])
        impf_deltares.paa = np.ones(impf_deltares.intensity.shape)
        impf_deltares.check()
        return impf_deltares
    
    def cat1 (self):
        impf_cat1 = ImpactFunc()
        impf_cat1.id = 3
        impf_cat1.haz_type = 'TC'
        impf_cat1.name = 'Category 1'
        impf_cat1.intensity_unit = 'm/s'
        impf_cat1.intensity = np.array([0, 17, 32, 33, 50, 100, 120]) 
        impf_cat1.mdd = np.array([0,0, 0, 1,  1,   1,  1])
        impf_cat1.paa = np.ones(impf_cat1.intensity.shape)
        impf_cat1.check()
        return impf_cat1
    
    def cat2 (self):
        impf_cat2 = ImpactFunc()
        impf_cat2.id = 4
        impf_cat2.haz_type = 'TC'
        impf_cat2.name = 'Category 2'
        impf_cat2.intensity_unit = 'm/s'
        impf_cat2.intensity = np.array([0,17,33,42,43,50,100,120])
        impf_cat2.mdd = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        impf_cat2.paa = np.ones(impf_cat2.intensity.shape)
        impf_cat2.check()
        return impf_cat2
    
    def cat3 (self):
        impf_cat3 = ImpactFunc()
        impf_cat3.id = 5
        impf_cat3.haz_type = 'TC'
        impf_cat3.name = 'Category 3'
        impf_cat3.intensity_unit = 'm/s'
        impf_cat3.intensity = np.array([0,17,33,43,49,50,100,120])
        impf_cat3.mdd = np.array([0, 0, 0, 0, 0, 1, 1, 1])
        impf_cat3.paa = np.ones(impf_cat3.intensity.shape)
        impf_cat3.check()
        return impf_cat3
    def cat4 (self):
        impf_cat4 = ImpactFunc()
        impf_cat4.id = 6
        impf_cat4.haz_type = 'TC'
        impf_cat4.name = 'Category 4'
        impf_cat4.intensity_unit = 'm/s'
        impf_cat4.intensity = np.array([0,17,33,43,50,57,58,100,120])
        impf_cat4.mdd = np.array([0, 0, 0, 0, 0, 0, 1, 1, 1])
        impf_cat4.paa = np.ones(impf_cat4.intensity.shape)
        impf_cat4.check()
        return impf_cat4


## Exposure 

def exposure_from_points(gdf, impf_dict):
    # TODO: check why 'FL' tag not taken when read in raster flood file
    exp_pnt = Exposures(gdf)
    #exp_pnt.gdf[f'impf_FL'] = getattr(ImpFuncsCIFloodMoz(), impf_dict['FL']).id
    exp_pnt.gdf['impf_TC'] = getattr(ImpFuncsCIWindMoz(), impf_dict['TC']).id
    exp_pnt.gdf['value'] = 1
    exp_pnt.set_lat_lon()
    exp_pnt.check()
    return exp_pnt  

def exposure_from_points_with_value(path_worldpop_cntry, impf_dict):
    # TODO: check why 'FL' tag not taken when read in raster flood file
    exp_pnt = Exposures.from_raster(path_worldpop_cntry)
    exp_pnt.gdf.rename(columns={'value': 'people'}, inplace=True)
    #exp_pnt.gdf[f'impf_FL'] = getattr(ImpFuncsCIFloodMoz(), impf_dict['FL']).id
    exp_pnt.gdf['impf_TC'] = getattr(ImpFuncsCIWindMoz(), impf_dict['TC']).id
    exp_pnt.gdf['value'] = 1
    exp_pnt.set_geometry_points()
    exp_pnt.gdf['latitude'] = exp_pnt.gdf.geometry.y
    exp_pnt.gdf['longitude'] = exp_pnt.gdf.geometry.x
    exp_pnt.check()
    return exp_pnt

def exposure_from_points_pp(path_worldpop_cntry, impf_dict):
    # TODO: check why 'FL' tag not taken when read in raster flood file
    exp_pnt = Exposures.from_raster(path_worldpop_cntry)
    #exp_pnt.gdf.rename(columns={'value': 'people'}, inplace=True)
    #exp_pnt.gdf[f'impf_FL'] = getattr(ImpFuncsCIFloodMoz(), impf_dict['FL']).id
    exp_pnt.gdf['impf_TC'] = getattr(ImpFuncsCIWindMoz(), impf_dict['TC']).id
    #exp_pnt.gdf['value'] = 1
    exp_pnt.set_geometry_points()
    exp_pnt.gdf['latitude'] = exp_pnt.gdf.geometry.y
    exp_pnt.gdf['longitude'] = exp_pnt.gdf.geometry.x
    exp_pnt.check()
    return exp_pnt

def exposure_from_lines(gdf, impf_dict, res, 
                        disagg_met=u_lp.DisaggMethod.FIX, disagg_val=None):
    exp_line = Exposures(gdf)
    if not disagg_val:
        disagg_val = res
    exp_pnt = u_lp.exp_geom_to_pnt(exp_line, res=res, to_meters=True, 
                                   disagg_met=disagg_met, disagg_val=disagg_val)  
    #exp_pnt.gdf[f'impf_FL'] = getattr(ImpFuncsCIFloodMoz(), impf_dict['FL']).id
    exp_pnt.gdf['impf_TC'] = getattr(ImpFuncsCIWindMoz(), impf_dict['TC']).id
    exp_pnt.set_lat_lon()
    exp_pnt.check() 
    return exp_pnt

############
## Exposures for dictionaries 
import re

def create_exp_dict(local_vars):
    exp_dict = {
        name: var
        for name, var in local_vars.items()
        if (name.startswith('exp_h') or name.startswith('exp_pp') or name.startswith('exp_ed') or name.startswith('exp_rd'))
        and name.endswith('_MOZ')
        and any(char.isdigit() for char in name)
    }

    sorted_keys = sorted(exp_dict.keys(), key=lambda x: (x.split('_')[0], int(re.search(r'\d+', x).group())))
    return {key: exp_dict[key] for key in sorted_keys}

######
#Impact calculation in impfset
from climada.entity.impact_funcs.impact_func_set import ImpactFuncSet
def make_impfset(imp_class):
    impfset = ImpactFuncSet()
    for attribute in set(imp_class.__dict__.keys()).difference({'tag'}):
        impfset.append(getattr(imp_class, attribute))
    return impfset

##########
## CALCULATING THE MEAN IMPACT BY EXPOSURE
def calc_mean_for_impdict(impact_dict):
    """
    Given a dictionary of impact objects, calculate the mean impact for all tracks.
    
    Parameters:
        impact_dict (dict): A dictionary where keys are track names and 
                            values are Impact objects.
    
    Returns:
        mean_impacts (dict): A dictionary where keys are track names and values
                             are numpy arrays representing the mean impacts.
    """
    mean_impacts = {}
    
    for track_name, imp_obj in impact_dict.items():
        # Check if the impact object is valid
        if imp_obj is None:
            raise ValueError(f"No impact object found for track {track_name}")
        
        # Calculate the mean
        mean = imp_obj.imp_mat.mean(axis=0)
        mean_imp = np.ravel(mean).flatten()
        
        # Store the mean impact in the dictionary
        mean_impacts[track_name] = mean_imp
    
    return mean_impacts

############ 

def calc_imp_overallexp (impact_dict):
    """
    Given a dictionary of impact objects, calculate the total impact over all the exposures, for every ensemble member
    
    Parameters:
        impact_dict (dict): A dictionary where keys are track names and 
                            values are Impact objects.
    
    Returns:
        total_impacts (dict): A dictionary where keys are track names and values
                             are numpy arrays representing the total impacts.
    """
    total_impacts = {}
    
    for track_name, imp_obj in impact_dict.items():
        # Check if the impact object is valid
        if imp_obj is None:
            raise ValueError(f"No impact object found for track {track_name}")
        
        # Calculate the mean
        total = imp_obj.imp_mat.sum(axis=1)
        total_imp = np.ravel(total).flatten()
        
        # Store the mean impact in the dictionary
        total_impacts[track_name] = total_imp
    
    return total_impacts

### Create and check exposures 

def create_and_check_exposures(dataframe):
    ''' Convert the joined_dfs dataframes into exposures. This dataframe contains 
        exposures plus the impact mean values per day, useful for computation. 
    ''' 
    # Create a CLIMADA Exposures instance from the given DataFrame
    exp = Exposures(dataframe)
    # Set geometry attribute (shapely Points) from GeoDataFrame using latitude and longitude
    exp.set_geometry_points()
    # Apply the check() method to ensure data consistency
    exp.check()
    return exp  # Return the exp instance
######################################

def ext_col_categories(exp_instance, date_forecast):
    try:
        #print("Checking columns in exp_instance.gdf:", exp_instance.gdf.columns)

        # Extract latitude and longitude from geometry
        exp_instance.gdf['latitude'] = exp_instance.gdf.geometry.y
        exp_instance.gdf['longitude'] = exp_instance.gdf.geometry.x

        matching_columns = [col for col in exp_instance.gdf.columns if col.endswith(date_forecast)]
        if not matching_columns:
            print(f"No column ending with {date_forecast} found.")
            return None, None

        combined_data = pd.DataFrame()
        for impact_column in matching_columns:
            impact_data = exp_instance.gdf[['latitude', 'longitude', impact_column]].copy()
            impact_data.rename(columns={impact_column: 'impact'}, inplace=True)
            combined_data = pd.concat([combined_data, impact_data])

        combined_data.drop_duplicates(subset=['latitude', 'longitude'], inplace=True)
        #print("Columns in combined_impact_data:", combined_data.columns)

        levels = exp_instance.gdf['levels'] if 'levels' in exp_instance.gdf.columns else None

    except KeyError as ke:
        #print(f"Error: {ke}. Could not extract data. Check column names and data structure.")
        return None, None
    
    return combined_data, levels
import pandas as pd
from datetime import datetime

#######################################################################################################

def extract_points_to_plot(exposures_dict, exp_key, date_forecast, event_date):
    try:
        dt_forecast = datetime.strptime(date_forecast, "%Y%m%d%H%M%S")
        dt_event = datetime.strptime(event_date, "%Y%m%d%H%M%S")
        lead_time = (dt_event - dt_forecast).days
        if lead_time < 0:
            print(f"Warning: The event date {event_date} is earlier than the forecast date {date_forecast}.")
        elif lead_time == 0:
            print("Note: The event date and forecast date are the same.")
        else:
            print(f"Note: Calculating with lead time of {lead_time} days.")

        exp_instance = exposures_dict[exp_key]
        combined_impact_data, exp_levels = ext_col_categories(exp_instance, date_forecast)

        # Initialize as None in case of errors
        exp_lon, exp_lat, exp_impact, exp_level_data = None, None, None, None

        if combined_impact_data is not None:
            #print("Columns in combined_impact_data:", combined_impact_data.columns)
            
            if 'latitude' in combined_impact_data.columns and 'longitude' in combined_impact_data.columns:
                exp_impact = combined_impact_data[['impact', 'latitude', 'longitude']]
                exp_lon = combined_impact_data['longitude']
                exp_lat = combined_impact_data['latitude']
            else:
                print("Error: 'latitude' or 'longitude' column missing in combined_impact_data.")

        if exp_levels is not None:
            #print("Columns in exp_instance.gdf:", exp_instance.gdf.columns)

            if 'latitude' in exp_instance.gdf.columns and 'longitude' in exp_instance.gdf.columns:
                exp_level_data = exp_instance.gdf[['levels', 'latitude', 'longitude']]
            else:
                print("Error: 'latitude' or 'longitude' column missing in exp_instance.gdf.")

    except ValueError as ve:
        print(f"Error: {ve}. Ensure date_forecast and event_date are correctly formatted.")
        return None
    except KeyError as ke:
        print(f"Error: {ke}. Key not found in exposures_dict.")
        return None

    return {
        'longitude': exp_lon,
        'latitude': exp_lat,
        'impact_data': exp_impact,
        'level_data': exp_level_data,
        'lead_time': lead_time
    }
############
## PLOT EXPOSURES 

SAFFIR_SIM_CAT = [34, 64, 83, 96, 113, 137, 1000]
import cartopy.crs as ccrs
import climada.util.plot as u_plot
import matplotlib.pyplot as plt
import climada.util.coordinates as u_coord
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.collections import LineCollection
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D
from climada.util.constants import ONE_LAT_KM, DEF_CRS, CMAP_EXPOSURES
# Define marker shapes for different levels
level_markers = {1: 'o', 2: 's', 3: '^', 4: 'D'}
# Define a dictionary to map levels to their alpha, edgecolor, and facecolor settings
level_style = {
    1: {'alpha': 0.7, 'edgecolor': 'indigo', 'facecolor': 'indigo', 'size': 5},
    2: {'alpha': 0.7, 'edgecolor': 'mediumslateblue', 'facecolor': 'mediumslateblue', 'size': 10},
    3: {'alpha': 0.7, 'edgecolor': 'darkmagenta', 'facecolor': 'darkmagenta', 'size': 30},  # Darker for level 3
    4: {'alpha': 0.7, 'edgecolor': 'mediumvioletred', 'facecolor': 'mediumvioletred', 'size': 40},    # Darker for level 4
}


def plot_exposure(exp_lon, exp_lat, exp_value, exp_level, tc_ob, figure_filename, gadm_cntry):    
    extent = (exp_lon.min(), exp_lon.max(), exp_lat.min(), exp_lat.max())
    proj = ccrs.PlateCarree()
    
    _, axis, fontsize = u_plot.make_map(proj=proj, figsize=(8, 8), adapt_fontsize=True)
    axis.set_extent(extent, crs=ccrs.PlateCarree())
    u_plot.add_shapes(axis)
    
    # Iterate through levels and markers
    for level, marker in level_markers.items():
        # Filter data for the current level
        level_data = exp_level[exp_level['levels'] == level]
        
        # Get the style and size settings for the current level
        style = level_style.get(level, {'alpha': 0.1, 'edgecolor': 'black', 'facecolor': 'none', 'size': 10})
        
        # Plot markers for the filtered data with the specified style and size
        axis.scatter(
            level_data['longitude'], 
            level_data['latitude'], 
            marker=marker, 
            s=style['size'],  # Use the size defined in level_style
            label=f'Level {level}',
            edgecolor=style['edgecolor'], 
            facecolor=style['facecolor'],
            linewidths=0.1, 
            alpha=style['alpha']
        )
    
    # Plot the provided country boundary (gadm_cntry)
    gadm_cntry.plot(ax=axis, facecolor='none', edgecolor='black', linewidth=0.1)
    
    plt.tight_layout()
    plt.savefig(figure_filename, bbox_inches='tight')
############ 

import matplotlib.patches as mpatches

SAFFIR_SIM_CAT = [17.49, 32.92, 42.7, 49.39, 58.13, 70.48, 1000]
CAT_NAMES = {
    -1: 'Tropical Depression',
    0: 'Tropical Storm',
    1: 'Hurricane Cat. 1',
    2: 'Hurricane Cat. 2',
    3: 'Hurricane Cat. 3',
    4: 'Hurricane Cat. 4',
    5: 'Hurricane Cat. 5',
}

#define the colourmap
color_ranges = [0, 0.02, 0.10, 0.20, 0.50,1.0]  # Add 1.01 to cover the entire range [0, 1]
colors = [(204 / 255, 255 / 255, 102 / 255, 0.1),   # Slightly transparent
    (204 / 255, 255 / 255, 102 / 255,0.9),     # Fully opaque
    (255 / 255, 255 / 255, 0 / 255, 0.9),    # More transparent
    (255 / 255, 153 / 255, 0 / 255, 0.9),
    (255 / 255, 0 / 255, 0 / 255, 0.9)]
# Create a custom colormap from the list of colors
my_cmap = ListedColormap(colors=colors)

# Create custom legend labels
legend_labels = [
    'No Damage (0.00 - 0.02)',
    'Minor Impact (0.02 - 0.10)',
    'Major Impact (0.10 - 0.20)',
    'Severe Impact (0.20 - 0.50)',
    'Destroyed (0.50 - 1.00)'
]
# Create legend patches based on the colors
legend_patches = [mpatches.Patch(color=colors[i], label=legend_labels[i]) for i in range(len(colors))]

# Define marker shapes for different levels
level_markers = {1: 'o', 2: 's', 3: '^', 4: 'D'}

# Define a dictionary to map levels to their alpha, edgecolor, and facecolor settings
level_style = {
    1: {'alpha': 0.7, 'edgecolor': 'indigo', 'facecolor': 'indigo', 'size': 40},
    2: {'alpha': 0.7, 'edgecolor': 'mediumslateblue', 'facecolor': 'mediumslateblue', 'size': 40},
    3: {'alpha': 0.7, 'edgecolor': 'darkmagenta', 'facecolor': 'darkmagenta', 'size': 40},  # Darker for level 3
    4: {'alpha': 0.7, 'edgecolor': 'mediumvioletred', 'facecolor': 'mediumvioletred', 'size': 40},    # Darker for level 4
}
############ 

def plot_tracks(tc_tracks, exp_lon, exp_lat, exp_value,exp_level,figure_filename,track_alpha,gadm_cntry,lead_time):    
    #######################################################
    color = ['#01B4CC', '#0000ff','#FFD700', '#B8860B', '#CD6600', '#8B4500', '#CD3333']
    CAT_COLORS = color[0:]
    extent = (exp_lon.min(), exp_lon.max(), exp_lat.min(), exp_lat.max())
    mid_lon = 0.5 * (extent[1] + extent[0])
    proj = ccrs.PlateCarree()
    _, axis, fontsize = u_plot.make_map(proj=proj, figsize=(8, 8), adapt_fontsize=True)
    axis.set_extent(extent, crs=ccrs.PlateCarree())
    u_plot.add_shapes(axis)
    cmap = ListedColormap(colors=CAT_COLORS)
    norm = BoundaryNorm([0] + SAFFIR_SIM_CAT, len(SAFFIR_SIM_CAT))
    for track in tc_tracks.data:
        lonlat = np.stack([track.lon.values, track.lat.values], axis=-1)
        lonlat[:, 0] = u_coord.lon_normalize(lonlat[:, 0], center=mid_lon)
        segments = np.stack([lonlat[:-1], lonlat[1:]], axis=1)
        segments = segments[segments[:, 0, 0] * segments[:, 1, 0] >= 0, :, :]
        track_lc = LineCollection(segments, cmap=cmap, norm=norm, linestyle=':', alpha=track_alpha)
        track_lc.set_array(track.max_sustained_wind.values)
        axis.add_collection(track_lc)
        
    # Loop over unique levels in exp_level and plot markers
    
    # Iterate through levels and markers
    for level, marker in level_markers.items():
    # Filter data for the current level
        level_data = exp_level[exp_level['levels'] == level]
    
        # Get the style and size settings for the current level
        style = level_style.get(level, {'alpha': 0.2, 'edgecolor': 'black', 'facecolor': 'none', 'size': 10})
    
        # Plot markers for the filtered data with the specified style and size
        axis.scatter(
            level_data['longitude'], 
            level_data['latitude'], 
            marker=marker, 
            s=style['size'],  # Use the size defined in level_style
            label=f'Level {level}',
            edgecolor=style['edgecolor'], 
            facecolor=style['facecolor'],
            linewidths=0.3, 
            alpha=style['alpha'])

    ## 
    lead_time_str = f"{lead_time} days"

    
    ##### 
    gadm_cntry.plot(ax=axis, facecolor='none', edgecolor='gray', linewidth=0.2)
    # Create a color normalization object
    norm = BoundaryNorm(color_ranges, my_cmap.N)
    mappable = axis.scatter(exp_lon, exp_lat, s=4, c=exp_value, cmap=my_cmap,norm=norm)
    # Create a colorbar with custom tick locations and labels
    cbax = make_axes_locatable(axis).append_axes('right', size="6.5%", pad=0.1, axes_class=plt.Axes)
    cbar = plt.colorbar(mappable, cax=cbax, orientation='vertical', extend='max')
    #cbar.set_label('Impacts Freddy')
    leg_lines = [Line2D([0], [0], color=CAT_COLORS[i_col], lw=2)
                 for i_col in range(len(SAFFIR_SIM_CAT))]
    leg_names = [CAT_NAMES[i_col] for i_col in CAT_NAMES]
    # plot the capital
    plt.plot(-1.58, -18.14, marker='o', markersize=4, markeredgewidth=.7, markeredgecolor='midnightblue',
             markerfacecolor='None')
    # Set the figure size to accommodate the legends
    plt.gcf().set_size_inches(12,8)
    
    # Create a legend for the color ranges and position it on the right
    color_legend = axis.legend(handles=legend_patches, loc='upper right', bbox_to_anchor=(-0.3, 0.3), fontsize=15, 
                               title='Impact-warnings', title_fontsize=15)
    color_legend.get_title().set_fontsize('15')  # Set the font size for the legend title
    # Create a new legend for the ensemble forecast tracks
    # Create a Line2D element for the ensemble forecast tracks (dashed lines)
    #ensemble_tracks_legend = Line2D([0], [0], linestyle=':', lw=2, label='Ens. Forecast Tracks')
    #ensemble_tracks_legend = axis.legend(handles=[ensemble_tracks_legend], loc='upper right',bbox_to_anchor=(-0.5, 0.75), fontsize=10, title='51 - Ensemble Tracks')
    #ensemble_tracks_legend.get_title().set_fontsize('10')  # Set the font size for the legend title

    # Create a legend for the levels and position it on the right below the color legend
    level_legend = axis.legend(title='Levels', loc='upper right', bbox_to_anchor=(-0.3, 0.6), fontsize=15,title_fontsize=15)
    level_legend.get_title().set_fontsize('15')  # Set the font size for the legend title

    # Create a legend for the tropical cyclone categories and position it on the right below the level legend
    cat_tc_legend = axis.legend(leg_lines, leg_names, loc='upper right', bbox_to_anchor=(-0.3, 1), fontsize=15, 
                                title='51 ensemble members',title_fontsize=15)

    # Add all three legends to the axis
    axis.add_artist(color_legend)
    axis.add_artist(level_legend)
    axis.add_artist(cat_tc_legend)
    #axis.add_artist(ensemble_tracks_legend)

    # Set the figure size to accommodate the legends
    plt.gcf().set_size_inches(14, 8)
   

    ### run_date time 
    lead_time_str = f"{lead_time} days"
    run_datetime = tc_tracks.data[0].attrs['run_datetime']
    # Assuming run_datetime is in the desired format ('%a %d %b %Y %HUTC') and lead_time is in days
    event_time = run_datetime + timedelta(days=lead_time)

    # Format event_time similarly to run_datetime
    event_time_str = event_time.strftime('%a %d %b %Y %HUTC')
    
    # Assuming run_datetime is in the desired format ('%a %d %b %Y %HUTC') and lead_time is in days
    forecast_date_str = "Forecast date: " + run_datetime.strftime('%a %d %b %Y %HUTC')
    # Add the forecast date text to the figure
    plt.figtext(0.01, 1.1, forecast_date_str, color='red', fontsize=22, ha='left')
    ###changuin the values of 0.145,0.09, 0.9 changes the location of the datetime 
    
    # Add the event time text to the figure
    event_text = f'Landfall on: {event_time_str}'
    plt.figtext(0.4, 1.05, event_text, color='red', fontsize=22, ha='left')
    plt.figtext(0.4, 1,'Lead time: ' +lead_time_str,color='k', fontsize=22, ha='left')
    plt.tight_layout()
    #plt.show()
    # Save the figure to a file
    plt.savefig(figure_filename, bbox_inches='tight')
    #print(f"Figure saved as {figure_filename}")
    
################################

def plot_impact_track(tc_tracks, exp_levels, exp_value, figure_filename,track_alpha,gadm_cntry,lead_time):
    #######################################################
    # Define custom color map for impacts
    impact_colors = [
        (204 / 255, 255 / 255, 102 / 255, 0.1),  # Slightly transparent
        (204 / 255, 255 / 255, 102 / 255, 0.9),  # Fully opaque
        (255 / 255, 255 / 255, 0 / 255, 0.9),    # Yellow
        (255 / 255, 153 / 255, 0 / 255, 0.9),    # Orange
        (255 / 255, 0 / 255, 0 / 255, 0.9)       # Red
    ]
    my_cmap = ListedColormap(impact_colors)

    # Define normalization range (adjust depending on your impact values)
    norm = BoundaryNorm([0.00, 0.02, 0.10, 0.20, 0.50, 1.0], len(impact_colors))

    # Define color map for tracks (cyclone)
    track_colors = ['#01B4CC', '#0000ff', '#FFD700', '#B8860B', '#CD6600', '#8B4500', '#CD3333']
    CAT_COLORS = track_colors
    track_cmap = ListedColormap(CAT_COLORS)
    track_norm = BoundaryNorm([0] + SAFFIR_SIM_CAT, len(SAFFIR_SIM_CAT))

    extent = (exp_levels['longitude'].min(), exp_levels['longitude'].max(),
              exp_levels['latitude'].min(), exp_levels['latitude'].max())
    mid_lon = 0.5 * (extent[1] + extent[0])
    proj = ccrs.PlateCarree()
    _, axis, fontsize = u_plot.make_map(proj=proj, figsize=(8, 8), adapt_fontsize=True)
    axis.set_extent(extent, crs=ccrs.PlateCarree())
    u_plot.add_shapes(axis)

    # Plot the cyclone tracks with `track_cmap`
    for track in tc_tracks.data:
        lonlat = np.stack([track.lon.values, track.lat.values], axis=-1)
        lonlat[:, 0] = u_coord.lon_normalize(lonlat[:, 0], center=mid_lon)
        segments = np.stack([lonlat[:-1], lonlat[1:]], axis=1)
        segments = segments[segments[:, 0, 0] * segments[:, 1, 0] >= 0, :, :]
        track_lc = LineCollection(segments, cmap=track_cmap, norm=track_norm, linestyle=':', alpha=track_alpha)
        track_lc.set_array(track.max_sustained_wind.values)
        axis.add_collection(track_lc)

    # Ensure exp_levels is a numpy array for proper masking
    exp_lon = np.array(exp_levels['longitude'])
    exp_lat = np.array(exp_levels['latitude'])
    exp_level = np.array(exp_levels['levels'])

    # Exclude points that have a zero or very low impact
    significant_impact_mask = exp_value > 0  # Adjust this threshold as needed
    exp_lon = exp_lon[significant_impact_mask]
    exp_lat = exp_lat[significant_impact_mask]
    exp_level = exp_level[significant_impact_mask]
    exp_value = exp_value[significant_impact_mask]

    # Set uniform size for all points
    uniform_size = 30  # Set a fixed size for all points

    # Plot markers based on levels
    for level, marker in level_markers.items():
        # Filter data for the current level
        level_mask = exp_level == level
        level_data_lon = exp_lon[level_mask]
        level_data_lat = exp_lat[level_mask]
        level_data_value = exp_value[level_mask]

        if len(level_data_lon) > 0:  # Plot only if there are points in this level
            # Use colors based on the impact values from `my_cmap`
            colors = my_cmap(norm(level_data_value))

            # Plot markers for the filtered data with edgecolor from `my_cmap`
            scatter = axis.scatter(
                level_data_lon, 
                level_data_lat, 
                marker=marker,  # Use the marker shape from level_markers
                s=uniform_size,  # Set uniform size for all points
                edgecolor=colors,  # Use colors based on impact values for edgecolor
                facecolor='None',  # Set facecolor to None or transparent
                linewidths=0.1,  # Set a consistent linewidth
                alpha=1)  # Full opacity for markers

    ##### Additional elements to the plot as needed #####
    gadm_cntry.plot(ax=axis, facecolor='none', edgecolor='gray', linewidth=0.2)

    # Create a color normalization object for the impacts
    mappable = axis.scatter(exp_lon, exp_lat, s=30, c=exp_value, cmap=my_cmap, norm=norm)

    # Create a colorbar with custom tick locations and labels for the impacts
    cbax = make_axes_locatable(axis).append_axes('right', size="6.5%", pad=0.1, axes_class=plt.Axes)
    cbar = plt.colorbar(mappable, cax=cbax, orientation='vertical', extend='max')
    #cbar.set_label('Impacts Freddy')
    
    ### run_date time 
    lead_time_str = f"{lead_time} days"
    run_datetime = tc_tracks.data[0].attrs['run_datetime']
    # Assuming run_datetime is in the desired format ('%a %d %b %Y %HUTC') and lead_time is in days
    event_time = run_datetime + timedelta(days=lead_time)

    # Format event_time similarly to run_datetime
    event_time_str = event_time.strftime('%a %d %b %Y %HUTC')
    
    # Assuming run_datetime is in the desired format ('%a %d %b %Y %HUTC') and lead_time is in days
    forecast_date_str = "Forecast date: " + run_datetime.strftime('%a %d %b %Y %HUTC')
    # Add the forecast date text to the figure
    plt.figtext(0.01, 1.1, forecast_date_str, color='red', fontsize=22, ha='left')
    ###changuin the values of 0.145,0.09, 0.9 changes the location of the datetime 
    
    # Add the event time text to the figure
    event_text = f'Landfall on: {event_time_str}'
    plt.figtext(0.4, 1.05, event_text, color='red', fontsize=22, ha='left')
    plt.figtext(0.4, 1,'Lead time: ' +lead_time_str,color='k', fontsize=22, ha='left')
    plt.tight_layout()

    # Set the figure size to accommodate the legends
    plt.gcf().set_size_inches(12, 8)

    # Save the figure to a file
    plt.tight_layout()
    plt.savefig(figure_filename, bbox_inches='tight')
    
########## 

def plot_tracks_nolegend(tc_tracks, exp_lon, exp_lat, exp_value,exp_level,figure_filename,track_alpha,gadm_cntry,lead_time):    
    #######################################################
    color = ['#01B4CC', '#0000ff','#FFD700', '#B8860B', '#CD6600', '#8B4500', '#CD3333']
    CAT_COLORS = color[0:]
    extent = (exp_lon.min(), exp_lon.max(), exp_lat.min(), exp_lat.max())
    mid_lon = 0.5 * (extent[1] + extent[0])
    proj = ccrs.PlateCarree()
    _, axis, fontsize = u_plot.make_map(proj=proj, figsize=(8, 8), adapt_fontsize=True)
    axis.set_extent(extent, crs=ccrs.PlateCarree())
    u_plot.add_shapes(axis)
    cmap = ListedColormap(colors=CAT_COLORS)
    norm = BoundaryNorm([0] + SAFFIR_SIM_CAT, len(SAFFIR_SIM_CAT))
    for track in tc_tracks.data:
        lonlat = np.stack([track.lon.values, track.lat.values], axis=-1)
        lonlat[:, 0] = u_coord.lon_normalize(lonlat[:, 0], center=mid_lon)
        segments = np.stack([lonlat[:-1], lonlat[1:]], axis=1)
        segments = segments[segments[:, 0, 0] * segments[:, 1, 0] >= 0, :, :]
        track_lc = LineCollection(segments, cmap=cmap, norm=norm, linestyle=':', alpha=track_alpha)
        track_lc.set_array(track.max_sustained_wind.values)
        axis.add_collection(track_lc)
        
    # Loop over unique levels in exp_level and plot markers
    
    # Iterate through levels and markers
    for level, marker in level_markers.items():
    # Filter data for the current level
        level_data = exp_level[exp_level['levels'] == level]
    
        # Get the style and size settings for the current level
        style = level_style.get(level, {'alpha': 0.2, 'edgecolor': 'black', 'facecolor': 'none', 'size': 10})
    
        # Plot markers for the filtered data with the specified style and size
        axis.scatter(
            level_data['longitude'], 
            level_data['latitude'], 
            marker=marker, 
            s=style['size'],  # Use the size defined in level_style
            label=f'Level {level}',
            edgecolor=style['edgecolor'], 
            facecolor=style['facecolor'],
            linewidths=0.3, 
            alpha=style['alpha'])

    ## 
    lead_time_str = f"{lead_time} days"

    
    ##### 
    gadm_cntry.plot(ax=axis, facecolor='none', edgecolor='gray', linewidth=0.2)
    # Create a color normalization object
    norm = BoundaryNorm(color_ranges, my_cmap.N)
    mappable = axis.scatter(exp_lon, exp_lat, s=4, c=exp_value, cmap=my_cmap,norm=norm)
    # Create a colorbar with custom tick locations and labels
    cbax = make_axes_locatable(axis).append_axes('right', size="6.5%", pad=0.1, axes_class=plt.Axes)
    cbar = plt.colorbar(mappable, cax=cbax, orientation='vertical', extend='max')
    #cbar.set_label('Impacts Freddy')
    leg_lines = [Line2D([0], [0], color=CAT_COLORS[i_col], lw=2)
                 for i_col in range(len(SAFFIR_SIM_CAT))]
    leg_names = [CAT_NAMES[i_col] for i_col in CAT_NAMES]
    # Set the figure size to accommodate the legends
    plt.gcf().set_size_inches(12,8)
    
    # Create a legend for the color ranges and position it on the right
    #color_legend = axis.legend(handles=legend_patches, loc='upper right', bbox_to_anchor=(-0.3, 0.3), fontsize=15, 
                              # title='Impact-warnings', title_fontsize=15)
    #color_legend.get_title().set_fontsize('15')  # Set the font size for the legend title
    # Create a new legend for the ensemble forecast tracks
    # Create a Line2D element for the ensemble forecast tracks (dashed lines)
    #ensemble_tracks_legend = Line2D([0], [0], linestyle=':', lw=2, label='Ens. Forecast Tracks')
    #ensemble_tracks_legend = axis.legend(handles=[ensemble_tracks_legend], loc='upper right',bbox_to_anchor=(-0.5, 0.75), fontsize=10, title='51 - Ensemble Tracks')
    #ensemble_tracks_legend.get_title().set_fontsize('10')  # Set the font size for the legend title

    # Create a legend for the levels and position it on the right below the color legend
    #level_legend = axis.legend(title='Levels', loc='upper right', bbox_to_anchor=(-0.3, 0.6), fontsize=15,title_fontsize=15)
    #level_legend.get_title().set_fontsize('15')  # Set the font size for the legend title

    # Create a legend for the tropical cyclone categories and position it on the right below the level legend
    #cat_tc_legend = axis.legend(leg_lines, leg_names, loc='upper right', bbox_to_anchor=(-0.3, 1), fontsize=15, 
                                #title='51 ensemble members',title_fontsize=15)

    # Add all three legends to the axis
    #axis.add_artist(color_legend)
    #axis.add_artist(level_legend)
    #axis.add_artist(cat_tc_legend)
    #axis.add_artist(ensemble_tracks_legend)

    # Set the figure size to accommodate the legends
    plt.gcf().set_size_inches(14, 8)
   

    ### run_date time 
    lead_time_str = f"{lead_time} days"
    run_datetime = tc_tracks.data[0].attrs['run_datetime']
    # Assuming run_datetime is in the desired format ('%a %d %b %Y %HUTC') and lead_time is in days
    event_time = run_datetime + timedelta(days=lead_time)

    # Format event_time similarly to run_datetime
    event_time_str = event_time.strftime('%a %d %b %Y %HUTC')
    
    # Assuming run_datetime is in the desired format ('%a %d %b %Y %HUTC') and lead_time is in days
    forecast_date_str = "Forecast date: " + run_datetime.strftime('%a %d %b %Y %HUTC')
    # Add the forecast date text to the figure
    plt.figtext(0.3, 1.1, forecast_date_str, color='red', fontsize=22, ha='left')
    ###changuin the values of 0.145,0.09, 0.9 changes the location of the datetime 
    
    # Add the event time text to the figure
    event_text = f'Landfall on: {event_time_str}'
    plt.figtext(0.3, 1.05, event_text, color='red', fontsize=22, ha='left')
    plt.figtext(0.3, 1,'Lead time: ' +lead_time_str,color='k', fontsize=22, ha='left')
    plt.tight_layout()
    #plt.show()
    # Save the figure to a file
    plt.savefig(figure_filename, bbox_inches='tight')
    #print(f"Figure saved as {figure_filename}")
    
    
#########################################################################################################################
##################### It is keeping the scale of colors of the tracks- ##################################################
#########################################################################################################################

def plot_impact_onelayer(tc_tracks, exp_lon, exp_lat, exp_value, exp_level, figure_filename, track_alpha, gadm_cntry, lead_time):    
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.collections import LineCollection
    from matplotlib.lines import Line2D
    import cartopy.crs as ccrs
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    from matplotlib.cm import ScalarMappable
    from datetime import timedelta

    color = ['#01B4CC', '#0000ff', '#FFD700', '#B8860B', '#CD6600', '#8B4500', '#CD3333']
    CAT_COLORS = color[0:]
    extent = (exp_lon.min(), exp_lon.max(), exp_lat.min(), exp_lat.max())
    mid_lon = 0.5 * (extent[1] + extent[0])
    proj = ccrs.PlateCarree()
    _, axis, fontsize = u_plot.make_map(proj=proj, figsize=(8, 8), adapt_fontsize=True)
    axis.set_extent(extent, crs=ccrs.PlateCarree())
    u_plot.add_shapes(axis)

    cmap = ListedColormap(colors=CAT_COLORS)
    norm_track = BoundaryNorm([0] + SAFFIR_SIM_CAT, len(SAFFIR_SIM_CAT))

    for track in tc_tracks.data:
        lonlat = np.stack([track.lon.values, track.lat.values], axis=-1)
        lonlat[:, 0] = u_coord.lon_normalize(lonlat[:, 0], center=mid_lon)
        segments = np.stack([lonlat[:-1], lonlat[1:]], axis=1)
        segments = segments[segments[:, 0, 0] * segments[:, 1, 0] >= 0, :, :]
        track_lc = LineCollection(segments, cmap=cmap, norm=norm_track, linestyle=':', alpha=track_alpha)
        track_lc.set_array(track.max_sustained_wind.values)
        axis.add_collection(track_lc)

    # Plot country boundaries
    gadm_cntry.plot(ax=axis, facecolor='none', edgecolor='gray', linewidth=0.2)

    # Create color normalization and scatter map
    norm = BoundaryNorm(color_ranges, my_cmap.N)
    mappable = axis.scatter(exp_lon, exp_lat, s=4, c=exp_value, cmap=my_cmap, norm=norm)

    # Use same colors but plot only selected level markers with different sizes
    scalar_mappable = ScalarMappable(norm=norm, cmap=my_cmap)

    for level in sorted(exp_level['levels'].unique()):
        level_data = exp_level[exp_level['levels'] == level]
        if level_data.empty:
            continue

        marker = level_markers.get(level, 'o')
        marker_size = 6 + (level * 3)  # smaller size for level 1, increasing with level
        facecolors = scalar_mappable.to_rgba(exp_value[level_data.index])

        axis.scatter(
            level_data['longitude'],
            level_data['latitude'],
            marker=marker,
            s=marker_size,
            edgecolor='black',
            facecolor=facecolors,
            linewidths=0.3,
            alpha=0.7
        )

    # Colorbar
    cbax = make_axes_locatable(axis).append_axes('right', size="6.5%", pad=0.1, axes_class=plt.Axes)
    cbar = plt.colorbar(mappable, cax=cbax, orientation='vertical', extend='max')

    # Saffir-Simpson track lines legend (not shown in figure)
    leg_lines = [Line2D([0], [0], color=CAT_COLORS[i_col], lw=2) for i_col in range(len(SAFFIR_SIM_CAT))]
    leg_names = [CAT_NAMES[i_col] for i_col in CAT_NAMES]

    plt.gcf().set_size_inches(14, 8)

    # Add forecast and event date info
    lead_time_str = f"{lead_time} days"
    run_datetime = tc_tracks.data[0].attrs['run_datetime']
    event_time = run_datetime + timedelta(days=lead_time)
    event_time_str = event_time.strftime('%a %d %b %Y %HUTC')
    forecast_date_str = "Forecast date: " + run_datetime.strftime('%a %d %b %Y %HUTC')

    plt.figtext(0.3, 1.1, forecast_date_str, color='black', fontsize=18, ha='left')
    plt.figtext(0.3, 1.05, f'Landfall on: {event_time_str}', color='black', fontsize=18, ha='left')
    plt.figtext(0.3, 1, 'Lead time: ' + lead_time_str, color='k', fontsize=18, ha='left')

    plt.tight_layout()
    plt.savefig(figure_filename, bbox_inches='tight')
####################################################################################################################
################## tracks in gray only ################################################################################

def plot_impact_onelayer_graytracks(tc_tracks, exp_lon, exp_lat, exp_value, exp_level, figure_filename, track_alpha, gadm_cntry, lead_time):    
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.collections import LineCollection
    from matplotlib.lines import Line2D
    import cartopy.crs as ccrs
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    from matplotlib.cm import ScalarMappable
    from datetime import timedelta

    color = ['#01B4CC', '#0000ff', '#FFD700', '#B8860B', '#CD6600', '#8B4500', '#CD3333']
    CAT_COLORS = color[0:]
    extent = (exp_lon.min(), exp_lon.max(), exp_lat.min(), exp_lat.max())
    mid_lon = 0.5 * (extent[1] + extent[0])
    proj = ccrs.PlateCarree()
    _, axis, fontsize = u_plot.make_map(proj=proj, figsize=(8, 8), adapt_fontsize=True)
    axis.set_extent(extent, crs=ccrs.PlateCarree())
    u_plot.add_shapes(axis)

    # Plot all tracks in gray with alpha
    for track in tc_tracks.data:
        lonlat = np.stack([track.lon.values, track.lat.values], axis=-1)
        lonlat[:, 0] = u_coord.lon_normalize(lonlat[:, 0], center=mid_lon)
        segments = np.stack([lonlat[:-1], lonlat[1:]], axis=1)
        segments = segments[segments[:, 0, 0] * segments[:, 1, 0] >= 0, :, :]
        
        track_lc = LineCollection(segments, colors='gray', linestyle=':', alpha=track_alpha)
        axis.add_collection(track_lc)

    # Plot country boundaries
    gadm_cntry.plot(ax=axis, facecolor='none', edgecolor='gray', linewidth=0.2)

    # Create color normalization and scatter map
    norm = BoundaryNorm(color_ranges, my_cmap.N)
    mappable = axis.scatter(exp_lon, exp_lat, s=4, c=exp_value, cmap=my_cmap, norm=norm)

    # Use same colors but plot only selected level markers with different sizes
    scalar_mappable = ScalarMappable(norm=norm, cmap=my_cmap)

    for level in sorted(exp_level['levels'].unique()):
        level_data = exp_level[exp_level['levels'] == level]
        if level_data.empty:
            continue

        marker = level_markers.get(level, 'o')
        marker_size = 6 + (level * 3)  # smaller size for level 1, increasing with level
        facecolors = scalar_mappable.to_rgba(exp_value[level_data.index])

        axis.scatter(
            level_data['longitude'],
            level_data['latitude'],
            marker=marker,
            s=marker_size,
            edgecolor='black',
            facecolor=facecolors,
            linewidths=0.3,
            alpha=0.7
        )

    # Colorbar
    cbax = make_axes_locatable(axis).append_axes('right', size="6.5%", pad=0.1, axes_class=plt.Axes)
    cbar = plt.colorbar(mappable, cax=cbax, orientation='vertical', extend='max')

    # Saffir-Simpson track lines legend (can remove if not needed anymore)
    leg_lines = [Line2D([0], [0], color=CAT_COLORS[i_col], lw=2) for i_col in range(len(SAFFIR_SIM_CAT))]
    leg_names = [CAT_NAMES[i_col] for i_col in CAT_NAMES]

    plt.gcf().set_size_inches(14, 8)

    # Add forecast and event date info
    lead_time_str = f"{lead_time} days"
    run_datetime = tc_tracks.data[0].attrs['run_datetime']
    event_time = run_datetime + timedelta(days=lead_time)
    event_time_str = event_time.strftime('%a %d %b %Y %HUTC')
    forecast_date_str = "Forecast date: " + run_datetime.strftime('%a %d %b %Y %HUTC')

    plt.figtext(0.3, 1.1, forecast_date_str, color='black', fontsize=18, ha='left')
    plt.figtext(0.3, 1.05, f'Landfall on: {event_time_str}', color='black', fontsize=18, ha='left')
    plt.figtext(0.3, 1, 'Lead time: ' + lead_time_str, color='k', fontsize=18, ha='left')

    plt.tight_layout()
    plt.savefig(figure_filename, bbox_inches='tight')

#####################################################################################################################

def plot_impact_track_nolegend(tc_tracks, exp_levels, exp_value, figure_filename,track_alpha,gadm_cntry,lead_time):
    #######################################################
    # Define custom color map for impacts
    impact_colors = [
        (204 / 255, 255 / 255, 102 / 255, 0.1),  # Slightly transparent
        (204 / 255, 255 / 255, 102 / 255, 0.9),  # Fully opaque
        (255 / 255, 255 / 255, 0 / 255, 0.9),    # Yellow
        (255 / 255, 153 / 255, 0 / 255, 0.9),    # Orange
        (255 / 255, 0 / 255, 0 / 255, 0.9)       # Red
    ]
    my_cmap = ListedColormap(impact_colors)

    # Define normalization range (adjust depending on your impact values)
    norm = BoundaryNorm([0.00, 0.02, 0.10, 0.20, 0.50, 1.0], len(impact_colors))

    # Define color map for tracks (cyclone)
    track_colors = ['#01B4CC', '#0000ff', '#FFD700', '#B8860B', '#CD6600', '#8B4500', '#CD3333']
    CAT_COLORS = track_colors
    track_cmap = ListedColormap(CAT_COLORS)
    track_norm = BoundaryNorm([0] + SAFFIR_SIM_CAT, len(SAFFIR_SIM_CAT))

    extent = (exp_levels['longitude'].min(), exp_levels['longitude'].max(),
              exp_levels['latitude'].min(), exp_levels['latitude'].max())
    mid_lon = 0.5 * (extent[1] + extent[0])
    proj = ccrs.PlateCarree()
    _, axis, fontsize = u_plot.make_map(proj=proj, figsize=(8, 8), adapt_fontsize=True)
    axis.set_extent(extent, crs=ccrs.PlateCarree())
    u_plot.add_shapes(axis)

    # Plot the cyclone tracks with `track_cmap`
    for track in tc_tracks.data:
        lonlat = np.stack([track.lon.values, track.lat.values], axis=-1)
        lonlat[:, 0] = u_coord.lon_normalize(lonlat[:, 0], center=mid_lon)
        segments = np.stack([lonlat[:-1], lonlat[1:]], axis=1)
        segments = segments[segments[:, 0, 0] * segments[:, 1, 0] >= 0, :, :]
        track_lc = LineCollection(segments, cmap=track_cmap, norm=track_norm, linestyle=':', alpha=track_alpha)
        track_lc.set_array(track.max_sustained_wind.values)
        axis.add_collection(track_lc)

    # Ensure exp_levels is a numpy array for proper masking
    exp_lon = np.array(exp_levels['longitude'])
    exp_lat = np.array(exp_levels['latitude'])
    exp_level = np.array(exp_levels['levels'])

    # Exclude points that have a zero or very low impact
    significant_impact_mask = exp_value > 0  # Adjust this threshold as needed
    exp_lon = exp_lon[significant_impact_mask]
    exp_lat = exp_lat[significant_impact_mask]
    exp_level = exp_level[significant_impact_mask]
    exp_value = exp_value[significant_impact_mask]

    # Set uniform size for all points
    uniform_size = 30  # Set a fixed size for all points

    # Plot markers based on levels
    for level, marker in level_markers.items():
        # Filter data for the current level
        level_mask = exp_level == level
        level_data_lon = exp_lon[level_mask]
        level_data_lat = exp_lat[level_mask]
        level_data_value = exp_value[level_mask]

        if len(level_data_lon) > 0:  # Plot only if there are points in this level
            # Use colors based on the impact values from `my_cmap`
            colors = my_cmap(norm(level_data_value))

            # Plot markers for the filtered data with edgecolor from `my_cmap`
            scatter = axis.scatter(
                level_data_lon, 
                level_data_lat, 
                marker=marker,  # Use the marker shape from level_markers
                s=uniform_size,  # Set uniform size for all points
                edgecolor=colors,  # Use colors based on impact values for edgecolor
                facecolor='None',  # Set facecolor to None or transparent
                linewidths=0.1,  # Set a consistent linewidth
                alpha=1)  # Full opacity for markers

    ##### Additional elements to the plot as needed #####
    gadm_cntry.plot(ax=axis, facecolor='none', edgecolor='gray', linewidth=0.2)

    # Create a color normalization object for the impacts
    mappable = axis.scatter(exp_lon, exp_lat, s=30, c=exp_value, cmap=my_cmap, norm=norm)

    # Create a colorbar with custom tick locations and labels for the impacts
    cbax = make_axes_locatable(axis).append_axes('right', size="6.5%", pad=0.1, axes_class=plt.Axes)
    cbar = plt.colorbar(mappable, cax=cbax, orientation='vertical', extend='max')
    #cbar.set_label('Impacts Freddy')
    
    ### run_date time 
    lead_time_str = f"{lead_time} days"
    run_datetime = tc_tracks.data[0].attrs['run_datetime']
    # Assuming run_datetime is in the desired format ('%a %d %b %Y %HUTC') and lead_time is in days
    event_time = run_datetime + timedelta(days=lead_time)

    # Format event_time similarly to run_datetime
    event_time_str = event_time.strftime('%a %d %b %Y %HUTC')
    
    # Assuming run_datetime is in the desired format ('%a %d %b %Y %HUTC') and lead_time is in days
    forecast_date_str = "Forecast date: " + run_datetime.strftime('%a %d %b %Y %HUTC')
    # Add the forecast date text to the figure
    plt.figtext(0.3, 1.1, forecast_date_str, color='red', fontsize=22, ha='left')
    ###changuin the values of 0.145,0.09, 0.9 changes the location of the datetime 
    
    # Add the event time text to the figure
    event_text = f'Landfall on: {event_time_str}'
    plt.figtext(0.3, 1.05, event_text, color='red', fontsize=22, ha='left')
    plt.figtext(0.3, 1,'Lead time: ' +lead_time_str,color='k', fontsize=22, ha='left')
    plt.tight_layout()

    # Set the figure size to accommodate the legends
    plt.gcf().set_size_inches(12, 8)

    # Save the figure to a file
    plt.tight_layout()
    plt.savefig(figure_filename, bbox_inches='tight')
    

######################
##CALCULATION FOR THE ROAD MEAN IMPACT OVER ALL THE POINTS 

## the standard one becasuse the other one have the new_Idai 

def impact_51ens_st(data_dict, ci_road, event_name):
    """
    Processes the impact data for 51 ensemble members and returns results as a dictionary of DataFrames.

    Parameters:
    data_dict: dict
        Dictionary containing impact data of roads per category.
    ci_road: str
        The road identifier (e.g., 'rd1', 'rd2').
    event_name: str
        The event identifier, which can be flexible (e.g., 'MOZ_Idai', 'MOZ_new_Idai', 'MOZ_new_Freddy').

    Returns:
    dict
        A dictionary where each key is a unique date and each value is a DataFrame containing the processed impact data.
    """
    # Extract unique dates from the data keys
    unique_dates = sorted(set([key.split('_')[-1] for key in data_dict.keys()]))
    result_dict = {}

    # Loop through the unique dates and process the data for each date
    for date in unique_dates:
        # Create the dynamic key using ci_road, event_name, and the date
        key = f'{ci_road}_{event_name}_{date}'  # Flexible event_name
        if key in data_dict:
            # Extract data for all 51 ensemble members and convert to a DataFrame
            columns_data = [np.array(data_dict[key].imp_mat[i].todense()).flatten() for i in range(51)]
            date_df = pd.DataFrame(np.column_stack(columns_data))
            result_dict[date] = date_df

    return result_dict

#################

import geopandas as gpd

def join_road_exp_51ens(ens_51, exposure_gdf):
    results = {}
    for key, df in ens_51.items():
        df = df.reset_index(drop=True)
        exposure_gdf = exposure_gdf.reset_index(drop=True)

        if len(df) == len(exposure_gdf):
            df['osm_id'] = exposure_gdf['osm_id']
        else:
            raise ValueError(f"Mismatch in DataFrame lengths for key: {key}")

        grouped = df.groupby('osm_id').mean()
        first_geometry = exposure_gdf.drop_duplicates(subset=['osm_id'])[['osm_id', 'geometry_orig']]
        merged_grouped = grouped.merge(first_geometry, on='osm_id', how='left')

        column_range = list(range(51))
        merged_grouped['mean_impact'] = merged_grouped[column_range].mean(axis=1)

        # Keep all ensemble columns, 'mean_impact', and 'geometry_orig'
        ensemble_cols = [col for col in merged_grouped.columns if isinstance(col, int) or col == 'mean_impact']
        final_cols = ['osm_id'] + ensemble_cols + ['geometry_orig']
        final_result = merged_grouped[final_cols]

        geo_df = gpd.GeoDataFrame(final_result, geometry='geometry_orig')
        geo_df.set_crs(epsg=4326, inplace=True)

        results[key] = geo_df

    return results
    
###########################################################################################

def mimpact_col_scale(data_dict, column_name, divisor):
    """
    Scales a specified column in all DataFrames within a dictionary.

    Parameters:
    data_dict (dict): Dictionary containing the DataFrames.
    column_name (str): Name of the column to scale.
    divisor (int or float): Value by which to divide the column values.

    Returns:
    None; the operation modifies the DataFrames in place.
    """
    for key in data_dict.keys():
        if column_name in data_dict[key].columns:
            data_dict[key][column_name] /= divisor
        else:
            print(f"Column '{column_name}' not found in DataFrame for key '{key}'.")

###########################################################################################

def mimpact_cols_scale(data_dict, divisor):
    """
    Scales columns 0 to 50 and 'mean_impact' in all DataFrames within a dictionary.

    Parameters:
    data_dict (dict): Dictionary containing the DataFrames.
    divisor (int or float): Value by which to divide the column values.

    Returns:
    None; the operation modifies the DataFrames in place.
    """
    for key, df in data_dict.items():
        # Select columns that are integers from 0 to 50 or 'mean_impact'
        cols_to_scale = [col for col in df.columns if 
                         (isinstance(col, int) and 0 <= col <= 50) or col == 'mean_impact']
        
        # Only scale if those columns are present
        if cols_to_scale:
            df[cols_to_scale] = df[cols_to_scale] / divisor
        else:
            print(f"No matching columns found in DataFrame for key '{key}'.")

###########################################################################################

## HERE THE TITLE SHOULD BE CHANGED AS WE USE ANOTHER FUNCTIONS 

import geopandas as gpd
import matplotlib.pyplot as plt  
import matplotlib.cm as cm
from datetime import datetime
from dateutil.parser import parse
import os

def plot_road_impact(rd1_mimpact, gadm_MDG, output_folder, landfall):
    """Function to plot road impact based on forecast data."""
    landfall_date = parse(landfall)

    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    for key, gdf in rd1_mimpact.items():
        figsize = (12, 12)
        fig, ax = plt.subplots(figsize=figsize)

        # Parse the forecast date from the key
        forecast_date = parse(key)
        lead_time_days = (landfall_date - forecast_date).days  # Calculate lead time in days

        # Use the corrected colormap function
        cmap = plt.get_cmap('plasma')  # Using plt.get_cmap() instead of cm.get_cmap()
        cmap.set_under('black', alpha=0.1)

        # Plot administrative boundaries
        gadm_MDG.plot(ax=ax, facecolor='none', edgecolor='gray', linewidth=0.5)

        # Plot 'mean_impact' from the GeoDataFrame
        gdf.plot(column='mean_impact', ax=ax, cmap=cmap, legend=True, vmin=0.01, vmax=1)

        # Adjust layout
        plt.subplots_adjust(top=0.8)

        # Add plot customizations
        plt.suptitle(f"Deltares: TC-Idai landfall on {landfall_date.strftime('%d %b %Y %H %Z')} UTC", fontsize=22, y=0.89)
        ax.text(-0.1, 1.08, forecast_date.strftime('%a %d %b %Y %H %Z') + " UTC", 
                ha='left', va='top', transform=ax.transAxes, color='red', fontsize=22)
        ax.text(-0.1, 1.04, f"Lead time: {lead_time_days} days", 
                ha='left', va='top', transform=ax.transAxes, color='red', fontsize=22)
        ax.set_axis_off()

        # Save the plot
        output_path = os.path.join(output_folder, f"road_plot_{key}_14032019_deltares.jpg")
        plt.savefig(output_path, bbox_inches='tight', format='jpg')

        plt.close()  # Close the figure to free memory
        
####################

# Function to filter "mean_impact" values above a threshold for all GeoDataFrames in a dictionary
def filter_disruptrd_data(data_dict, threshold):
    filtered_data_dict = {}
    for key, gdf in data_dict.items():
        if 'mean_impact' in gdf.columns:
            filtered_gdf = gdf[gdf['mean_impact'] > threshold]
            filtered_data_dict[key] = filtered_gdf
    return filtered_data_dict

#######################

import geopandas as gpd
from shapely.geometry import Point

def create_points_geodfs_pp(ed_dict, levels_gdf, crs):
    """
    Create a dictionary of GeoDataFrames from a dictionary of coordinates, adding 'levels' from a GeoDataFrame.

    Parameters:
    ed_dict (dict): Dictionary where keys are identifiers and values contain coord_exp attribute.
    levels_gdf (GeoDataFrame): GeoDataFrame containing the 'levels' column to be added.
    crs: Coordinate reference system to use for the GeoDataFrames.

    Returns:
    dict: A dictionary of GeoDataFrames with 'levels' column added.
    """
    geodfs = {}

    for key, impact in ed_dict.items():
        coords = impact.coord_exp  # Extract coordinates

        # **Extract 'latitude' and 'longitude' if missing**
        if 'latitude' not in levels_gdf.columns or 'longitude' not in levels_gdf.columns:
            print(f"Warning: 'latitude' and 'longitude' missing in {key}. Extracting from geometry.")
            levels_gdf = levels_gdf.copy()  # Avoid modifying the original dataframe
            levels_gdf['latitude'] = levels_gdf.geometry.y
            levels_gdf['longitude'] = levels_gdf.geometry.x

        # Selecting necessary columns
        levels = levels_gdf[['latitude', 'longitude', 'value']]

        # Creating GeoDataFrame
        points = [Point(lon, lat) for lat, lon in coords]
        points_gdf = gpd.GeoDataFrame({'geometry': points, 'latitude': levels['latitude'], 
                                       'longitude': levels['longitude']}, crs=crs)

        geodfs[key] = points_gdf  # Store result in dictionary

    return geodfs

#################################

import geopandas as gpd

def convert_to_geodf(df, column_names):
    """
    Convert a DataFrame to a GeoDataFrame with the specified columns.
    
    Parameters:
    - df: DataFrame to be converted
    - column_names: List of column names to include in the GeoDataFrame

    Returns:
    - gdf: The resulting GeoDataFrame with the specified columns
    """
    # Create a GeoDataFrame with the specified columns
    gdf = gpd.GeoDataFrame(df[column_names])
    
    return gdf

##################################

import geopandas as gpd
from shapely.geometry import Point

def create_points_geodfs_CI(ed_dict, levels_gdf, crs):
    """
    Create a dictionary of GeoDataFrames from a dictionary of coordinates, adding 'levels' from a GeoDataFrame.

    Parameters:
    ed_dict (dict): Dictionary where keys are identifiers and values contain coord_exp attribute.
    levels_gdf (GeoDataFrame): GeoDataFrame containing the 'levels' column to be added.
    crs: Coordinate reference system to use for the GeoDataFrames.

    Returns:
    dict: A dictionary of GeoDataFrames with 'levels' column added.
    """
    geodfs = {}
    for key, impact in ed_dict.items():
        coords = impact.coord_exp

        # Selecting the desired columns from levels_gdf
        levels = levels_gdf[['name', 'latitude', 'longitude']]

        # Creating GeoDataFrame with geometry and 'levels'
        points = [Point(lon, lat) for lat, lon in coords]
        points_gdf = gpd.GeoDataFrame({'name': levels['name'], 'geometry': points,
                                       'latitude': levels['latitude'], 'longitude': levels['longitude']}, crs=crs)

        geodfs[key] = points_gdf

    return geodfs

################################

import geopandas as gpd
from shapely.geometry import Point

def create_points_geodfs_hfacilities(ed_dict, levels_gdf, crs):
    """
    Create a dictionary of GeoDataFrames from a dictionary of coordinates, adding 'levels' from a GeoDataFrame.

    Parameters:
    ed_dict (dict): Dictionary where keys are identifiers and values contain coord_exp attribute.
    levels_gdf (GeoDataFrame): GeoDataFrame containing the 'levels' column to be added.
    crs: Coordinate reference system to use for the GeoDataFrames.

    Returns:
    dict: A dictionary of GeoDataFrames with 'levels' column added.
    """
    geodfs = {}
    for key, impact in ed_dict.items():
        coords = impact.coord_exp

        # Selecting the desired columns from levels_gdf
        levels = levels_gdf[['name', 'levels', 'latitude', 'longitude']]

        # Creating GeoDataFrame with geometry and 'levels'
        points = [Point(lon, lat) for lat, lon in coords]
        points_gdf = gpd.GeoDataFrame({'name': levels['name'], 'geometry': points, 'levels': levels['levels'],
                                       'latitude': levels['latitude'], 'longitude': levels['longitude']}, crs=crs)

        geodfs[key] = points_gdf

    return geodfs

##############################

def add_columns_in_geodata(points_geo, mimpacts, column_dict_key):
    """
    Adds NumPy arrays from the mimpacts[column_dict_key] dictionary as new columns to the corresponding 
    GeoDataFrames in points_geo, using the dictionary keys as column names.

    Parameters:
    points_geo (dict): Dictionary of GeoDataFrames.
    mimpacts (dict): Dictionary containing a sub-dictionary at mimpacts[column_dict_key] with NumPy arrays.
    column_dict_key (str): The key to access the relevant sub-dictionary in mimpacts.
    """

    if column_dict_key not in mimpacts:
        print(f"Key '{column_dict_key}' not found in mimpacts.")
        return

    for key in points_geo.keys():
        if key in mimpacts[column_dict_key]:
            geo_df = points_geo[key]
            my_array = mimpacts[column_dict_key][key]

            if len(geo_df) == len(my_array):
                geo_df[key] = my_array  # Add the array as a new column named after the key
                points_geo[key] = geo_df  # Update the GeoDataFrame in points_geo
            else:
                print(f"Lengths do not match for key {key}. Cannot add the NumPy array as a new column.")
        else:
            print(f"Key {key} is not present in mimpacts['{column_dict_key}'].")
            
#################################

import geopandas as gpd
###THIS ONE IS FOR HOSPITALS AS IT CONTAINS LEVELS 

def conv_col_togdf_hf(df, substring):
    """
    Convert columns from a DataFrame to separate GeoDataFrames based on a substring.

    Parameters:
    - df: DataFrame containing the columns to convert
    - substring: string to match in column names to select them for conversion

    Returns:
    - gdf_imp_pp: dictionary of GeoDataFrames, each derived from a column in df
    """
    # List of names that you want to convert to GeoDataFrames
    column_names = [col_name for col_name in df.columns if substring in col_name]

    # Dictionary to hold the created GeoDataFrames
    gdf_imp_pp = {}

    for col_name in column_names:
        # Create a new DataFrame containing only the relevant columns
        sub_df = df[['name','latitude', 'longitude', 'value', 'geometry','levels', col_name]]
        
        # Convert the DataFrame to a GeoDataFrame using the existing 'geometry' column
        gdf = gpd.GeoDataFrame(sub_df, geometry='geometry', crs='EPSG:4326')
        
        # Store the GeoDataFrame in the dictionary
        gdf_imp_pp[col_name] = gdf
    
    return gdf_imp_pp

####################################

def conv_col_togdf_st(df, substring):
    """
    Convert columns from a DataFrame to separate GeoDataFrames based on a substring.

    Parameters:
    - df: DataFrame containing the columns to convert
    - substring: string to match in column names to select them for conversion

    Returns:
    - gdf_imp_pp: dictionary of GeoDataFrames, each derived from a column in df
    """
    # List of names that you want to convert to GeoDataFrames
    column_names = [col_name for col_name in df.columns if substring in col_name]

    # Dictionary to hold the created GeoDataFrames
    gdf_imp_pp = {}

    for col_name in column_names:
        # Create a new DataFrame containing only the relevant columns
        sub_df = df[['name','latitude', 'longitude', 'value', 'geometry', col_name]]
        
        # Convert the DataFrame to a GeoDataFrame using the existing 'geometry' column
        gdf = gpd.GeoDataFrame(sub_df, geometry='geometry', crs='EPSG:4326')
        
        # Store the GeoDataFrame in the dictionary
        gdf_imp_pp[col_name] = gdf
    
    return gdf_imp_pp

#############################

import geopandas as gpd

def conv_col_togdf_pp(df, substring):
    """
    Convert columns from a DataFrame to separate GeoDataFrames based on a substring.

    Parameters:
    - df: DataFrame containing the columns to convert
    - substring: string to match in column names to select them for conversion

    Returns:
    - gdf_imp_pp: dictionary of GeoDataFrames, each derived from a column in df
    It multiplies the value -people per the impact value (0-1) to obtain the %
    people affected. 
    """
    # List of names that you want to convert to GeoDataFrames
    column_names = [col_name for col_name in df.columns if substring in col_name]

    # Dictionary to hold the created GeoDataFrames
    gdf_imp_pp = {}

    for col_name in column_names:
        # Create a new DataFrame containing only the relevant columns
        sub_df = df[['latitude', 'longitude', 'value', 'geometry', 'people', col_name]]

        # Calculate the product of 'people' and the column referred to by col_name
        # and store it in a new column, named 'imp_people'
        sub_df['imp_people'] = sub_df['people'] * sub_df[col_name]

        # Convert the DataFrame to a GeoDataFrame using the existing 'geometry' column
        gdf = gpd.GeoDataFrame(sub_df, geometry='geometry', crs='EPSG:4326')
        
        # Store the GeoDataFrame in the dictionary
        gdf_imp_pp[col_name] = gdf
    
    return gdf_imp_pp
###############################

import geopandas as gpd

def sjoin_gdfs(gdf_imp_pp_dict, other_gdf, predicate='within'):
    """
    Perform a spatial join for each GeoDataFrame in a dictionary with another GeoDataFrame.
    Joins the impact GeoDataFrames with administrative boundaries (e.g., Mozambique shapefile).

    Parameters:
    - gdf_imp_pp_dict: Dictionary of GeoDataFrames to be joined.
    - other_gdf: The other GeoDataFrame to join with.
    - predicate: Spatial relationship predicate for sjoin (default: 'within').

    Returns:
    - joined_gdfs: Dictionary of GeoDataFrames resulting from the spatial joins, with NaN values dropped 
                   and the 'index_right' column removed.
    """
    joined_gdfs_imp_pp = {}
    for key, gdf in gdf_imp_pp_dict.items():
        joined_gdf = gpd.sjoin(gdf, other_gdf, predicate=predicate, how='left')
        joined_gdf = joined_gdf.dropna(subset=['index_right'])  # Drop rows where no join happened
        
        # Remove 'index_right' column
        joined_gdf = joined_gdf.drop(columns=['index_right'])

        joined_gdfs_imp_pp[key] = joined_gdf
    
    return joined_gdfs_imp_pp

######################################

import pandas as pd

def hfacilities_inrisk(gdfs_dict):
    """
    Processes a dictionary of GeoDataFrames to sum the values and count the occurrences of facilities by province and level.
    
    Args:
    gdfs_dict (dict): A dictionary where each key is a string and each value is a GeoDataFrame.
    
    Returns:
    dict: A dictionary where each key is the original key from gdfs_dict, and each value is a DataFrame with summed values and counts.
    """
    counts_dict = {}

    for key, gdf in gdfs_dict.items():
        # Identify the column that starts with 'imph1'
        imp_col = [col for col in gdf.columns if col.startswith('imph')][0]

        # Filter rows where 'imp_col' is greater than 0
        filtered_data = gdf[gdf[imp_col] > 0]

        # Group by 'NAME_1' and 'levels', then sum the imp_col values and count occurrences
        grouped = filtered_data.groupby(['NAME_1', 'levels'])
        sums = grouped[imp_col].sum().reset_index(name='Total_Sum')
        counts = grouped.size().reset_index(name='Count')

        # Merging the sums and counts
        merged_df = pd.merge(sums, counts, on=['NAME_1', 'levels'])

        # Store the result in the dictionary
        counts_dict[key] = merged_df

    return counts_dict

###################################

import pandas as pd

def hfacilities_level_nfailure(gdfs_dict):
    """
    Processes a dictionary of GeoDataFrames to sum the values and count the occurrences of facilities by province and level.
    
    Args:
    gdfs_dict (dict): A dictionary where each key is a string and each value is a GeoDataFrame.
    
    Returns:
    dict: A dictionary where each key is the original key from gdfs_dict, and each value is a DataFrame with summed values and counts.
    """
    counts_dict = {}

    for key, gdf in gdfs_dict.items():
        # Identify the column that starts with 'imph1'
        imp_col = [col for col in gdf.columns if col.startswith('imph')][0]

        # Filter rows where 'imp_col' is greater than 0
        filtered_data = gdf[gdf[imp_col] > 0.20]

        # Group by 'NAME_1' and 'levels', then sum the imp_col values and count occurrences
        grouped = filtered_data.groupby(['NAME_1', 'levels'])
        sums = grouped[imp_col].sum().reset_index(name='Total_Sum')
        counts = grouped.size().reset_index(name='Count')

        # Merging the sums and counts
        merged_df = pd.merge(sums, counts, on=['NAME_1', 'levels'])

        # Store the result in the dictionary
        counts_dict[key] = merged_df

    return counts_dict

######################################

def hfacilities_impsum_level(gdfs_dict):
    """
    Processes a dictionary of GeoDataFrames to sum the values by province and level and keeps only sums above 0.50.
    
    Args:
    gdfs_dict (dict): A dictionary where each key is a string and each value is a GeoDataFrame.
    
    Returns:
    dict: A dictionary where each key is the original key from gdfs_dict and each value is a DataFrame with summed values above 0.50.
    """
    filtered_sums_dict = {}

    for key, gdf in gdfs_dict.items():
        # Identify the column that starts with 'imph1'
        imp_col = [col for col in gdf.columns if col.startswith('imph')][0]

        # Group by 'NAME_1' and 'levels', then sum the imp_col values
        grouped = gdf.groupby(['NAME_1', 'levels'])
        sums = grouped[imp_col].sum().reset_index(name='Total_Sum')

        # Keep only the rows where 'Total_Sum' is greater than 0.50
        filtered_sums = sums[sums['Total_Sum'] > 0.5]

        # Store the result in the dictionary
        filtered_sums_dict[key] = filtered_sums

    return filtered_sums_dict

###################
#### Standard Facilities without levels of clasification or people impp1 ['impp1_MOZ_FREDDY_20230219120000']

def CI_inrisk(gdfs_dict):
    """
    Processes a dictionary of GeoDataFrames to sum the values and count the occurrences of facilities by province and level.
    
    Args:
    gdfs_dict (dict): A dictionary where each key is a string and each value is a GeoDataFrame.
    
    Returns:
    dict: A dictionary where each key is the original key from gdfs_dict, and each value is a DataFrame with summed values and counts.
    """
    counts_dict = {}

    for key, gdf in gdfs_dict.items():
        # Identify the column that starts with 'imph1'
        imp_col = [col for col in gdf.columns if col.startswith('ed')][0]

        # Filter rows where 'imp_col' is greater than 0
        filtered_data = gdf[gdf[imp_col] > 0]

        # Group by 'NAME_1' and 'levels', then sum the imp_col values and count occurrences
        grouped = filtered_data.groupby(['NAME_1'])
        sums = grouped[imp_col].sum().reset_index(name='Total_Sum')
        counts = grouped.size().reset_index(name='Count')

        # Merging the sums and counts
        merged_df = pd.merge(sums, counts, on=['NAME_1'])

        # Store the result in the dictionary
        counts_dict[key] = merged_df

    return counts_dict

#####################

def CI_level_nfailure(gdfs_dict):
    """
    Processes a dictionary of GeoDataFrames to sum the values and count the occurrences of facilities by    province and level.
    
    Args:
    gdfs_dict (dict): A dictionary where each key is a string and each value is a GeoDataFrame.
    
    Returns:
    dict: A dictionary where each key is the original key from gdfs_dict, and each value is a DataFrame with summed values and counts.
    """
    counts_dict = {}

    for key, gdf in gdfs_dict.items():
        # Identify the column that starts with 'imph1'
        imp_col = [col for col in gdf.columns if col.startswith('ed')][0]

        # Filter rows where 'imp_col' is greater than 0
        filtered_data = gdf[gdf[imp_col] > 0.20]

        # Group by 'NAME_1' and 'levels', then sum the imp_col values and count occurrences
        grouped = filtered_data.groupby(['NAME_1'])
        sums = grouped[imp_col].sum().reset_index(name='Total_Sum')
        counts = grouped.size().reset_index(name='Count')

        # Merging the sums and counts
        merged_df = pd.merge(sums, counts, on=['NAME_1'])

        # Store the result in the dictionary
        counts_dict[key] = merged_df

    return counts_dict

############################3

def filter_disrupted(dataframes_dict, threshold):
    """
    Filters each DataFrame in a dictionary by a threshold value in the column that matches the DataFrame's key.

    Parameters:
    dataframes_dict (dict): A dictionary where keys are strings and values are pandas DataFrames.
    threshold (float): The threshold value for filtering.

    Returns:
    dict: A new dictionary with filtered DataFrames.
    """
    disrupted_dfs = {}
    
    for key, df in dataframes_dict.items():
        # Construct the column name from the key
        column_name = key
        # Check if the column exists in the DataFrame
        if column_name in df.columns:
            # Filter the DataFrame
            disrupted_dfs[key] = df[df[column_name] > threshold]
        else:
            print(f"Column '{column_name}' does not exist in DataFrame with key '{key}'.")

    return disrupted_dfs
    
##################################################

def filter_disrupted_range(dataframes_dict, lower_threshold=0, upper_threshold=0.09):
    """
    Filters each DataFrame in a dictionary for values within a specific range in the column that matches the DataFrame's key.

    Parameters:
    - dataframes_dict (dict): Dictionary where keys are strings and values are pandas DataFrames.
    - lower_threshold (float): Lower threshold for filtering (exclusive).
    - upper_threshold (float): Upper threshold for filtering (inclusive).

    Returns:
    - dict: Dictionary with filtered DataFrames.
    """
    disrupted_dfs = {}
    
    for key, df in dataframes_dict.items():
        # Column name matches the dictionary key
        column_name = key

        # Check if the column exists in the DataFrame
        if column_name in df.columns:
            # Filter rows based on threshold range
            filtered_df = df[(df[column_name] > lower_threshold) & (df[column_name] <= upper_threshold)]
            disrupted_dfs[key] = filtered_df
        else:
            print(f"Column '{column_name}' does not exist in DataFrame with key '{key}'.")

    return disrupted_dfs

#########################################################################################

import geopandas as gpd

def aggregate_impact_by_regions_for_all(points_geodfs, admin_regions_gdf, ed1, admin_col_name='NAME_1'):
    """
    Aggregate impact by administrative regions for all keys in points_geodfs.

    Parameters:
    - points_geodfs (dict): Dictionary of GeoDataFrames containing point geometries.
    - admin_regions_gdf (geopandas.GeoDataFrame): GeoDataFrame containing administrative region geometries.
    - ed1 (dict): Dictionary containing impact objects with impact_at_reg method.
    - admin_col_name (str): Column name in admin_regions_gdf that contains region names. Default is 'NAME_1'.

    Returns:
    - dict: A dictionary of DataFrames with aggregated impact data for each key.
    """
    aggregated_impacts = {}
    for key, points_gdf in points_geodfs.items():
        # Change `op=` to `predicate=` for this CLIMADA version 5.0.0.
        joined_gdf = gpd.sjoin(points_gdf, admin_regions_gdf[[admin_col_name, 'geometry']], how='left', predicate='within')

        # Use the result of the spatial join as aggregation regions in impact_at_reg
        if key in ed1:
            aggregated_df = ed1[key].impact_at_reg(agg_regions=joined_gdf[admin_col_name].tolist())

            # Remove 'nan' column if it exists
            if 'nan' in aggregated_df.columns:
                aggregated_df.drop(columns=['nan'], inplace=True)

            aggregated_impacts[key] = aggregated_df
        else:
            print(f"Key '{key}' not found in ed1.")

    return aggregated_impacts

#################33

def remove_zero_columns(dtf):
    """
    Removes columns with all zero values from each DataFrame in a dictionary.

    Parameters:
    dataframes_dict (dict): A dictionary where each value is a DataFrame.

    Returns:
    dict: The updated dictionary with filtered DataFrames.
    """
    for key in dtf.keys():
        # Keep columns where the maximum value is greater than zero
        dtf[key] = dtf[key].loc[:, (dtf[key].max() > 0)]
    
    return dtf
##################################

def seaborn_whiskers(group):
    q1 = group.quantile(0.25)
    q3 = group.quantile(0.75)
    iqr = q3 - q1
    upper_whisker = group[group <= q3 + 1.5 * iqr].max()
    lower_whisker = group[group >= q1 - 1.5 * iqr].min()
    return pd.Series({'lower_whisker': lower_whisker, 'upper_whisker': upper_whisker})

##########
## heatmpas 
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime, timedelta

def plot_heatmap_inrisk(nh1, start_date_str, landfall_date_str, figure_filename):
    combined_heatmap_data = pd.DataFrame()

    for key, df in nh1.items():
        datetime_str = key.split('_')[-1]
        formatted_date = pd.to_datetime(datetime_str, format='%Y%m%d%H%M%S', utc=True).strftime('%Y-%m-%d')
        pivot_df = df.pivot_table(index='NAME_1', columns='levels', values='Count', fill_value=0)
        pivot_df['Date'] = formatted_date
        pivot_df.set_index('Date', append=True, inplace=True)
        combined_heatmap_data = pd.concat([combined_heatmap_data, pivot_df])

    combined_heatmap_data = combined_heatmap_data.stack(level='levels').reset_index()
    combined_heatmap_data.columns = ['Province', 'Date', 'Level', 'Count']
    heatmap_df = combined_heatmap_data.pivot_table(index=['Province', 'Date'], columns='Level', values='Count', fill_value=0)
    heatmap_df = heatmap_df[heatmap_df.sum(axis=1) > 0.5]
    heatmap_df = heatmap_df.round(0)

    # Calculate days to landfall
    landfall_date = datetime.strptime(landfall_date_str, '%Y%m%d%H%M%S')
    heatmap_df['Days_to_Landfall'] = [(landfall_date - datetime.strptime(d, '%Y-%m-%d')).days for d in heatmap_df.index.get_level_values('Date')]
    heatmap_df.sort_values(by='Days_to_Landfall', ascending=False, inplace=True)

    # Create the heatmap
    plt.figure(figsize=(15, 10))
    ax = sns.heatmap(heatmap_df.drop(columns='Days_to_Landfall'), annot=True, fmt="g", cmap='YlGnBu', annot_kws={"size": 15})

    # Increase ytick label size on colorbar
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=15)  # Set colorbar label size
    
    # Increase xtick label size
    ax.tick_params(axis='x', labelsize=15)  # Set x-axis label size
    
    plt.title('Number of Health Facilities in Risk by Province', fontsize=25)
    plt.xlabel('Hospital Level', fontsize=25)
    plt.ylabel('')

    # Modify y-axis labels to countdown format
    y_labels = []
    for index, row in heatmap_df.iterrows():
        days_to_landfall = int(row['Days_to_Landfall'])  # Convert to integer to avoid decimals
        label = f"{index[0]}, {days_to_landfall} days" if days_to_landfall > 0 else f"{index[0]}, Landfall"
        y_labels.append(label)

    ax.set_yticklabels(y_labels, rotation=0, fontsize=15)
    
    # Add text for the day of landfall
    formatted_landfall_date = landfall_date.strftime('%d %b %Y, %H:%M UTC')
    plt.text(0.3, -0.05, f'TC Freddy - Landfall Day: {formatted_landfall_date}', ha='right', va='top', transform=ax.transAxes, fontsize=20)

    # Save the heatmap as an image
    plt.savefig(figure_filename, dpi=300, bbox_inches='tight')
    plt.show()

#################################################################

def plot_heatmap_mimp_HF(nh1, start_date_str, landfall_date_str, figure_filename):
    combined_heatmap_data = pd.DataFrame()

    for key, df in nh1.items():
        datetime_str = key.split('_')[-1]
        formatted_date = pd.to_datetime(datetime_str, format='%Y%m%d%H%M%S', utc=True).strftime('%Y-%m-%d')
        pivot_df = df.pivot_table(index='NAME_1', columns='levels', values='Total_Sum', fill_value=0)
        pivot_df['Date'] = formatted_date
        pivot_df.set_index('Date', append=True, inplace=True)
        combined_heatmap_data = pd.concat([combined_heatmap_data, pivot_df])

    combined_heatmap_data = combined_heatmap_data.stack(level='levels').reset_index()
    combined_heatmap_data.columns = ['Province', 'Date', 'Level', 'Total_Sum']
    heatmap_df = combined_heatmap_data.pivot_table(index=['Province', 'Date'], columns='Level', values='Total_Sum', fill_value=0)
    heatmap_df = heatmap_df[heatmap_df.sum(axis=1) > 0.5]
    heatmap_df = heatmap_df.round(0)

    # Calculate days to landfall and convert to integers
    landfall_date = datetime.strptime(landfall_date_str, '%Y%m%d%H%M%S')
    heatmap_df['Days_to_Landfall'] = [(landfall_date - datetime.strptime(date, '%Y-%m-%d')).days for date in heatmap_df.index.get_level_values('Date')]
    heatmap_df['Days_to_Landfall'] = heatmap_df['Days_to_Landfall'].astype(int)

    # Sort by days to landfall in descending order
    heatmap_df.sort_values(by='Days_to_Landfall', ascending=False, inplace=True)

    # Create the heatmap
    plt.figure(figsize=(15, 10))
    ax = sns.heatmap(heatmap_df.drop(columns='Days_to_Landfall'), annot=True, fmt="g", cmap='YlGnBu', annot_kws={"size": 15})
    
    # Increase ytick label size on colorbar
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=15)  # Set colorbar label size
    
    # Increase xtick label size
    ax.tick_params(axis='x', labelsize=15)  # Set x-axis label size
    
    plt.title('Mean Impact - Health Facilities in Risk by Province', fontsize=25)
    plt.xlabel('Hospital Level', fontsize=25)
    plt.ylabel('')

    # Modify y-axis labels to countdown format
    y_labels = []
    for index, row in heatmap_df.iterrows():
        days_to_landfall = row['Days_to_Landfall']
        label = f"{index[0]}, {int(days_to_landfall)} days" if days_to_landfall > 0 else f"{index[0]}, Landfall"
        y_labels.append(label)

    ax.set_yticklabels(y_labels, rotation=0, fontsize=15)
    
    # Add text for the day of landfall at the bottom of the figure
    formatted_landfall_date = landfall_date.strftime('%d %b %Y, %H:%M UTC')
    plt.text(0.3, -0.05, f'TC Freddy - Landfall Day: {formatted_landfall_date}', ha='right', va='top', transform=ax.transAxes, fontsize=20)

    # Save the heatmap as a JPG image
    plt.savefig(figure_filename, dpi=300, bbox_inches='tight', format='jpg')
    plt.show()
###################################################

def plot_heatmap_nfailures(nh1, start_date_str, landfall_date_str, figure_filename):
    combined_heatmap_data = pd.DataFrame()

    for key, df in nh1.items():
        datetime_str = key.split('_')[-1]
        formatted_date = pd.to_datetime(datetime_str, format='%Y%m%d%H%M%S', utc=True).strftime('%Y-%m-%d')
        pivot_df = df.pivot_table(index='NAME_1', columns='levels', values='Count', fill_value=0)
        pivot_df['Date'] = formatted_date
        pivot_df.set_index('Date', append=True, inplace=True)
        combined_heatmap_data = pd.concat([combined_heatmap_data, pivot_df])

    combined_heatmap_data = combined_heatmap_data.stack(level='levels').reset_index()
    combined_heatmap_data.columns = ['Province', 'Date', 'Level', 'Count']
    heatmap_df = combined_heatmap_data.pivot_table(index=['Province', 'Date'], columns='Level', values='Count', fill_value=0)
    heatmap_df = heatmap_df[heatmap_df.sum(axis=1) > 0.5]
    heatmap_df = heatmap_df.round(0)

    # Calculate days to landfall and sort by it
    landfall_date = datetime.strptime(landfall_date_str, '%Y%m%d%H%M%S')
    heatmap_df['Days_to_Landfall'] = [(landfall_date - datetime.strptime(d, '%Y-%m-%d')).days for d in heatmap_df.index.get_level_values('Date')]
    heatmap_df.sort_values(by='Days_to_Landfall', ascending=False, inplace=True)

    # Create the heatmap
    plt.figure(figsize=(15, 10))
    ax = sns.heatmap(heatmap_df.drop(columns='Days_to_Landfall'), annot=True, fmt="g", cmap='YlGnBu', annot_kws={"size": 15})

    # Increase ytick label size on colorbar
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=15)  # Set colorbar label size
    
    # Increase xtick label size
    ax.tick_params(axis='x', labelsize=15)  # Set x-axis label size
    
    plt.title('Number of Health Facilities Disrupted by Province', fontsize=25)
    plt.xlabel('Hospital Level', fontsize=25)
    plt.ylabel('')
        
    # Modify y-axis labels to countdown format
    y_labels = []
    for index, row in heatmap_df.iterrows():
        days_to_landfall = row['Days_to_Landfall']
        label = f"{index[0]}, {int(days_to_landfall)} days" if days_to_landfall > 0 else f"{index[0]}, Landfall"
        y_labels.append(label)
    
    ax.set_yticklabels(y_labels, rotation=0, fontsize=15)
    
    # Add text for the day of landfall at the bottom of the figure
    formatted_landfall_date = landfall_date.strftime('%d %b %Y, %H:%M UTC')
    plt.text(0.3, -0.05, f'TC Freddy - Landfall Day: {formatted_landfall_date}', ha='right', va='top', transform=ax.transAxes, fontsize=20)

    # Save the figure to a file
    plt.savefig(figure_filename, dpi=300, bbox_inches='tight')
    plt.show()
##########################

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime, timedelta

def plot_heatmap_mimp_CI(nh1, start_date_str, landfall_date_str, figure_filename):
    combined_heatmap_data = pd.DataFrame()

    for key, df in nh1.items():
        datetime_str = key.split('_')[-1]
        formatted_date = pd.to_datetime(datetime_str, format='%Y%m%d%H%M%S', utc=True).strftime('%Y-%m-%d')
        pivot_df = df.pivot_table(index='NAME_1', values='Count', fill_value=0)
        pivot_df['Date'] = formatted_date
        pivot_df.set_index('Date', append=True, inplace=True)
        combined_heatmap_data = pd.concat([combined_heatmap_data, pivot_df])

    combined_heatmap_data = combined_heatmap_data.reset_index()
    combined_heatmap_data.columns = ['Province', 'Date', 'Count']
    heatmap_df = combined_heatmap_data.pivot_table(index=['Province', 'Date'], values='Count', fill_value=0)
    heatmap_df = heatmap_df[heatmap_df.sum(axis=1) > 0.5]
    heatmap_df = heatmap_df.round(0)

     # Calculate days to landfall and convert to integers
    landfall_date = datetime.strptime(landfall_date_str, '%Y%m%d%H%M%S')
    heatmap_df['Days_to_Landfall'] = [(landfall_date - datetime.strptime(date, '%Y-%m-%d')).days for date in heatmap_df.index.get_level_values('Date')]
    heatmap_df['Days_to_Landfall'] = heatmap_df['Days_to_Landfall'].astype(int)

    # Sort by days to landfall in descending order
    heatmap_df.sort_values(by='Days_to_Landfall', ascending=False, inplace=True)

    # Create the heatmap
    plt.figure(figsize=(15, 10))
    ax = sns.heatmap(heatmap_df.drop(columns='Days_to_Landfall'), annot=True, fmt="g", cmap='YlGnBu', annot_kws={"size": 15})
    
    # Increase ytick label size on colorbar
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=15)  # Set colorbar label size
    
    # Increase xtick label size
    ax.tick_params(axis='x', labelsize=15)  # Set x-axis label size
    
    plt.title('Number of Educational Facilities in Risk by Province', fontsize=25)
    plt.xlabel('Hospital Level', fontsize=25)
    plt.ylabel('')

    # Modify y-axis labels to countdown format
    y_labels = []
    for index, row in heatmap_df.iterrows():
        days_to_landfall = row['Days_to_Landfall']
        label = f"{index[0]}, {int(days_to_landfall)} days" if days_to_landfall > 0 else f"{index[0]}, Landfall"
        y_labels.append(label)

    ax.set_yticklabels(y_labels, rotation=0, fontsize=15)
    
    # Add text for the day of landfall at the bottom of the figure
    formatted_landfall_date = landfall_date.strftime('%d %b %Y, %H:%M UTC')
    plt.text(0.3, -0.05, f'TC Freddy - Landfall Day: {formatted_landfall_date}', ha='right', va='top', transform=ax.transAxes, fontsize=20)

    # Save the heatmap as a JPG image
    plt.savefig(figure_filename, dpi=300, bbox_inches='tight', format='jpg')
    plt.show()

##############################################

def plot_heatmap_CI_fail(nh1, start_date_str, landfall_date_str, figure_filename):
    combined_heatmap_data = pd.DataFrame()

    # Collect and process the data from each key in the dictionary
    for key, df in nh1.items():
        datetime_str = key.split('_')[-1]
        formatted_date = pd.to_datetime(datetime_str, format='%Y%m%d%H%M%S', utc=True).strftime('%Y-%m-%d')
        pivot_df = df.pivot_table(index='NAME_1', values='Count', fill_value=0)
        pivot_df['Date'] = formatted_date
        pivot_df.set_index('Date', append=True, inplace=True)
        combined_heatmap_data = pd.concat([combined_heatmap_data, pivot_df])

    # Reformat the DataFrame for the heatmap
    combined_heatmap_data = combined_heatmap_data.reset_index()
    combined_heatmap_data.columns = ['Province', 'Date', 'Count']
    heatmap_df = combined_heatmap_data.pivot_table(index=['Province', 'Date'], values='Count', fill_value=0)
    heatmap_df = heatmap_df[heatmap_df.sum(axis=1) > 0.5]
    heatmap_df = heatmap_df.round(0)

    # Calculate days to landfall and add them to the DataFrame
    landfall_date = datetime.strptime(landfall_date_str, '%Y%m%d%H%M%S')
    heatmap_df['Days_to_Landfall'] = [(landfall_date - datetime.strptime(d, '%Y-%m-%d')).days for d in heatmap_df.index.get_level_values(1)]
    
    # Sort the DataFrame by 'Days_to_Landfall' in descending order
    heatmap_df.sort_values(by='Days_to_Landfall', ascending=False, inplace=True)

    # Create the heatmap
    plt.figure(figsize=(15, 10))
    ax = sns.heatmap(heatmap_df.drop(columns='Days_to_Landfall'), annot=True, fmt="g", cmap='YlGnBu', annot_kws={"size": 15})
    
    # Set colorbar label size
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=15)
    
    # Set x-axis label size
    ax.tick_params(axis='x', labelsize=15)
    
    # Set the title and axis labels
    plt.title('Number of Educational Facilities Disrupted by Province', fontsize=25)
    plt.xlabel('')
    plt.ylabel('')

    # Modify y-axis labels to countdown format
    y_labels = []
    for index, row in heatmap_df.iterrows():
        days_to_landfall = int(row['Days_to_Landfall'])
        label = f"{index[0]}, {days_to_landfall} days" if days_to_landfall > 0 else f"{index[0]}, Landfall"
        y_labels.append(label)

    # Set y-axis labels
    ax.set_yticklabels(y_labels, rotation=0, fontsize=15)
    
    # Add text for the day of landfall
    formatted_landfall_date = landfall_date.strftime('%d %b %Y, %H:%M UTC')
    plt.text(0.3, -0.05, f'TC Freddy - Landfall Day: {formatted_landfall_date}', ha='right', va='top', transform=ax.transAxes, fontsize=20)

    # Save the heatmap as an image
    plt.savefig(figure_filename, dpi=600, bbox_inches='tight')
    plt.show()
    
###################################

def plot_exposure_ed(exp_lon, exp_lat, figure_filename):    
    color = cm_mp.BuPu(np.linspace(0, 1, len(SAFFIR_SIM_CAT) + 2))
    CAT_COLORS = color[2:]
    extent = (exp_lon.min(), exp_lon.max(), exp_lat.min(), exp_lat.max())
    proj = ccrs.PlateCarree()
    _, axis, fontsize = u_plot.make_map(proj=proj, figsize=(8, 8), adapt_fontsize=True)
    axis.set_extent(extent, crs=ccrs.PlateCarree())
    u_plot.add_shapes(axis)

    # Scatter plot for the latitude and longitude data
    axis.scatter(exp_lon, exp_lat, s=30, color='blue')  # Color can be adjusted

    plt.tight_layout()
    plt.savefig(figure_filename, bbox_inches='tight')
    plt.show()

########################################################

def plot_tracks_ed(tc_tracks, exp_lon, exp_lat, exp_value,figure_filename,track_alpha,gadm_cntry,lead_time):    
    #######################################################
    color = ['#01B4CC', '#0000ff','#FFD700', '#B8860B', '#CD6600', '#8B4500', '#CD3333']
    CAT_COLORS = color[0:]
    extent = (exp_lon.min(), exp_lon.max(), exp_lat.min(), exp_lat.max())
    mid_lon = 0.5 * (extent[1] + extent[0])
    proj = ccrs.PlateCarree()
    _, axis, fontsize = u_plot.make_map(proj=proj, figsize=(8, 8), adapt_fontsize=True)
    axis.set_extent(extent, crs=ccrs.PlateCarree())
    u_plot.add_shapes(axis)
    cmap = ListedColormap(colors=CAT_COLORS)
    norm = BoundaryNorm([0] + SAFFIR_SIM_CAT, len(SAFFIR_SIM_CAT))
    for track in tc_tracks.data:
        lonlat = np.stack([track.lon.values, track.lat.values], axis=-1)
        lonlat[:, 0] = u_coord.lon_normalize(lonlat[:, 0], center=mid_lon)
        segments = np.stack([lonlat[:-1], lonlat[1:]], axis=1)
        segments = segments[segments[:, 0, 0] * segments[:, 1, 0] >= 0, :, :]
        track_lc = LineCollection(segments, cmap=cmap, norm=norm, linestyle=':', alpha=track_alpha)
        track_lc.set_array(track.max_sustained_wind.values)
        axis.add_collection(track_lc)
        
    # Plot exposure data
    norm = BoundaryNorm(color_ranges, my_cmap.N)
    mappable = axis.scatter(exp_lon, exp_lat, s=10, c=exp_value, cmap=my_cmap, norm=norm)

    ## 
    lead_time_str = f"{lead_time} days"

    
    ##### 
    gadm_cntry.plot(ax=axis, facecolor='none', edgecolor='gray', linewidth=0.5)
    # Create a color normalization object
    norm = BoundaryNorm(color_ranges, my_cmap.N)
    mappable = axis.scatter(exp_lon, exp_lat, s=10, c=exp_value, cmap=my_cmap,norm=norm)
    # Create a colorbar with custom tick locations and labels
    cbax = make_axes_locatable(axis).append_axes('right', size="6.5%", pad=0.1, axes_class=plt.Axes)
    cbar = plt.colorbar(mappable, cax=cbax, orientation='vertical', extend='max')
    #cbar.set_label('Impacts Freddy')
    leg_lines = [Line2D([0], [0], color=CAT_COLORS[i_col], lw=2)
                 for i_col in range(len(SAFFIR_SIM_CAT))]
    leg_names = [CAT_NAMES[i_col] for i_col in CAT_NAMES]
    # plot the capital
    plt.plot(-1.58, -18.14, marker='o', markersize=4, markeredgewidth=.7, markeredgecolor='midnightblue',
             markerfacecolor='None')
    # Set the figure size to accommodate the legends
    plt.gcf().set_size_inches(12,8)
    
    # Create a legend for the color ranges and position it on the right
    color_legend = axis.legend(handles=legend_patches, loc='upper right', bbox_to_anchor=(-0.3, 0.3), fontsize=15, 
                               title='Impact-warnings', title_fontsize=15)
    color_legend.get_title().set_fontsize('15')  # Set the font size for the legend title
    # Create a new legend for the ensemble forecast tracks
    # Create a Line2D element for the ensemble forecast tracks (dashed lines)
    #ensemble_tracks_legend = Line2D([0], [0], linestyle=':', lw=2, label='Ens. Forecast Tracks')
    #ensemble_tracks_legend = axis.legend(handles=[ensemble_tracks_legend], loc='upper right',bbox_to_anchor=(-0.5, 0.75), fontsize=10, title='51 - Ensemble Tracks')
    #ensemble_tracks_legend.get_title().set_fontsize('10')  # Set the font size for the legend title

    # Create a legend for the levels and position it on the right below the color legend
    #level_legend = axis.legend(title='Levels', loc='upper right', bbox_to_anchor=(-0.3, 0.6), fontsize=15,title_fontsize=15)
    #level_legend.get_title().set_fontsize('15')  # Set the font size for the legend title

    # Create a legend for the tropical cyclone categories and position it on the right below the level legend
    cat_tc_legend = axis.legend(leg_lines, leg_names, loc='upper right', bbox_to_anchor=(-0.3, 1), fontsize=15, 
                                title='51 ensemble members',title_fontsize=15)

    # Add all three legends to the axis
    axis.add_artist(color_legend)
    #axis.add_artist(level_legend)
    axis.add_artist(cat_tc_legend)
    #axis.add_artist(ensemble_tracks_legend)

    # Set the figure size to accommodate the legends
    plt.gcf().set_size_inches(14, 8)
   

    ### run_date time 
    lead_time_str = f"{lead_time} days"
    run_datetime = tc_tracks.data[0].attrs['run_datetime']
    # Assuming run_datetime is in the desired format ('%a %d %b %Y %HUTC') and lead_time is in days
    event_time = run_datetime.item() + timedelta(days=lead_time)

    # Format event_time similarly to run_datetime
    event_time_str = event_time.strftime('%a %d %b %Y %HUTC')
    
    # Assuming run_datetime is in the desired format ('%a %d %b %Y %HUTC') and lead_time is in days
    forecast_date_str = "Forecast date: " + run_datetime.item().strftime('%a %d %b %Y %HUTC')
    # Add the forecast date text to the figure
    plt.figtext(0.01, 1.1, forecast_date_str, color='red', fontsize=22, ha='left')
    ###changuin the values of 0.145,0.09, 0.9 changes the location of the datetime 
    
    # Add the event time text to the figure
    event_text = f'Landfall on: {event_time_str}'
    plt.figtext(0.4, 1.05, event_text, color='red', fontsize=22, ha='left')
    plt.figtext(0.4, 1,'Lead time: ' +lead_time_str,color='k', fontsize=22, ha='left')
    plt.tight_layout()
    #plt.show()
    # Save the figure to a file
    plt.savefig(figure_filename, bbox_inches='tight')
    #print(f"Figure saved as {figure_filename}") it works fine but I do not want to plot exp_level please 
    
    
##################

def plot_tracks_nolegend_ed(tc_tracks, exp_lon, exp_lat, exp_value,figure_filename,track_alpha,gadm_cntry,lead_time):    
    #######################################################
    color = ['#01B4CC', '#0000ff','#FFD700', '#B8860B', '#CD6600', '#8B4500', '#CD3333']
    CAT_COLORS = color[0:]
    extent = (exp_lon.min(), exp_lon.max(), exp_lat.min(), exp_lat.max())
    mid_lon = 0.5 * (extent[1] + extent[0])
    proj = ccrs.PlateCarree()
    _, axis, fontsize = u_plot.make_map(proj=proj, figsize=(8, 8), adapt_fontsize=True)
    axis.set_extent(extent, crs=ccrs.PlateCarree())
    u_plot.add_shapes(axis)
    cmap = ListedColormap(colors=CAT_COLORS)
    norm = BoundaryNorm([0] + SAFFIR_SIM_CAT, len(SAFFIR_SIM_CAT))
    for track in tc_tracks.data:
        lonlat = np.stack([track.lon.values, track.lat.values], axis=-1)
        lonlat[:, 0] = u_coord.lon_normalize(lonlat[:, 0], center=mid_lon)
        segments = np.stack([lonlat[:-1], lonlat[1:]], axis=1)
        segments = segments[segments[:, 0, 0] * segments[:, 1, 0] >= 0, :, :]
        track_lc = LineCollection(segments, cmap=cmap, norm=norm, linestyle=':', alpha=track_alpha)
        track_lc.set_array(track.max_sustained_wind.values)
        axis.add_collection(track_lc)
        
    # Plot exposure data
    norm = BoundaryNorm(color_ranges, my_cmap.N)
    mappable = axis.scatter(exp_lon, exp_lat, s=10, c=exp_value, cmap=my_cmap, norm=norm)

    ## 
    lead_time_str = f"{lead_time} days"

    
    ##### 
    gadm_cntry.plot(ax=axis, facecolor='none', edgecolor='gray', linewidth=0.5)
    # Create a color normalization object
    norm = BoundaryNorm(color_ranges, my_cmap.N)
    mappable = axis.scatter(exp_lon, exp_lat, s=10, c=exp_value, cmap=my_cmap,norm=norm)
    # Create a colorbar with custom tick locations and labels
    cbax = make_axes_locatable(axis).append_axes('right', size="6.5%", pad=0.1, axes_class=plt.Axes)
    cbar = plt.colorbar(mappable, cax=cbax, orientation='vertical', extend='max')
    #cbar.set_label('Impacts Freddy')
    leg_lines = [Line2D([0], [0], color=CAT_COLORS[i_col], lw=2)
                 for i_col in range(len(SAFFIR_SIM_CAT))]
    leg_names = [CAT_NAMES[i_col] for i_col in CAT_NAMES]
    # plot the capital
    plt.plot(-1.58, -18.14, marker='o', markersize=4, markeredgewidth=.7, markeredgecolor='midnightblue',
             markerfacecolor='None')
    # Set the figure size to accommodate the legends
    plt.gcf().set_size_inches(12,8)
    
    # Create a legend for the color ranges and position it on the right
    #color_legend = axis.legend(handles=legend_patches, loc='upper right', bbox_to_anchor=(-0.3, 0.3), fontsize=15, 
                               #title='Impact-warnings', title_fontsize=15)
    #color_legend.get_title().set_fontsize('15')  # Set the font size for the legend title
    # Create a new legend for the ensemble forecast tracks
    # Create a Line2D element for the ensemble forecast tracks (dashed lines)
    #ensemble_tracks_legend = Line2D([0], [0], linestyle=':', lw=2, label='Ens. Forecast Tracks')
    #ensemble_tracks_legend = axis.legend(handles=[ensemble_tracks_legend], loc='upper right',bbox_to_anchor=(-0.5, 0.75), fontsize=10, title='51 - Ensemble Tracks')
    #ensemble_tracks_legend.get_title().set_fontsize('10')  # Set the font size for the legend title

    # Create a legend for the levels and position it on the right below the color legend
    #level_legend = axis.legend(title='Levels', loc='upper right', bbox_to_anchor=(-0.3, 0.6), fontsize=15,title_fontsize=15)
    #level_legend.get_title().set_fontsize('15')  # Set the font size for the legend title

    # Create a legend for the tropical cyclone categories and position it on the right below the level legend
    #cat_tc_legend = axis.legend(leg_lines, leg_names, loc='upper right', bbox_to_anchor=(-0.3, 1), fontsize=15, 
                                #title='51 ensemble members',title_fontsize=15)

    # Add all three legends to the axis
    #axis.add_artist(color_legend)
    #axis.add_artist(level_legend)
    #axis.add_artist(cat_tc_legend)
    #axis.add_artist(ensemble_tracks_legend)

    # Set the figure size to accommodate the legends
    plt.gcf().set_size_inches(14, 8)
   

    ### run_date time 
    lead_time_str = f"{lead_time} days"
    run_datetime = tc_tracks.data[0].attrs['run_datetime']
    # Assuming run_datetime is in the desired format ('%a %d %b %Y %HUTC') and lead_time is in days
    event_time = run_datetime.item() + timedelta(days=lead_time)

    # Format event_time similarly to run_datetime
    event_time_str = event_time.strftime('%a %d %b %Y %HUTC')
    
    # Assuming run_datetime is in the desired format ('%a %d %b %Y %HUTC') and lead_time is in days
    forecast_date_str = "Forecast date: " + run_datetime.item().strftime('%a %d %b %Y %HUTC')
    # Add the forecast date text to the figure
    plt.figtext(0.4, 1.1, forecast_date_str, color='red', fontsize=22, ha='left')
    ###changuin the values of 0.145,0.09, 0.9 changes the location of the datetime 
    
    # Add the event time text to the figure
    event_text = f'Landfall on: {event_time_str}'
    plt.figtext(0.4, 1.05, event_text, color='red', fontsize=22, ha='left')
    plt.figtext(0.4, 1,'Lead time: ' +lead_time_str,color='k', fontsize=22, ha='left')
    plt.tight_layout()
    #plt.show()
    # Save the figure to a file
    plt.savefig(figure_filename, bbox_inches='tight')
    #print(f"Figure saved as {figure_filename}") it works fine but I do not want to plot exp_level please
    
#################################################


def calculate_nearest_population(geodisrupt_gdf, pop_gdf):
    """
    Calculate the nearest population point for each entry in GeoDataFrames within geodisrupt2_dfs.

    Parameters:
    - geodisrupt_gdf: Dictionary of GeoDataFrames where nearest population will be calculated for each entry.
    - pop_gdf: GeoDataFrame representing population data.

    Returns:
    - geodisrupt_gdf: Dictionary of updated GeoDataFrames with nearest population index and affected population.
    """
    for key, gdf in geodisrupt_gdf.items():
        # Calculate the index of the nearest population point for each entry in gdf
        gdf['nearest_pop_index'] = gdf.geometry.apply(lambda x: pop_gdf.distance(x).idxmin())
        
        # Create a new column to store the affected population for each entry in gdf
        gdf['imp_people'] = gdf['nearest_pop_index'].apply(lambda idx: pop_gdf.at[idx, 'people'])
        
        # Convert the 'affected_population' column to a numeric type, round to integers without decimals, and cast to int
        gdf['imp_people'] = pd.to_numeric(gdf['imp_people']).round(0).astype(int)
        
        # Update the dictionary with the calculated GeoDataFrame
        geodisrupt_gdf[key] = gdf
    
    return geodisrupt_gdf

###########################

def get_ppaffected_cat1_nodisrupt(people_nodisrupted_cat1, disruptpp1, disruptpp2):
    """
    Identify people affected in Category 1 but not disrupted, by comparing imp_people_cat1 with disrupt_pp1_unique_dict and disrupt_pp2.

    Parameters:
    - imp_people_cat1: Dictionary of GeoDataFrames representing affected people in Category 1.
    - disrupt_pp1_unique_dict: Dictionary of GeoDataFrames representing disrupted people in Category 1.
    - disrupt_pp2: Dictionary of GeoDataFrames representing disrupted people in Category 2.

    Returns:
    - imp_people_cat1_unique: Dictionary of GeoDataFrames with people affected but not disrupted for each date.
    """
    people_nodisrupted_cat1_unique = {}

    # Iterate over each key in imp_people_cat1 (dates)
    for date_key in people_nodisrupted_cat1.keys():
        # Retrieve the GeoDataFrames for the current day from all dictionaries
        people_nodisrupted_cat1_df = people_nodisrupted_cat1[date_key]
        disruptpp1_df = disruptpp1.get(date_key)  # Use .get() to avoid KeyError if key doesn't exist
        disruptpp2_df = disruptpp2.get(date_key)  # Use .get() to avoid KeyError if key doesn't exist

        # Check if disrupt_pp1_df exists for this date
        if disruptpp1_df is not None:
            # Step 1: Perform a left join to find points that are in imp_people_cat1 but not in disrupt_pp1_unique_dict
            merged_df_pp1 = pd.merge(people_nodisrupted_cat1_df, disruptpp1_df[['latitude', 'longitude']], 
                                     on=['latitude', 'longitude'], how='left', indicator=True)
            
            # Step 2: Keep only rows where points in imp_people_cat1 do not exist in disrupt_pp1_unique_dict
            people_nodisrupted_cat1_unique_df = merged_df_pp1[merged_df_pp1['_merge'] == 'left_only']
            
            # Drop the '_merge' column which was added for the merge check
            people_nodisrupted_cat1_unique_df = people_nodisrupted_cat1_unique_df.drop(columns=['_merge'])
            
            # Step 3: If disrupt_pp2_df exists, remove points that overlap with disrupt_pp2 as well
            if disruptpp2_df is not None:
                # Perform a left join to find points that are in imp_people_cat1_unique_df but not in disrupt_pp2
                merged_df_pp2 = pd.merge(people_nodisrupted_cat1_unique_df, disruptpp2_df[['latitude', 'longitude']], 
                                         on=['latitude', 'longitude'], how='left', indicator=True)
                
                # Keep only rows where points in imp_people_cat1_unique_df do not exist in disrupt_pp2
                people_nodisrupted_cat1_unique_df = merged_df_pp2[merged_df_pp2['_merge'] == 'left_only']
                
                # Drop the '_merge' column again
                people_nodisrupted_cat1_unique_df = people_nodisrupted_cat1_unique_df.drop(columns=['_merge'])
            
            # Store the result in the dictionary for this date
            people_nodisrupted_cat1_unique[date_key] = people_nodisrupted_cat1_unique_df
        else:
            print(f"No corresponding disrupted data found for {date_key}")
    
    return people_nodisrupted_cat1_unique

############################

import pandas as pd

def cal_nearestpop_disrup(geodisrupt_gdf, disrupt_data_gdf):
    """
    Calculate the nearest population point for each entry in GeoDataFrames within geodisrupt_gdf
    using the corresponding GeoDataFrames in disrupt_data_gdf. Skips keys with empty data and
    shows exactly where it was skipped.

    Parameters:
    - geodisrupt_gdf: Dictionary of GeoDataFrames where nearest population will be calculated.
    - disrupt_data_gdf: Dictionary of GeoDataFrames representing population data.

    Returns:
    - geodisrupt_gdf: Updated dictionary with nearest population index and affected population.
    """
    # Ensure the keys in both dictionaries are in the same order
    keys_geodisrupt = sorted(geodisrupt_gdf.keys())
    keys_disrupt_data = sorted(disrupt_data_gdf.keys())

    print(f"\n Starting processing for {len(keys_geodisrupt)} entries...")

    # Iterate over paired keys from both dictionaries
    for geo_key, disrupt_key in zip(keys_geodisrupt, keys_disrupt_data):
        print(f"\n Processing pair: {geo_key} | {disrupt_key}")

        # Access the corresponding GeoDataFrames
        current_geodisrupt_gdf = geodisrupt_gdf[geo_key]
        current_disrupt_data_gdf = disrupt_data_gdf[disrupt_key]

        # Skip and show where if either GeoDataFrame is empty
        if current_geodisrupt_gdf.empty:
            print(f" SKIPPED: GeoDisrupt data for **{geo_key}** is empty.")
            continue
        if current_disrupt_data_gdf.empty:
            print(f" SKIPPED: Population data for **{disrupt_key}** is empty.")
            continue

        # Perform the nearest population calculation
        try:
            print(f" Calculating nearest population for **{geo_key}**...")

            current_geodisrupt_gdf['nearest_pop_index'] = current_geodisrupt_gdf.geometry.apply(
                lambda x: current_disrupt_data_gdf.distance(x).idxmin()
            )

            current_geodisrupt_gdf['pp_affected'] = current_geodisrupt_gdf['nearest_pop_index'].apply(
                lambda idx: current_disrupt_data_gdf.at[idx, 'imp_people']
            )
            current_geodisrupt_gdf['pp_affected'] = pd.to_numeric(
                current_geodisrupt_gdf['pp_affected'], errors='coerce'
            ).fillna(0).round(0).astype(int)

            # Update the dictionary with the calculated GeoDataFrame
            geodisrupt_gdf[geo_key] = current_geodisrupt_gdf
            print(f" SUCCESS: Processed **{geo_key}** successfully.")

        except Exception as e:
            print(f" ERROR: Failed processing **{geo_key}** due to: {e}")

    print("\n All available data processed successfully.\n")
    return geodisrupt_gdf

#############################################

def subset_imppeople(dataframes_dict, threshold_cat):
    """
    Filters each DataFrame in a dictionary by a threshold value in the 'imp_people' column.

    Parameters:
    - dataframes_dict (dict): A dictionary where keys are strings and values are pandas DataFrames.
    - threshold_cat (float): The threshold value for filtering the 'imp_people' column.

    Returns:
    - dict: A new dictionary with filtered DataFrames where 'imp_people' values are above the threshold.
    """
    disrupted_dfs = {}
    
    for key, df in dataframes_dict.items():
        # Check if the 'imp_people' column exists in the DataFrame
        if 'imp_people' in df.columns:
            # Filter the DataFrame where 'imp_people' is above the threshold
            disrupted_dfs[key] = df[df['imp_people'] > threshold_cat]
        else:
            print(f"'imp_people' column does not exist in DataFrame with key '{key}'.")

    return disrupted_dfs
#############################################


    
##########################################

def get_unique_disrupt_impp1(disrupt_pp1, disrupt_pp2):
    # Initialize an empty dictionary to store unique points for each day
    disrupt_pp1_unique_dict = {}
    
    # Iterate over each key in the disrupt_pp1 dictionary
    for date_key in disrupt_pp1.keys():
        # Retrieve the GeoDataFrames for the current day from both dictionaries
        disrupt_pp1_df = disrupt_pp1[date_key]
        date_key_pp2 = date_key.replace('impp1_', 'impp2_')  # Adjust key to match disrupt_pp2 format
        
        # Check if the corresponding key exists in disrupt_pp2
        if date_key_pp2 in disrupt_pp2:
            disrupt_pp2_df = disrupt_pp2[date_key_pp2]
            
            # Perform a left join to find points that are in disrupt_pp1 but not in disrupt_pp2
            merged_df = pd.merge(disrupt_pp1_df, disrupt_pp2_df[['latitude', 'longitude']], 
                                 on=['latitude', 'longitude'], how='left', indicator=True)
            
            # Keep only rows where points in disrupt_pp1 do not exist in disrupt_pp2
            disrupt_pp1_unique = merged_df[merged_df['_merge'] == 'left_only']
            
            # Drop the '_merge' column which was added for the merge check
            disrupt_pp1_unique = disrupt_pp1_unique.drop(columns=['_merge'])
            
            # Store the result in the dictionary for this date
            disrupt_pp1_unique_dict[date_key] = disrupt_pp1_unique
        
        else:
            print(f"No corresponding data found in disrupt_pp2 for {date_key_pp2}")
    
    return disrupt_pp1_unique_dict




##################################

import geopandas as gpd

def assign_province_to_roads(disrupt_rd2_dict, gadm_MOZ_gdf):
    """
    Assign each road segment in disrupt_rd2_dict to a province based on the gadm_MOZ_gdf boundaries.

    Parameters:
    - disrupt_rd2_dict: Dictionary of GeoDataFrames containing LineStrings with disruption data.
    - gadm_MOZ_gdf: GeoDataFrame containing province boundaries with a 'NAME_1' column for province names.

    Returns:
    - result_dict: Dictionary of GeoDataFrames with an added 'NAME_1' column indicating the province name for each road.
    """
    result_dict = {}

    # Ensure gadm_MOZ_gdf has the right geometry set and required column
    if 'NAME_1' not in gadm_MOZ_gdf.columns:
        raise ValueError("gadm_MOZ_gdf must contain a 'NAME_1' column with province names.")
    gadm_MOZ_gdf = gadm_MOZ_gdf.set_geometry(gadm_MOZ_gdf.geometry)

    for date_key, roads_gdf in disrupt_rd2_dict.items():
        # Set the geometry column for roads if not already set
        roads_gdf = roads_gdf.set_geometry('geometry_orig')

        # ✅ FIXED: Change `op=` to `predicate=`
        roads_with_provinces = gpd.sjoin(roads_gdf, gadm_MOZ_gdf[['NAME_1', 'geometry']], how="left", predicate="intersects")
        
        # Keep only relevant columns, including 'osm_id', 'mean_impact', and 'NAME_1'
        result_dict[date_key] = roads_with_provinces[['osm_id', 'mean_impact', 'geometry_orig', 'NAME_1']]
    
    return result_dict


######################################################################################################


from shapely.geometry import LineString
from sklearn.neighbors import BallTree
import numpy as np

def calculate_pp_byroaddisrup(disrupt_rd2_dict, disrupt_pp1_dict, radius_km=2):
    """
    Calculate the total number of people affected within a 2 km radius of the midpoint of each LineString
    in each GeoDataFrame within disrupt_rd2_dict, using population data in disrupt_pp1_dict.
    Ensures no double-counting of affected people.
    Skips any keys where either GeoDataFrame is empty.
    """
    result_dict = {}

    # Extract date keys from disrupt_pp1_dict and create a mapping
    pp1_date_mapping = {key.split('_')[-1]: key for key in disrupt_pp1_dict.keys()}

    # Initialize a set to keep track of counted population indices to avoid double-counting
    counted_indices = set()

    # Iterate over each entry in disrupt_rd2_dict
    for rd2_key, disrupt_rd2 in disrupt_rd2_dict.items():
        # Attempt to match the date portion in rd2_key with a key in disrupt_pp1_dict
        pp1_key = pp1_date_mapping.get(rd2_key)

        if pp1_key is None:
            print(f"Warning: No population data found for key {rd2_key}. Skipping.")
            continue

        # Retrieve the corresponding GeoDataFrame for disrupt_pp1
        disrupt_pp1 = disrupt_pp1_dict[pp1_key]

        # Skip if either dataframe is empty
        if disrupt_rd2.empty:
            print(f"Skipping {rd2_key}: Road data is empty.")
            continue
        if disrupt_pp1.empty:
            print(f"Skipping {pp1_key}: Population data is empty.")
            continue

        # Set 'geometry_orig' as the geometry column if it exists in disrupt_rd2
        if 'geometry_orig' in disrupt_rd2.columns:
            disrupt_rd2 = disrupt_rd2.set_geometry('geometry_orig')
        else:
            raise KeyError(f"ERROR: 'geometry_orig' missing in {rd2_key} GeoDataFrame.")

        # Calculate midpoints for each LineString in disrupt_rd2
        disrupt_rd2['midpoint'] = disrupt_rd2.geometry.apply(
            lambda line: line.interpolate(0.5, normalized=True) if isinstance(line, LineString) else None
        )

        # Filter out any None values that may arise if geometry isn't a LineString
        disrupt_rd2 = disrupt_rd2.dropna(subset=['midpoint'])
        if disrupt_rd2.empty:
            print(f"Skipping {rd2_key}: No valid midpoints after filtering.")
            continue

        # Extract coordinates for midpoints and population points
        midpoints_coords = np.array([(point.x, point.y) for point in disrupt_rd2['midpoint']])
        pop_coords = np.array([(point.x, point.y) for point in disrupt_pp1.geometry])

        # Skip if coordinates are empty
        if pop_coords.size == 0:
            print(f"Skipping {pp1_key}: Population coordinates are empty.")
            continue
        if midpoints_coords.size == 0:
            print(f"Skipping {rd2_key}: Midpoints coordinates are empty.")
            continue

        # Initialize BallTree for fast spatial queries
        try:
            tree = BallTree(np.radians(pop_coords), metric='haversine')
        except Exception as e:
            print(f"ERROR building BallTree for {rd2_key}: {e}")
            continue

        midpoints_radians = np.radians(midpoints_coords)
        radius_radians = radius_km / 6371.0

        # Calculate affected people for each midpoint
        affected_population = []
        for midpoint in midpoints_radians:
            indices = tree.query_radius([midpoint], r=radius_radians)[0]
            unique_indices = [idx for idx in indices if idx not in counted_indices]
            total_affected = disrupt_pp1.iloc[unique_indices]['imp_people'].sum()
            affected_population.append(total_affected)
            counted_indices.update(unique_indices)

        # Add the affected population to disrupt_rd2
        disrupt_rd2['pp_affected'] = affected_population
        disrupt_rd2 = disrupt_rd2.drop(columns=['midpoint'])
        result_dict[rd2_key] = disrupt_rd2

        print(f" Finished processing {rd2_key}. Affected population calculated.\n")

    return result_dict





########################################################################################################

def calculate_ppaffected_2km(geodisrupt_gdf, pop_gdf, max_distance_km=2):
    """
    Calculate the population within a specified distance for each entry in GeoDataFrames.

    Parameters:
    - geodisrupt_gdf: Dictionary of GeoDataFrames.
    - pop_gdf: GeoDataFrame representing population data.
    - max_distance_km: Maximum distance in kilometers to consider (default is 2 km).

    Returns:
    - geodisrupt_gdf: Dictionary of updated GeoDataFrames with population within specified distance.
    """
    # Convert the distance to meters (1 km = 1000 meters)
    max_distance_m = max_distance_km * 1000

    for key, gdf in geodisrupt_gdf.items():
        # Initialize the affected population column
        gdf['affected_population'] = 0

        for idx, row in gdf.iterrows():
            # Calculate distances to all population points
            distances = pop_gdf.distance(row.geometry)

            # Filter population points within the specified distancedisrupt
            within_distance = pop_gdf[distances <= max_distance_m]

            # Sum the population values of these points
            gdf.at[idx, 'affected_population'] = within_distance['people'].sum()

        geodisrupt_gdf[key] = gdf

    return geodisrupt_gdf

