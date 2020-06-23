import sys
import os
import math
import xlrd # Dependency (can be installed through pip)

sys.path.append('./../Libraries') # Add the library folder to the path
import json_alternate as json  # Needs local

class FlatEncoder(json.JSONEncoder): # Encodes an array of objects into a JSON array of objects
    def default(self,input):
        if isinstance(input,Dataset):
            datapoints_as_dictionaries = tuple(input.convertDatapointsToFlatDictionaries()) # Use a tuple to prevent additional brackets
            return datapoints_as_dictionaries

class Compilation(): # Class to contain multiple datasets
    def __init__(self):
        self.checkCommandLineInput() # Ensure there is an input configuration file
        self.importConfiguration() # Import the configuration file
        self.importColumnHeaderMap() # Import the column header map
        self.importProxyNameMap() # Import the proxy name map

        self.correctRootFolder() # Append a / to the root folder if necessary

        self.doTranslation() # Performs the main function
    def checkCommandLineInput(self): # Looks for the required input file (the JSON configuration file)
        if len(sys.argv)!=2:
            raise ValueError("There must be one input - the config file")
        if not os.path.isfile(str(sys.argv[1])):
            raise ValueError("Input file not found")
    def importConfiguration(self): # Opens and imports the JSON configuration file
        file = open(str(sys.argv[1]),"r")
        self.configuration = json.load(file)
        file.close()
    def importColumnHeaderMap(self): # Opens and imports the JSON column header map (if it exists)
        if "column_header_map" in self.configuration.keys() and self.configuration["column_header_map"]:
            file = open(str(self.configuration["column_header_map"]),"r")
            self.column_header_map = json.load(file)
            file.close()
        else:
            self.column_header_map = None # Set to None if there is no file
    def importProxyNameMap(self): # Opens and imports the JSON proxy name map (if it exists)
        if "proxy_name_map" in self.configuration.keys() and self.configuration["proxy_name_map"]:
            file = open(str(self.configuration["proxy_name_map"]),"r")
            self.proxy_name_map = json.load(file)
            file.close()
        else:
            self.proxy_name_map = None

    def correctRootFolder(self): # Adds a trailing slash to root folder if required
        if not self.configuration["root_folder"].endswith("/"):
            self.configuration["root_folder"] += "/"
    def shouldBeAnalysed(self,file): # Checks the file doesn't start with ~ to ignore Windows temporary files, or . to ignore hidden files
        if file[0]!="~" and file[0]!=".":
            return True
        else:
            return False

    def doTranslation(self): # Main method to perform the translation
        self.datasets = [] # Create and empty list to hold datasets
        for file in os.listdir(self.configuration["root_folder"]): # For each file in the data directory
            if self.shouldBeAnalysed(file):
                self.datasets.append(Dataset(filename=file,configuration=self.configuration,column_header_map=self.column_header_map,proxy_name_map=self.proxy_name_map)) # Append a dataset with the necessary information for processing

                # Run methods for data collection
                self.datasets[-1].addDatapoints()

                print("Added {} datapoints from {}".format(len(self.datasets[-1].datapoints),file))
                self.datasets[-1]._excel_workbook.release_resources()

        with open(self.configuration["output_file"],'w',encoding='utf-8') as file:
            json.dump(self.datasets,file,cls=FlatEncoder,indent=4,ensure_ascii=False)
class Dataset(): # Class to contain multiple datapoints
    def __init__(self,filename,configuration,column_header_map=None,proxy_name_map=None):
        self.filename = filename
        self.configuration = configuration
        self.column_header_map = column_header_map
        self.proxy_name_map = proxy_name_map

        self.filepath = self.configuration["root_folder"]+self.filename

        self.datapoints = []

        self._sheet = []
        self._header_rows = self.configuration["header_rows"]

    def addDatapoints(self):
        self.openFirstSheet()
        self.collectColumns()
        self.replaceNA()
        self.parseToDatapoints()

    def openFirstSheet(self):
        self._excel_workbook = xlrd.open_workbook(self.filepath)
        self._sheet = self._excel_workbook.sheet_by_index(0)
    def collectColumns(self): # Create a variable which has the requesite columns as determined by the configuration file
        output_dictionary = {}
        for column in self.configuration["properties"]:
            column_name = self.correctColumnName(column["name"])
            column_index = self.getUnknownColumnIndex(column["name"],column["column"])
            if column_index:
                output_dictionary[column_name] = self._sheet.col_values(self.charactersToOrd(column_index))[self._header_rows:]
        self.data_by_column = output_dictionary
    def replaceNA(self): # Replaces NA in the spreadsheets with None
        for datapoint_index in range(len(self.data_by_column["proxy"])):
            for column in self.data_by_column:
                if self.data_by_column[column][datapoint_index]=="NA":
                    self.data_by_column[column][datapoint_index] = None # Replace NA with None
    def parseToDatapoints(self): # Convert the column dictionary into a list of Datapoints
        for datapoint_index in range(len(self.data_by_column["proxy"])):
            self.datapoints += [Datapoint()]
            for column in self.data_by_column:
                self.datapoints[-1].__dict__[column] = self.data_by_column[column][datapoint_index]
    def correctColumnName(self,name): # Uses a column header map, if one is available, to translate header row names
        if self.column_header_map and name in self.column_header_map:
            return self.column_header_map[name]
        return name
    def correctProxyName(self,name): # Uses a proxy name map, if one is available, to translate proxy names to match website
        if self.proxy_name_map and name in self.proxy_name_map:
            return self.proxy_name_map[name]
        return name
    def getUnknownColumnIndex(self,name,column): # Searches through the header rows to fill in unknown column indices
        if column=="?":
            try:
                for column_number in range(self._sheet.ncols):
                    value = self._sheet.cell_value(self._header_rows-1,column_number)
                    if value==name:
                        return self.ordToCharacters(column_number)
            except:
                pass
                #print("The number of header rows needs to be fixed before this file will be imported properly")
            #print("Column '"+name+"' not found")
            return None
        return column

    # Output
    def convertDatapointsToFlatDictionaries(self): # Returns a list of dictionaries to represent each datapoint
        datapoint_dictionary_list = []
        for currentPoint in self.datapoints:
            if currentPoint.proxy:
                currentPoint.proxy = self.correctProxyName(currentPoint.proxy)
                datapoint_dictionary_list.append({**currentPoint.convertToDictionary()})
        return datapoint_dictionary_list
    def toJSON(self): # Saves the file using the encoding and sorting
        return json.dumps(self, default=lambda o: o.__dict__,sort_keys=True, indent=4)

    # static methods
    @staticmethod
    def charactersToOrd(array): # Translates a string into an array of orders (for alphabetic to numeric index)
        order = 0
        for index,character in enumerate(array):
            reversed_index = len(array)-index-1
            order += (26**reversed_index)*(ord(character)-65)
        return order
    @staticmethod
    def ordToCharacters(input): # Translates an array of orders into a string (for numberic to alphabetic index)
        output = [input]
        while output[-1]>26:
            output += [output[-1]//26]
            output[-2] = output[-2]%26
        output_str = "".join([chr(out+65) for out in output])[::-1]
        return output_str
class Datapoint(): # Class to represent each datapoint
    def __init__(self): # No need to create any content as it is done dynamically based on the configuation file
        pass
    def __repr__(self): # Print each of the properties and their value to display
        output_string = ""
        for the_property in self.__dict__.keys():
            output_string += the_property+" = "+str(self.__dict__[the_property])+"\n"
        return output_string

    def convertToDictionary(self): # Return the dictionary property when requested
        return self.__dict__

compilation = Compilation()
