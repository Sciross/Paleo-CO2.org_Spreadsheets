import sys
import os
import math
import xlrd             # Needs install (available through pip)
import requests         # Needs install (available through pip)

sys.path.append('./../Libraries') # Add the library folder to the path
import json_alternate as json  # Needs local folder

class Verifier:
    def __init__(self):
        self.checkCommandLineInput()

        self._json_contents = ""
        self.importJSON()

        self.checkColorOptionsWork()

        self.createOutputFile()

        self.correctRootFolder()
        self.setMissingValue()

        self.defineColors()

        self.last_successful_doi = None
        self.last_successful_url_request = None

        self.analyse()

    # inputs
    def checkCommandLineInput(self): # Looks for the required input file (the JSON configuration file)
        if len(sys.argv)!=2:
            raise ValueError("There must be one input - the config file")
        if not os.path.isfile(str(sys.argv[1])):
            raise ValueError("Input file not found")
    def importJSON(self): # Opens and imports the JSON configuration file
        file = open(str(sys.argv[1]),"r")
        self.json_contents = json.load(file)
        file.close()
    def createOutputFile(self): # Creates the output log file with the name specified in the JSON configuration file
        if self.json_contents["log_file"]:
            self._log_file = open(self.json_contents["log_file"],"w") # Change option to x when ready
        else:
            self._log_file = None

    # outputs
    def writeOutput(self,content): # Generic method to write to the log file
        if self._log_file:
            self._log_file.write(content+"  \n")
    def consoleOutput(self,content,background_color="black",text_color="white",end="\n"): # Generic method to print to console with nice coloring
        clean_background_color = self.translateColor(background_color)
        clean_text_color = self.translateColor(text_color)

        escape = "\033["
        text_specifier = "38;2;"
        background_specifier = "48;2;"

        if "text_color_bits" in self.json_contents.keys() and self.json_contents["text_color_bits"]:
            bits = self.json_contents["text_color_bits"]
            if bits==8:
                text_specifier = "38;5;"
                background_specifier = "48;5;"
        print(escape+text_specifier+clean_text_color+";"+background_specifier+clean_background_color+"m"+content+escape+"0m",end=end)

    def defineColors(self): # Defines a few colors that can be accessed by name
        if "text_color_bits" in self.json_contents.keys() and self.json_contents["text_color_bits"]:
            bits = self.json_contents["text_color_bits"]
            if bits==8:
                self._known_colors = {"red":"1",
                                    "green":"2",
                                    "blue":"4",
                                    "yellow":"3",
                                    "white":"7",
                                    "grey":"8",
                                    "black":"0"}
            elif bits==24:
                self._known_colors = {"red":"255;0;0",
                                    "green":"0;255;0",
                                    "blue":"0;0;255",
                                    "yellow":"255;255;0",
                                    "white":"255;255;255",
                                    "grey":"150;150;150",
                                    "black":"0;0;0"}
            else:
                raise ValueError("Color bits must be 8 or 24 (8 for default Mac Terminal)")
    def setBackgroundColor(self): # Sets the background color of the terminal by cycling through the colors specified in the JSON configuration file (or the defaults)
        default_colors = ["black","grey"]

        if "use_background_colors" in self.json_contents.keys() and self.json_contents["use_background_colors"]:
            if "background_colors" in self.json_contents.keys() and self.json_contents["background_colors"]:
                self._current_background_color = self.json_contents["background_colors"][(self.total_so_far+(len(self.json_contents["background_colors"])-1))%len(self.json_contents["background_colors"])]
            else:
                self._current_background_color = default_colors[(self.total_so_far+(len(default_colors)-1))%len(default_colors)]
        else:
            self._current_background_color = "black"
    def getTextColor(self,name): # Returns the text color for commonly used instructions
        default_colors = {"PASS":"green","WARN":"yellow","FAIL":"red"}

        if "use_text_colors" in self.json_contents.keys() and self.json_contents["use_text_colors"]:
            if "text_colors" in self.json_contents.keys() and self.json_contents["text_colors"]:
                colors_to_use = self.json_contents["text_colors"]
            else:
                colors_to_use = default_colors
            return colors_to_use[name]
        else:
            return "black"
    def translateColor(self,color): # Translates a hex code into RGB, or the ANSI color code if required
        if color.startswith("#"): # Assume RGB
            rgb = tuple(int(color.lstrip("#")[index:index+2], 16) for index in (0, 2, 4))
            return ";".join(str(element) for element in rgb)
        elif color in self._known_colors:
            return self._known_colors[color]
        else:
            raise ValueError("Unknown color option: "+str(color))
    def checkColorOptionsWork(self): # Checks that 8 bit color is not selected with RGB color codes (8 bit required on mac)
        if ("text_color_bits" in self.json_contents.keys() and self.json_contents["text_color_bits"]):
            bits = self.json_contents["text_color_bits"]
            if bits==8:
                if ("use_text_colors" in self.json_contents.keys() and self.json_contents["use_text_colors"]) and ("text_colors" in self.json_contents.keys() and self.json_contents["text_colors"]):
                    for color in self.json_contents["text_colors"].values():
                        if color.startswith("#"):
                            raise ValueError("RGB colors incompatible with 24 bit color")
                if ("use_background_colors" in self.json_contents.keys() and self.json_contents["use_background_colors"]) and ("background_colors" in self.json_contents.keys() and self.json_contents["background_colors"]):
                    for color in self.json_contents["background_colors"].values():
                        if color.startswith("#"):
                            raise ValueError("RGB colors incompatible with 24 bit color")

    # derivative properties
    def correctRootFolder(self): # Adds a trailing slash to root folder if required
        if not self.json_contents["root_folder"].endswith("/"):
            self.json_contents["root_folder"] += "/"
    def calculateColumnIndex(self): # Iterates over properties to convert the alphabetic column indices to zero indexed values
        for each_property in self.json_contents["properties"]:
            column_index = self.getUnknownColumnIndex(each_property["name"],each_property["column"])
            if column_index is not None:
                each_property["column_number"] = self.charactersToOrd(column_index)
            else:
                each_property["column_number"] = None

    def getUnknownColumnIndex(self,name,column): # Searches through the header rows to fill in unknown column indices
        if column=="?":
            try:
                for column_number in range(self.current_sheet.ncols):
                    value = self.current_sheet.cell_value(self._current_header_rows-1,column_number)
                    if value==name:
                        return self.ordToCharacters(column_number)
            except:
                print("This should only happen if the file is shorter than the number of header rows")
            self.writeOutput("1. Could not find header '_"+name+"_'")
            return None
        return column

    def guessNumberOfHeaderRows(self): # Attempts to guess the number of header rows, first by looking for 'proxy', then by looking for anything non-empty
        try:
            index = 0
            while index<20:
                cell_contents = self.current_sheet.cell_value(index,0)
                if cell_contents!="proxy":
                    index += 1
                else:
                    return index+1
        except:
            pass

        try:
            index = 0
            while index<20:
                cell_contents = self.current_sheet.cell_value(index,0)
                if not cell_contents:
                    index += 1
                else:
                    return index+1
        except:
            return None
        return None
    def checkHeaderRows(self): # Verifies that the guess at header rows has produced something workable
        if self._current_header_rows == self.json_contents["header_rows"]:
            pass
        elif self._current_header_rows is None:
            self._current_pass = False
            self.writeOutput("Could not work out the number of header rows")
        else:
            self._current_pass = False
            if self._current_header_rows==1:
                self.writeOutput("1. There is "+str(self._current_header_rows)+" header row - there should be "+str(self.json_contents["header_rows"]))
            else:
                self.writeOutput("There are "+str(self._current_header_rows)+" header rows - there should be "+str(self.json_contents["header_rows"]))
    def guessNumberOfDataRows(self): # Iterates over spreadsheet to guess the number of data rows
        gaps = 0
        number_of_rows = 0

        while True:
            try:
                cell_contents = self.current_sheet.cell_value(self._current_header_rows + number_of_rows,0)
            except:
                break

            if not cell_contents: # If the cell is empty
                try: # Try the next cell down
                    cell_contents = self.current_sheet.cell_value(self._current_header_rows + number_of_rows + 1,0)
                    if not cell_contents: # If that cell is also empty
                        break
                    else: # But if it's not
                        gaps += 1 # Keep track of blanks
                        number_of_rows += 1 # Just continue as normal
                except: # End of file
                    pass
            else:
                number_of_rows += 1
        self._current_number_of_rows = number_of_rows-gaps # Assume gaps are in header
        self._current_gaps = gaps
    def checkFor(self,name): # Looks at whether the name is in the JSON configuration file, and whether it is not None
        if name in self._current_property.keys():
            value = self._current_property[name]
            if value is not None:
                return True
        return False
    def setMissingValue(self): # Creates an entry for the missing value i.e. what is used when the data is unknown
        if "missing_value" in self.json_contents.keys() and self.json_contents["missing_value"]:
            self._missing_value = self.json_contents["missing_value"]
        else:
            self._missing_value = None
    def checkExempt(self,value): # Returns true if the value is 'exempt' i.e. if it is the missing value
        if self._missing_value is not None:
            if value==self._missing_value:
                return True
        return False

    # actual calculations
    def checkName(self): # Checks the column name is as specified in the JSON configuration file
        value = self.current_sheet.cell_value(self._current_header_rows-1,self._current_property["column_number"])

        if self.checkFor("match_case"):
            if self._current_property["match_case"]:
                current_property_name = self._current_property["name"]
            else:
                current_property_name = self._current_property["name"].lower()
                value = value.lower()
        else:
            current_property_name = self._current_property["name"].lower()
            value = value.lower()

        if value==current_property_name:
            pass
        else:
            self._current_pass = False
            self.writeOutput("1. The title of column "+self._current_property["column"]+" should be _'"+current_property_name+"'_ but is _'"+value+"'_")
    def checkType(self): # Checks the type of each value is as specified in the JSON configuration file
        def translateType(input): # Translates the base python types in readable strings
            if isinstance(input,str):
                return "text"
            elif isinstance(input,(int,float)):
                return "numeric"
            else:
                return "unknown"
        def doCheck(self): # Container method to apply the logic
            self._type_pass = True
            output_string = ""
            actual_type = ""
            fail_count = 0

            for count in range(0,self._current_number_of_rows):
                value = self.current_sheet.cell_value(self._current_header_rows+self._current_gaps+count,self._current_property["column_number"])
                actual_type = translateType(value)

                if not self.checkExempt(value):
                    if variable_type=="text" or variable_type=="DOI" or variable_type=="reference":
                        if not isinstance(value,str):
                            self._current_pass = False
                            self._type_pass = False
                            fail_count += 1
                            output_string += str("1. The value in "+self._current_property["column"]+str(count+1+self._current_header_rows+self._current_gaps)+" should be a "+variable_type+" but is a "+actual_type+"\n")
                    elif variable_type=="numeric":
                        if not isinstance(value,(int,float)):
                            self._current_pass = False
                            self._type_pass = False
                            fail_count += 1
                            output_string += str("1. The value in "+self._current_property["column"]+str(count+1+self._current_header_rows+self._current_gaps)+" should be a "+variable_type+" but is a "+actual_type+"\n")
                    if count==self._current_number_of_rows-1:
                        output_string = output_string[:-1]
                return output_string,fail_count,actual_type

        if self.checkFor("type"):
            variable_type = self._current_property["type"]
            if variable_type not in {"text","numeric","DOI","reference"}:
                print(variable_type)
                raise ValueError("Specified type unknown, must be 'text' or 'numeric'")

            output_string,fail_count,actual_type = doCheck(self)

            if fail_count==self._current_number_of_rows:
                self.writeOutput("1. Values in column "+self._current_property["column"]+" should be a "+variable_type+" but are "+actual_type)
            elif fail_count>0:
                self.writeOutput(output_string)
    def checkRequired(self): # Looks for any cells which are the exempt value but are required
        if self.checkFor("required"):
            if self._current_property["required"]:
                for count in range(0,self._current_number_of_rows):
                    value = self.current_sheet.cell_value(self._current_header_rows+self._current_gaps+count,self._current_property["column_number"])
                    if self.checkExempt(value):
                        self._current_pass = False
                        self.writeOutput("1. The value in "+self._current_property["column"]+str(count+1+self._current_header_rows+self._current_gaps)+" is missing but required")
    def checkHardLimits(self): # Checks that the values are between the hard limits specified in the JSON configuration file
        def doCheck(self): # Container method to apply the logic
            output_string = ""
            fail_count = 0

            hard_limits = self._current_property["hard_limits"]
            for count in range(0,self._current_number_of_rows):
                value = self.current_sheet.cell_value(self._current_header_rows+self._current_gaps+count,self._current_property["column_number"])
                if not self.checkExempt(value):
                    if hard_limits[0] and value<hard_limits[0]:
                        self._current_pass = False
                        fail_count += 1
                        output_string += "1. The value in "+self._current_property["column"]+str(count+1+self._current_header_rows+self._current_gaps)+" is less than the specified minimum\n"
                    elif hard_limits[1] and value>hard_limits[1]:
                        self._current_pass = False
                        fail_count += 1
                        output_string += "1. The value in "+self._current_property["column"]+str(count+1+self._current_header_rows+self._current_gaps)+" is more than the specified maximum\n"

            if count==self._current_number_of_rows:
                output_string = output_string[:-1]

            return output_string,fail_count

        # If necessary, do the checks
        if self.checkFor("hard_limits"):
            output_string,fail_count = doCheck(self)

            if fail_count==self._current_number_of_rows:
                self.writeOutput("1. Values in column "+self._current_property["column"]+" are all outside the specified limits")
            elif fail_count>0:
                self.writeOutput(output_string)
    def checkSoftLimits(self): # Checks that the values are between the soft limits specified in the JSON configuration file
        def doCheck(self): # Container method to apply the logic
            output_string = ""
            fail_count = 0

            soft_limits = self._current_property["soft_limits"]
            for count in range(0,self._current_number_of_rows):
                value = self.current_sheet.cell_value(self._current_header_rows+self._current_gaps+count,self._current_property["column_number"])
                if not self.checkExempt(value):
                    if soft_limits[0] and value<soft_limits[0]:
                        self._current_warning = True
                        fail_count += 1
                        output_string += "The value in "+self._current_property["column"]+str(count+1+self._current_header_rows+self._current_gaps)+" is less than the suggested minimum\n"
                    elif soft_limits[1] and value>soft_limits[1]:
                        self._current_warning = True
                        fail_count += 1
                        output_string += "The value in "+self._current_property["column"]+str(count+1+self._current_header_rows+self._current_gaps)+" is more than the suggested maximum\n"

            if count==self._current_number_of_rows:
                output_string = output_string[:-1]

            return output_string,fail_count

        # If necessary, do the checks
        if self.checkFor("soft_limits"):
            output_string,fail_count = doCheck(self)

            if fail_count==self._current_number_of_rows:
                self.writeOutput("Values in column "+self._current_property["column"]+" are all outside the suggested limits")
            elif fail_count>0:
                self.writeOutput(output_string)
    def checkAcceptableValues(self): # Checks that the values in the cells are one of the acceptable values as specified in the JSON configuration file
        def doCheck(self,acceptable_values): # Container method to apply the logic
            output_string = ""
            fail_count = 0

            for count in range(0,self._current_number_of_rows):
                value = self.current_sheet.cell_value(self._current_header_rows+self._current_gaps+count,self._current_property["column_number"])

                if self.checkFor("match_case"):
                    if not self._current_property["match_case"]:
                        value = value.lower()
                else:
                    value = value.lower()

                if not self.checkExempt(value):
                    if value not in acceptable_values:
                        self._current_pass = False
                        fail_count += 1
                        output_string +=  str("1. The value in "+self._current_property["column"]+str(count+1+self._current_header_rows+self._current_gaps)+" does not match any of the acceptable values in the configuration file\n")

                if count==self._current_number_of_rows:
                    output_string = output_string[:-1]

            return output_string,fail_count

        if self.checkFor("acceptable_values"):
            if self.checkFor("match_case"):
                if self._current_property["match_case"]:
                    acceptable_values = set(self._current_property["acceptable_values"])
                else:
                    acceptable_values = [value.lower() for value in self._current_property["acceptable_values"]]
            else:
                acceptable_values = [value.lower() for value in self._current_property["acceptable_values"]]

            output_string,fail_count = doCheck(self,acceptable_values)

            if fail_count==self._current_number_of_rows:
                self.writeOutput("1. Values in column "+self._current_property["column"]+" are not any of the acceptable values")
            elif fail_count>0:
                self.writeOutput(output_string)
    def checkDOI(self): # Checks that values specified as DOI's resolve to a valid URL
        def doCheck(self): # Container method to apply the logic
            output_string = ""
            fail_count = 0
            self.last_doi_requested = None
            for count in range(0,self._current_number_of_rows):
                value = self.current_sheet.cell_value(self._current_header_rows+self._current_gaps+count,self._current_property["column_number"])

                if not self.checkExempt(value):
                    if str(value).startswith("10."): # Basic validation before attempting to access
                        if value!=self.last_doi_requested:
                            url_request =  requests.get("https://dx.doi.org/"+str(value),headers={"Accept":"text/bibliography; style=american-geophysical-union; locale=en-EN"})
                            self.last_doi_requested = value # Cache the previous DOI request to streamline the process and avoid unecessary (slow) network requests
                            if url_request.status_code!=200: # Meaning the DOI is not valid
                                self._current_pass = False
                                fail_count += 1
                                output_string +=  str("1. The value in "+self._current_property["column"]+str(count+1+self._current_header_rows+self._current_gaps)+" is not a valid DOI\n")
                    else:
                        self._current_pass = False
                        fail_count += 1
                        output_string +=  str("1. The value in "+self._current_property["column"]+str(count+1+self._current_header_rows+self._current_gaps)+" is not a properly formatted DOI\n")

                if count==self._current_number_of_rows:
                    output_string = output_string[:-1]

            return output_string,fail_count

        if self.checkFor("type") and self._current_property["type"]=="DOI":
            self._DOI_property = self._current_property
            output_string,fail_count = doCheck(self)

            if fail_count==self._current_number_of_rows:
                self.writeOutput("1. Values in column "+self._current_property["column"]+" are not valid DOIs")
            elif fail_count>0:
                self.writeOutput(output_string)
    def checkReference(self): # Checks that the values specified as DOI's resolve to a reference that matches the one in the spreadsheet
        def doCheck(self): # Container method to apply the logic
            output_string = ""
            fail_count = 0
            self.last_doi_requested = None
            self.last_url_request = None
            for count in range(0,self._current_number_of_rows):
                doi = self.current_sheet.cell_value(self._current_header_rows+self._current_gaps+count,self._DOI_property["column_number"])
                value = self.current_sheet.cell_value(self._current_header_rows+self._current_gaps+count,self._current_property["column_number"])

                if not self.checkExempt(value):
                    if str(doi).startswith("10."): # Basic validation before network request
                        if doi==self.last_doi_requested:
                            url_request = self.last_url_request
                        else:
                            url_request =  requests.get("https://dx.doi.org/"+str(doi),headers={"Accept":"text/bibliography; style=american-geophysical-union; locale=en-EN"})
                            self.last_doi_requested = doi
                            self.last_url_request = url_request
                        if url_request.status_code==200: # The request received a valid response
                            try:
                                doi_acquired_reference = url_request._content.decode("utf-8") # Should be formatted as UTF-8 (though many seem not to be)
                                if doi_acquired_reference!=value:
                                    self.last_acquired_reference = doi_acquired_reference # Cache the previous request to streamline the script (fewer network requests)

                                    self._current_warning = True
                                    fail_count += 1
                                    output_string += "1. The value in "+self._current_property["column"]+str(count+1+self._current_header_rows+self._current_gaps)+" does not match the DOI acquired reference which is: "+doi_acquired_reference+"\n"
                            except:
                                output_string += "The reference can not be decoded\n"

                if count==self._current_number_of_rows:
                    output_string = output_string[:-1]

            return output_string,fail_count

        if self.checkFor("type") and self._current_property["type"]=="reference":
            if self._DOI_property:
                output_string,fail_count = doCheck(self)

            if fail_count==self._current_number_of_rows:
                self.writeOutput("1. The content of column "+self._current_property["column"]+" does not match the information linked to the DOI, which is: \n"+self.last_acquired_reference)
            elif fail_count>0:
                self.writeOutput(output_string)

    # collective method
    def analyse(self): # This is the collective method that applies each of the methods
        print("Processing: ")
        self.total_so_far = 0
        self.total_fail = 0
        self.total_pass = 0
        self.total_warn = 0
        color_flag = False
        for this_file in os.listdir(self.json_contents["root_folder"])[::]:
            if this_file.endswith(tuple(self.json_contents["file_endings"])) and not this_file.startswith("~"):
                self.total_so_far += 1

                self.setBackgroundColor()

                self.consoleOutput(this_file,background_color=self._current_background_color,end="")

                self._current_pass = True
                self._current_warning = False
                self._type_pass = False
                self._DOI_property = None
                self.current_workbook = xlrd.open_workbook(self.json_contents["root_folder"]+this_file)
                self.current_sheet = self.current_workbook.sheet_by_index(0)

                self.writeOutput("# "+this_file)

                self._current_header_rows = self.guessNumberOfHeaderRows()
                self.checkHeaderRows()
                self.guessNumberOfDataRows()
                self.calculateColumnIndex()

                for each_property in self.json_contents["properties"]:
                    self._current_property = each_property
                    if self._current_property["column_number"] is not None:
                        self.checkName()
                        self.checkRequired()
                        self.checkType()
                        if self._type_pass:
                            self.checkHardLimits()
                            self.checkSoftLimits()
                            self.checkAcceptableValues()
                        else:
                            self.writeOutput("Could not perform further checks because variable is of incorrect type")

                for each_property in self.json_contents["properties"]:
                    self._current_property = each_property
                    if self._current_property["column_number"] is not None:
                        self.checkDOI()
                for each_property in self.json_contents["properties"]:
                    self._current_property = each_property
                    if self._current_property["column_number"] is not None:
                        self.checkReference()

                self.current_workbook.release_resources()
                self.writeOutput("")

                # Finish up
                if self._current_pass is False:
                    self.total_fail += 1
                    self.consoleOutput(" "*(50-len(this_file)-len("FAIL")),background_color=self._current_background_color,end="")
                    self.consoleOutput("FAIL",text_color=self.getTextColor("FAIL"),background_color=self._current_background_color)
                elif self._current_warning is True:
                    self.total_warn += 1
                    self.consoleOutput(" "*(50-len(this_file)-len("WARN")),background_color=self._current_background_color,end="")
                    self.consoleOutput("WARN",text_color=self.getTextColor("WARN"),background_color=self._current_background_color)
                elif self._current_pass is True:
                    self.total_pass += 1
                    self.consoleOutput(" "*(50-len(this_file)-len("PASS")),background_color=self._current_background_color,end="")
                    self.consoleOutput("PASS",text_color=self.getTextColor("PASS"),background_color=self._current_background_color)
                else:
                    print("Error")
        self.consoleOutput(" ")
        self.consoleOutput("Summary")
        self.consoleOutput("__________________")
        self.consoleOutput("PASS: "+str(round((self.total_pass/self.total_so_far)*100,2))+ "%",text_color=self.getTextColor("PASS"))
        self.consoleOutput("WARN: "+str(round((self.total_warn/self.total_so_far)*100,2))+ "%",text_color=self.getTextColor("WARN"))
        self.consoleOutput("FAIL: "+str(round((self.total_fail/self.total_so_far)*100,2))+ "%",text_color=self.getTextColor("FAIL"))

    # static methods
    @staticmethod
    def charactersToOrd(array): # Translates a string into an array of orders (for alphabetic to numeric index)
        if array is not None:
            order = 0
            for index,character in enumerate(array):
                reversed_index = len(array)-index-1
                order += (26**reversed_index)*(ord(character)-65)
            return order
        else:
            return None
    @staticmethod
    def ordToCharacters(input): # Translates an array of orders into a string (for index to alphabetic index)
        if input is not None:
            output = [input]
            while output[-1]>26:
                output += [output[-1]//26]
                output[-2] = output[-2]%26
            output_str = "".join([chr(out+65) for out in output])[::-1]
            return output_str
        else:
            return None

# Create the object and run the functions
Verifier()
