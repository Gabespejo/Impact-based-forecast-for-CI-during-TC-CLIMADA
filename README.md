# Impact-based Forecast for Critical Infrastructure during Tropical Cyclones 

Forecasting the potential impact of weather extremes in the weeks to days before they happen can help increase the preparedness in the areas that might be
affected. The emerging field of research on impact-based forecast models is instrumental in this regard, aiding international organizations and governments in making informed decisions,
taking early actions, and allocating resources efficiently. This study aims to build upon the pioneering research of the Weather4UN project, by developing and impact forecast tool of
tropical cyclones on critical infrastructure. While earlier efforts concentrated on estimating the potential affected population, our focus shifts to understanding the impact on critical
infrastructure, starting with healthcare facilities, schools and road networks. We present a case study of Tropical Cyclone (TC) Freddy, which hit Mozambique and Madagascar in 2023.
We calculate direct impacts using two sets of vulnerability curves for structural damage and another based on the Saffir-Simpson scale to ensure global applicability when needed. To
better understand the significance of these impacts, we further assess their indirect effects on the population.

## Structure
The scripts consist in: 
- Hazard data (Fetching the forecast) ECMWF 51 ensemble members (IFS Cycle 47r3)
- Exposure data:
  Hospitals, Educational facilities, roads
  Worldpop (UN adjust 2020)
- Impact Function/ vulnerability:
  Eberenz et. al (2021) & Deltares Institute (Global Facility for Disaster Reduction and Recovery, 2023)
  Saffir Simpson hurricane wind scale

## Forecast Fetching

This function in the code look for the files that correspond to the event that we want to analyze. In order to use this function, you should have the files in your own computer or server

**fetch_multiple_ecmwf_data(base_folder, start_date, end_date, event_name)**

- base_folder= "/cluster/project/climate/gespejo/data/TC_0012"  change this path with your own data.

- start_date = datetime(2023,2,16,18,0) refers to the start of the event; year,month,day,UTC. 

- end_date = datetime(2023, 2,21,18, 0)  refers to the end of the event; year,month,day,UTC. 

- event_name = "FREDDY"  refers to the name of the event. In this case is FREDDY.

In our case we are using a lead time of 5 days. 

## Centroids

**from climada.hazard import Centroids**

min_lat, max_lat, min_lon, max_lon = -27,-10, 42, 52

cent = Centroids.from_pnt_bounds((min_lon, min_lat, max_lon, max_lat), res=0.12)

cent.check()

This code is set within the region of study, which in this case corresponds to Madagascar (MDG).

## Factor Intensity

**tc_intensity_10min(tc_object, factor)**

"""
    Modifies the intensity of a TropCyclone object.

    Parameters:
    tc_object: TropCyclone object to be modified.
    factor: The factor by which to multiply the intensity.

    Returns:
    Modified TropCyclone object.
    """
For the vulnerability curve from the Deltares Institute (Global Facility for Disaster Reduction and Recovery, 2023). It is needed to use this factor conversion.

## Exposure

In this part in order to work with the exposure data, it is needed to put the location of your data. To download the Openstreetmap data, you should follow
the instructions from https://github.com/CLIMADA-project/climada_petals/blob/main/doc/tutorial/climada_exposures_openstreetmap.ipynb

"""

PATH_DATA = '/cluster/project/climate/gespejo/data/infrastructure/'

PATH_DATA_OSM = '/cluster/work/climate/gespejo/climada/data/openstreetmap/' # path to search for osm.pbf files and to download to if not existing

PATH_DATA_HVMV = PATH_DATA +'power_global/grid.gpkg' # path of this file from gridfinder (It needs to be downloaded).

PATH_DATA_PP = PATH_DATA +'power_global/global_power_plant_database.csv' # path of this file from WRI global power plant db. (It needs to be downloaded).

#PATH_DATA_CT = PATH_DATA +'cell_towers/opencellid_global_1km_int.tif' # path of this file from worldbank open data gridded celltowers (It needs to be downloaded)

PATH_DATA_POP = PATH_DATA + 'population/' # path to search for population files and to download to if not existing

PATH_SAVE = '/cluster/project/climate/gespejo/data/infrastructure/Madagascar_results_'

"""

## Cleaning exposure data & Classification of the Hospitals for levels 

**_find_duplicates(overlap_gdf)**  look for the duplicate points 

**_remove_duplicates(orig_gdf, indices_dupl)**  remove the duplicates points 

**find_remove_duplicates(orig_gdf)**  here in a single function does both actions, first look for the duplicates and then remove them. 



## License

[Specify the license under which the project is distributed.]

## Contributors

[List the contributors to the project, including their roles or contributions.]

## Acknowledgments

[Optional section to acknowledge any individuals, organizations, or resources that contributed to the project.]

## Contact

[Provide contact information for questions, feedback, or collaboration opportunities.]
