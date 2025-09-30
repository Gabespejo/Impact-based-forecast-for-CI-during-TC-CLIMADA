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
## This one is for Indirect Impact Functions 
####### This is for disrupted hospitals that have level as well #################

def get_disrupted_exposures_by_latlon(imph2_dict, exp_gdf, threshold=0.20, min_members=5, mode="above", lower=None, upper=None):
    
    """
    Identify disrupted exposures (hospitals) and assign levels using exact latitude/longitude match.

    Parameters:
    - imph2_dict: dict[str, Impact] with .imp_mat and .coord_exp
    - exp_gdf: GeoDataFrame with ['latitude', 'longitude', 'levels']
    - threshold: threshold value for disruption
    - min_members: minimum number of ensemble members
    - mode: 'above' or 'range'
    - lower, upper: bounds for 'range' mode

    Returns:
    - dict[str, GeoDataFrame] with disrupted points and hospital levels
    """
    disrupted_exposures_dict = {}

    # Ensure proper CRS
    exp_gdf = exp_gdf.set_crs("EPSG:4326")

    for key, impact_obj in imph2_dict.items():
        imp_matrix = impact_obj.imp_mat.toarray().T

        if mode == "above":
            mask = imp_matrix >= threshold
        elif mode == "range":
            if lower is None or upper is None:
                raise ValueError("Specify both lower and upper for 'range' mode.")
            mask = (imp_matrix > lower) & (imp_matrix < upper)
        else:
            raise ValueError("Invalid mode. Use 'above' or 'range'.")

        count_mask = mask.sum(axis=1)
        disrupted_mask = count_mask >= min_members
        coords = impact_obj.coord_exp[disrupted_mask]

        disrupted_gdf = gpd.GeoDataFrame({
            "latitude": coords[:, 0],
            "longitude": coords[:, 1],
            "n_ensemble_members": count_mask[disrupted_mask],
            "geometry": [Point(lon, lat) for lat, lon in coords]
        }, crs="EPSG:4326")

        # Merge by exact lat/lon
        merged = disrupted_gdf.merge(
            exp_gdf[['latitude', 'longitude', 'levels']],
            on=['latitude', 'longitude'],
            how='left'
        )

        disrupted_exposures_dict[key] = merged

    return disrupted_exposures_dict

#################################################################################################
################################################################################################
################# This is for hospitals without levels and other infrastructure standard ######
###############################################################################################
import geopandas as gpd
from shapely.geometry import Point

def get_disrupted_exposures_and_ensemble(imph2_dict, threshold=0.20, min_members=5, mode="above", lower=None, upper=None):
    """
    Extract disrupted exposure points from imph2 dictionary based on impact threshold.

    Parameters:
    - imph2_dict (dict): Dictionary with impact matrices.
    - threshold (float): Threshold for 'above' mode (default 0.20).
    - min_members (int): Minimum ensemble members needed.
    - mode (str): 'above' or 'range'.
    - lower (float): Lower bound for 'range' mode (exclusive).
    - upper (float): Upper bound for 'range' mode (exclusive).

    Returns:
    - disrupted_exposures_dict (dict): Dictionary of GeoDataFrames with disrupted exposures and member count.
    """
    disrupted_exposures_dict = {}

    for key, impact_obj in imph2_dict.items():
        imp_matrix = impact_obj.imp_mat.toarray()     # (51, N)
        imp_matrix_T = imp_matrix.T                   # (N, 51)

        if mode == "above":
            mask = imp_matrix_T >= threshold
        elif mode == "range":
            if lower is None or upper is None:
                raise ValueError("For 'range' mode, both 'lower' and 'upper' must be provided.")
            mask = (imp_matrix_T > lower) & (imp_matrix_T < upper)
        else:
            raise ValueError("Invalid mode. Choose 'above' or 'range'.")

        count_mask = mask.sum(axis=1)                 # number of members ≥ threshold per exposure
        disrupted_mask = count_mask >= min_members    # boolean: exposures considered disrupted

        coords = impact_obj.coord_exp[disrupted_mask]
        latitudes = coords[:, 0]
        longitudes = coords[:, 1]
        member_counts = count_mask[disrupted_mask]    # ensemble counts for disrupted only

        disrupted_gdf = gpd.GeoDataFrame({
            "latitude": latitudes,
            "longitude": longitudes,
            "n_ensemble_members": member_counts,
            "geometry": [Point(lon, lat) for lat, lon in coords]
        }, crs="EPSG:4326")

        disrupted_exposures_dict[key] = disrupted_gdf

    return disrupted_exposures_dict

######################################################################################################################
### I want to add people and NAME_1 
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

