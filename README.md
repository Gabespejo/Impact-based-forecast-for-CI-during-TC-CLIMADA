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

This function in the code look for the files that correspond to the event that we want to analyze. In order to use this function, you should have the files in your own computer or server.
fetch_multiple_ecmwf_data(base_folder, start_date, end_date, event_name)
base_folder= "/cluster/project/climate/gespejo/data/TC_0012"  change this path with your own data
start_date = datetime(2023,2,16,18,0) refers to the start of the event; year,month,day,UTC 
end_date = datetime(2023, 2,21,18, 0)  refers to the end of the event; year,month,day,UTC 
event_name = "FREDDY"  refers to the name of the event. In this case is FREDDY

## Centroids

[Discuss the centroids used in the project, their significance, and how they are determined.]

## Time Steps

[Explain the time steps or intervals used in the project, including any considerations or reasons for choosing them.]

## Factor Intensity

[Describe the factor intensity analysis in the project, including the factors considered and their impact on the analysis.]

## Exposure

[Discuss the exposure analysis in the project, including the types of exposure considered and their relevance.]

## Usage

[Provide instructions on how to use the project, including any setup steps, dependencies, or commands.]

## License

[Specify the license under which the project is distributed.]

## Contributors

[List the contributors to the project, including their roles or contributions.]

## Acknowledgments

[Optional section to acknowledge any individuals, organizations, or resources that contributed to the project.]

## Contact

[Provide contact information for questions, feedback, or collaboration opportunities.]
