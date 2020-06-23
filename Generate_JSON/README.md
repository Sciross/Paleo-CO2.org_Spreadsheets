# Paleo-CO2.org spreadsheet -> JSON converter

---
## Requirements
`python3` - version 3.0+ (tested with version 3.6.8)  
[`xlrd`](https://pypi.org/project/xlrd/) - available through pip (tested with version 1.2.0)  
[`json_alternate`](./../Libraries/json_alternate) - a slight variation of the python JSON library

## What does it do?
The paleo-co2.org spreadsheet -> JSON converter is designed to iterate over a folder of preverified spreadsheets formatted for [paleo-co2.org](paleo-co2.org).

It does this by:
1. Iterating over each file in the chosen directory and creating a `Dataset` object
2. Iterating over the data in each file to and creating a series of `Datapoint` objects
3. Using a JSON encoder on each `Dataset`

## How does it work?
The converter first translates the tabular format found in the paleo-co2.org spreadsheets into a class based hierarchical format. A [custom JSON encoder](/json_me) is used to convert the hierarchical format into a JSON file.

The converter takes a configuration file as input (the same style of configuration file as is used for the `Paleo-CO2.org spreadsheet Verifier`). The spreadsheets should be verified using the same configuration file and the `Paleo-CO2.org spreadsheet Verifier` before being converted to JSON.

The converter does not parse or interpret the content of the spreadsheets, instead it assumes that the file is formatted as specified in the configuration file. Data is assigned using the column names in the header rows of the spreadsheets - meaning these names must be consistent. For example, if age data has the column heading "_age_" in file and "_age_ka_" in another, the output JSON from this program will have some datapoints with an "_age_" field and some with an "_age_ka_" field. This will lead to an error when the data from the JSON is used.

## How do I run it?
Ensure the [dependencies](#Requirements) are installed, then call the [GenerateJSON_Flat.py](/GenerateJSON_Flat.py) with a configuration file as the only input. The configuration file controls the output.

```python
python3 GenerateJSON.py ./../Configuration/archive_configuration.json
```
or
```python
python3 GenerateJSON.py ./../Configuration/product_configuration.json
```

---

## The configuration file
An example of the configuration file can be found [here](./../Configuration/example.json). There are 13 top level settings, which can be subdivided as follows:

### Metadata
&nbsp;&nbsp;&nbsp;&nbsp;`version` - increment as needed

### Inputs
&nbsp;&nbsp;&nbsp;&nbsp;`root_folder` - This is folder over which the program will iterate (e.g. [/Data/Archive/](/Data/Archive/) )  
&nbsp;&nbsp;&nbsp;&nbsp; `column_header_map` : Used as a translation map for column names in the [Generate_JSON.py](./../Generate_JSON/GenerateJSON.py) script  
&nbsp;&nbsp;&nbsp;&nbsp; `proxy_name_map`  : Used as a translation map for proxy names in the [Generate_JSON.py](./../Generate_JSON/GenerateJSON.py) script  
&nbsp;&nbsp;&nbsp;&nbsp;`file_endings`: A list of file suffixes to process (e.g. [.xls,.xlsx] will process Excel files)

### Outputs
&nbsp;&nbsp;&nbsp;&nbsp;`output_file` - Determines an output JSON file if one is required (more useful for the spreadsheet -> JSON translation)
&nbsp;&nbsp;&nbsp;&nbsp;`log_file` - Filepath for the output .txt file (e.g. "log.txt")

### Settings
&nbsp;&nbsp;&nbsp;&nbsp;`header_rows` - The number of header rows in the files (e.g. 3)  
&nbsp;&nbsp;&nbsp;&nbsp;`missing_value` - The value used to represent missing data (e.g. "NA")

### Display
&nbsp;&nbsp;&nbsp;&nbsp;`use_background_colors` - Boolean which controls whether terminal printing uses background colors  
&nbsp;&nbsp;&nbsp;&nbsp;`background_colors` - A list of colors which will be used as background in terminal printing. The program will use the colors in the order they're specified. (e.g. ["grey","black"] will alternate between grey and black background)  
&nbsp;&nbsp;&nbsp;&nbsp;`use_text_colors` - Boolean which controls whether text is printed to the terminal in color  
&nbsp;&nbsp;&nbsp;&nbsp;`text_color_bits`: The resolution of the color space to use (8 and 24 are supported, Mac users should use 8 bit color)    
&nbsp;&nbsp;&nbsp;&nbsp;`text_colors` - A dictionary of colors to use for the three keywords: PASS/WARN/FAIL.  
Should take the form: `{"PASS":"#00ff00",
  "WARN":"yellow",
  "FAIL":"red"}`  
Colors beginning with # are assumed to be RGB codes (only supported in 24 bit color space)

### Data
&nbsp;&nbsp;&nbsp;&nbsp;`properties` - A definition of each column to be analysed/imported. Specified in [Properties](#Properties)


## Properties
The properties field is an array of objects, each of which corresponds to a single column in the Excel spreadsheets. There are several options which control the analysis of each column:

&nbsp;&nbsp;&nbsp;&nbsp;`name` - The name of the column, which must be found after the number of specified header rows (e.g. "proxy")  
&nbsp;&nbsp;&nbsp;&nbsp;`column` - The alphabetical column index (e.g. "A")  
&nbsp;&nbsp;&nbsp;&nbsp;`type` - The type of data in the column, valid options are `"text"`,`"numeric"`,`"DOI"` and `"reference"`  
&nbsp;&nbsp;&nbsp;&nbsp;`hard_limits` - A two element array in the form `[minimum,maximum]`. The file will fail the checks if the value is outside of these limits.  
&nbsp;&nbsp;&nbsp;&nbsp;`soft_limits` - A two element array in the form `[minimum,maximum]`. A warning will be issued if the values are outside of these limits.  
&nbsp;&nbsp;&nbsp;&nbsp;`acceptable_values` - A list of values which the data in the column can be (e.g. ["Stomata","Liverworts","Boron isotopes"])  
&nbsp;&nbsp;&nbsp;&nbsp;`match_case` - Determines whether capitalisation is considered when matching column `name` and `acceptable_values`  
&nbsp;&nbsp;&nbsp;&nbsp;`required` - Boolean that specifies whether the data is required (if `true` then the value can not be the `missing_value`)