def add_population_and_region_to_disrupted(impp1_disrupted_dict, gdf_worldpop, gadm_MOZ_gdf):
    """
    Add 'people' (from WorldPop) and 'NAME_1' (from GADM) to each disrupted-points GeoDataFrame.
    Expects points in EPSG:4326; projects to a metric CRS for spatial ops, then back to 4326.
    """

    # Accept CLIMADA Exposures objects
    if hasattr(gdf_worldpop, 'gdf'):
        gdf_worldpop = gdf_worldpop.gdf

    # Ensure CRS present
    if gdf_worldpop.crs is None:
        gdf_worldpop = gdf_worldpop.set_crs(4326)
    if gadm_MOZ_gdf.crs is None:
        gadm_MOZ_gdf = gadm_MOZ_gdf.set_crs(4326)

    # Use a projected CRS for all spatial ops (choose one that’s OK for Mozambique)
    PROJ = "EPSG:3857"
    wp_proj  = gdf_worldpop.to_crs(PROJ)
    adm_proj = gadm_MOZ_gdf.to_crs(PROJ)

    # KDTree on admin centroids (projected)
    centroids = adm_proj.geometry.centroid
    kdtree = cKDTree(np.column_stack([centroids.x, centroids.y]))

    updated = {}

    for key, gdf in impp1_disrupted_dict.items():

        # EMPTY-GUARD: no disrupted points for this lead time
        if gdf is None or gdf.empty:
            empty = gpd.GeoDataFrame(
                {"latitude": [], "longitude": [], "n_ensemble_members": []},
                geometry=gpd.GeoSeries([], crs=4326),
                crs=4326
            )
            empty["people"] = pd.Series(dtype="Int64")
            empty["NAME_1"] = pd.Series(dtype="object")
            updated[key] = empty
            continue

        # Ensure geometry exists and CRS is 4326
        if "geometry" not in gdf.columns or not isinstance(gdf.geometry, gpd.GeoSeries) or gdf.crs is None:
            gdf = gpd.GeoDataFrame(
                gdf.drop(columns=[c for c in gdf.columns if c == "geometry"]),
                geometry=gpd.points_from_xy(gdf["longitude"], gdf["latitude"], crs=4326),
                crs=4326,
            )

        # Project to PROJ for spatial joins
        pts = gdf.to_crs(PROJ)

        # Add population (spatial join; robust vs merge on geometry)
        if not pts.empty and not wp_proj.empty:
            pts = gpd.sjoin(pts, wp_proj[["geometry", "people"]], how="left", predicate="intersects").drop(columns="index_right")
        if "people" not in pts.columns:
            pts["people"] = 0
        pts["people"] = pts["people"].fillna(0).astype(int)

        # Add NAME_1 (admin region)
        if not pts.empty and not adm_proj.empty:
            pts = gpd.sjoin(pts, adm_proj[["geometry", "NAME_1"]], how="left", predicate="intersects").drop(columns="index_right")
        if "NAME_1" not in pts.columns:
            pts["NAME_1"] = pd.Series(dtype="object")

        # Nearest admin centroid for any unmatched NAME_1
        unmatched = pts[pts["NAME_1"].isna()]
        if not unmatched.empty:
            coords = np.column_stack([unmatched.geometry.x, unmatched.geometry.y])
            _, idxs = kdtree.query(coords, k=1)
            pts.loc[unmatched.index, "NAME_1"] = adm_proj.iloc[idxs]["NAME_1"].values

        # Return to geographic CRS for storage
        updated[key] = pts.to_crs(4326)

    return updated


######################################################################################################

import pandas as pd
import numpy as np
from scipy.spatial import cKDTree

def cal_nearestpop_to_infrastructure(disrupted_hospitals, impp1_disrupted_dict):
    """
    Assign nearest affected population and NAME_1 region from disrupted population points
    to each disrupted infrastructure point (e.g., hospitals).

    Parameters:
    - disrupted_hospitals (dict): GeoDataFrames of disrupted hospitals.
    - impp1_disrupted_dict (dict): GeoDataFrames of affected population with 'people' and 'NAME_1'.

    Returns:
    - updated_hospitals_dict (dict): Dictionary with 'pp_affected' and 'NAME_1' assigned from nearest population.
    """

    updated_hospitals_dict = {}

    keys_hosp = sorted(disrupted_hospitals.keys())
    keys_pop = sorted(impp1_disrupted_dict.keys())

    print(f"\n Starting nearest population match for {len(keys_hosp)} lead times...")

    for hosp_key, pop_key in zip(keys_hosp, keys_pop):
        gdf_hosp = disrupted_hospitals[hosp_key]
        gdf_pop = impp1_disrupted_dict[pop_key]

        print(f"\n  Processing: {hosp_key} | {pop_key}")

        if gdf_hosp.empty:
            print(f"  SKIPPED: No hospitals in {hosp_key}")
            continue
        if gdf_pop.empty:
            print(f"  SKIPPED: No population data in {pop_key}")
            continue

        try:
            # Coordinates
            hosp_coords = np.array([[pt.x, pt.y] for pt in gdf_hosp.geometry])
            pop_coords = np.array([[pt.x, pt.y] for pt in gdf_pop.geometry])

            # KDTree search
            tree = cKDTree(pop_coords)
            _, idx = tree.query(hosp_coords, k=1)

            # Add values from nearest population point
            gdf_hosp['nearest_pop_index'] = idx
            gdf_hosp['pp_affected'] = gdf_hosp['nearest_pop_index'].apply(
                lambda i: gdf_pop.iloc[i]['people']
            ).fillna(0).round(0).astype(int)

            gdf_hosp['NAME_1'] = gdf_hosp['nearest_pop_index'].apply(
                lambda i: gdf_pop.iloc[i]['NAME_1']
            )

            updated_hospitals_dict[hosp_key] = gdf_hosp
            print(f"  SUCCESS: Population + NAME_1 assigned to {hosp_key}")

        except Exception as e:
            print(f"  ERROR in {hosp_key}: {e}")

    print("\n All processing complete.")
    return updated_hospitals_dict

