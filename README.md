# tsm_app_data_export
Export TSM auctions items' stats from *AppData.lua* to csv, json or hdf5 files

## requirements
- [python 3.7](https://www.python.org/downloads/)
- properly configured [TSM application](https://www.tradeskillmaster.com/app/overview)

## install dependencies
> python -m pip install -r requirement.txt

## launch
> python export_tsm_auctions.py -r <path_to_app_data.lua> -o <outputdir> -f csv
  
or on windows just double click **export_tsm_auctions.py**
  
## how does it works
- find and read the *AppData.lua* files
- use a python [lua interpreter](https://github.com/scoder/lupa) to parse/interpret the data in files
- fit each realm's data into a [pandas.DataFrame](https://pandas.pydata.org/)
- export the dataframes to csv, json, ...
