# Paleo-CO2.org spreadsheet Verifier
A python script to verify the data in paleo-CO2.org spreadsheets

---

## Requirements
`python3` - version 3.0+ (tested with version 3.6.8)  
[`xlrd`](https://pypi.org/project/xlrd/) - available through pip (tested with version 1.2.0)  
[`requests`](https://pypi.org/project/requests/) - available through pip (tested with version 2.23.0)  
[`json_alternate`](./../Libraries/json_alternate) - a slight variation of the python JSON library

## What does it do?
The Verifier class is designed to iterate over a folder of spreadsheets formatted for [paleo-co2.org](paleo-co2.org). A configuration file is used to control which columns should be checked and what should be in those columns.

It attempts to ensure that the spreadsheets are consistent by checking:
- The number of header rows
- The title of columns
- The type of data in each specified column
- Any bounds on data
- Any suggested limits on data
- Whether the data is one of the specified acceptable values
- The format of text that has a known structure (DOIs and references)

## How does it work?
The Verifier class provided in [VerifyPaleoCO2Spreadsheets.py](/VerifyPaleoCO2Spreadsheets.py) takes a JSON configuration file (for example [archive_configuration.json](/configuration/archive_configuration.json)) as input, iterates of the necessary spreadsheets, then prints information to the terminal and produces a log file as output.

Conceptually the Verifier class works in two stages. The first is checking the requirements which pertain to all the columns in each file (e.g. the number of header rows). The second is iterating over each column, and checking the value in each row against the conditions described in the configuration file. The Verifier presumes that each file will pass the checks, but when any requirement is not met the Verifier logs the problem and marks the file as having failed the checks. In some cases, more minor infractions (e.g. not being within specific soft limits), will allow the file to pass the checks but with a warning - the details of which are written to the log file.

There are some minor complications because some features of the spreadsheets are a prerequisite for performing further verification (i.e. the number of header rows must be known, and the type of the value must be correct, for any more detailed checks to proceed). For header rows, if the number of header rows is not the same as the number in the configuration file, the Verifier will attempt to guess the right number of header rows so that further checks can proceed (and logs the issue).

The Verifier uses only one of the two output files specified in the configuration file - the log file. The log file contains detailed information on the problems found in each file (if there are any). The Verifier will also print summary information to the terminal, so that you can track progress and see some statistics on the directory.

## How do I run it?
Ensure the [dependencies](#Requirements) are installed, then call the [VerifyPaleoCO2Spreadsheets.py](/VerifyPaleoCO2Spreadsheets.py) with a configuration file as the only input.

```python
python3 VerifyPaleoCO2Spreadsheets.py ./../Configuration/archive_configuration.json
```
or
```python
python3 VerifyPaleoCO2Spreadsheets.py ./../Configuration/product_configuration.json
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
&nbsp;&nbsp;&nbsp;&nbsp;`column` - The alphabetical column index (e.g. "A"). If _?_ is used, the Verifier will attempt to search for the column with the specified `name` (it can be a different column in each spreadsheet)  
&nbsp;&nbsp;&nbsp;&nbsp;`type` - The type of data in the column, valid options are `"text"`,`"numeric"`,`"DOI"` and `"reference"`  
&nbsp;&nbsp;&nbsp;&nbsp;`hard_limits` - A two element array in the form `[minimum,maximum]`. The file will fail the checks if the value is outside of these limits.  
&nbsp;&nbsp;&nbsp;&nbsp;`soft_limits` - A two element array in the form `[minimum,maximum]`. A warning will be issued if the values are outside of these limits.  
&nbsp;&nbsp;&nbsp;&nbsp;`acceptable_values` - A list of values which the data in the column can be (e.g. ["Stomata","Liverworts","Boron isotopes"])  
&nbsp;&nbsp;&nbsp;&nbsp;`match_case` - Determines whether capitalisation is considered when matching column `name` and `acceptable_values`  
&nbsp;&nbsp;&nbsp;&nbsp;`required` - Boolean that specifies whether the data is required (if `true` then the value can not be the `missing_value`)