####################################################################################################
###################################################################################################
#####################################################################################################

####get disrupted roads ############################################################################

def get_disrupted_road(exposure_dict, threshold=0.20, min_members=5, mode="above", lower=None, upper=None):
    """
    Filters exposures disrupted in at least `min_members` ensemble members using one of two modes.

    Returns:
    - dict of filtered GeoDataFrames by lead time key, keeping the 'geometry_orig' column if present.
    """
    disrupted_dict = {}

    for lead_time_key, gdf in exposure_dict.items():
        ens_cols = [col for col in gdf.columns if isinstance(col, int) and 0 <= col <= 50]
        impact_array = gdf[ens_cols].values

        if mode == "above":
            count_disrupted = (impact_array >= threshold).sum(axis=1)
        elif mode == "range":
            if lower is None or upper is None:
                raise ValueError("Both lower and upper bounds must be set for 'range' mode.")
            count_disrupted = ((impact_array >= lower) & (impact_array <= upper)).sum(axis=1)
        else:
            raise ValueError("Invalid mode. Use 'above' or 'range'.")

        mask = count_disrupted >= min_members

        # Start with selected ensemble columns
        filtered = gdf.loc[mask, ens_cols].copy()

        # Preserve osm_id if available
        if 'osm_id' in gdf.columns:
            filtered.insert(0, 'osm_id', gdf.loc[mask, 'osm_id'].values)

        # Preserve geometry_orig if present
        if 'geometry_orig' in gdf.columns:
            filtered['geometry_orig'] = gdf.loc[mask, 'geometry_orig'].values

        #  Fix applied here
        filtered["n_ensemble_members"] = count_disrupted[mask]

        # Convert to GeoDataFrame with geometry if available
        if 'geometry' in gdf.columns:
            filtered = gpd.GeoDataFrame(filtered, geometry=gdf.loc[mask, 'geometry'], crs=gdf.crs)

        disrupted_dict[lead_time_key] = filtered

    return disrupted_dict

#####################################################################################################
############# geometry to disrupted roads ##########################################################
#####################################################################################################

def add_geometry_to_disrupted_roads(rd2_disrupted, gdf_roads):
    """
    Merge road geometry into each disrupted roads DataFrame by osm_id.
    
    Parameters:
    - rd2_disrupted: dict of DataFrames with disrupted roads per lead time
    - gdf_roads: GeoDataFrame with 'osm_id' and 'geometry'
    
    Returns:
    - dict with same keys as rd2_disrupted, each value a DataFrame with geometry
    """
    result = {}
    for key, df in rd2_disrupted.items():
        merged = df.merge(
            gdf_roads[['osm_id', 'geometry']],
            on='osm_id',
            how='left'
        )
        result[key] = merged
    return result

######################################################################################################
#####################################################################################################

### calculate people within 2km around the road that is disrupted 
from shapely.geometry import LineString
from sklearn.neighbors import BallTree
import numpy as np

def calc_pp_byroaddisrup_5ens(disrupt_rd2_dict, disrupt_pp1_dict, radius_km=2):
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
        if 'geometry' in disrupt_rd2.columns:
            disrupt_rd2 = disrupt_rd2.set_geometry('geometry')
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
            total_affected = disrupt_pp1.iloc[unique_indices]['people'].sum()
            affected_population.append(total_affected)
            counted_indices.update(unique_indices)

        # Add the affected population to disrupt_rd2
        disrupt_rd2['pp_affected'] = affected_population
        disrupt_rd2 = disrupt_rd2.drop(columns=['midpoint'])
        result_dict[rd2_key] = disrupt_rd2

        print(f" Finished processing {rd2_key}. Affected population calculated.\n")

    return result_dict
    
###############################################################################################
############# this is only for roads 

def assign_province_to_roads(rd2_disrupted_impp1_dict, gadm_moz):
    updated_dict = {}
    gadm_moz = gadm_moz.to_crs(4326)

    for key, gdf in rd2_disrupted_impp1_dict.items():
        if gdf.empty:
            updated_dict[key] = gdf
            continue

        gdf = gdf.copy()
        gdf = gdf.set_geometry('geometry')

        # Fix missing CRS
        if gdf.crs is None:
            gdf.set_crs(4326, inplace=True)
        else:
            gdf = gdf.to_crs(4326)

        gdf_with_province = gpd.sjoin(
            gdf, gadm_moz[['NAME_1', 'geometry']], how='left', predicate='intersects'
        ).drop(columns=['index_right'])

        updated_dict[key] = gdf_with_province

    return updated_dict
    

########################################################################################################
