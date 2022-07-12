from xdrlib import ConversionError
from colorama import init, Fore, Back, Style
import sys
import psutil # pip install -r requirements.txt
import time
import subprocess
import os
import traceback
import threading

init() # initialize colorama

"""
Issues:
- stuff needs to be thread-safe
"""

# CTRL+F "--WARN--" to find stuff that needs fixing

VERSION="1.0.1"
TIME_DELAY = 5 # time delay between spawning in each round of threads /seconds
CHECK_ACTIVE_DELAY = 0.5 # time delay between checking if the program is still active /seconds
CHECK_TIMEOUT = 30 # after this has finished, it is concluded that the malware is still active and not stopped by the antivirus
HELP_MENU = f"""
Options:
    -h, --help      Show this help menu
    -v, --version   Show version
    -f, --file      File to launch
    -d, --directory Directory from which to launch files (only in the first level)
    -r, --recursive Recursively launch files from any depth within a folder
    -e, --extension Extension to filter by (default: all)
    -t, --thread    Number of threads to use for launching the files every {TIME_DELAY} seconds (default 1)
    -l, --log       Save the output log (default: none)
    -o, --output    Output folder to write details to, previous details will be overwritten(default: none)

ie.
    malx.py -d samples/ -e .txt
"""

class Threads:
	def newThread(function, args=()):
		new_thread = threading.Thread(target=function, args=args) # error handle threads so they output into log file
		new_thread.start()
		return new_thread

class Tools:
    def countAllInstances(listSearch, items) -> int:
        count = 0
        for item in items:
            count += listSearch.count(item)
        return count

class ErrorIdentifier(object):
    def __init__(self, details = "This is an object assigned to a dict key if the key is invalid"):
        self.details = details

class TimeoutError(Exception):
    pass

class Analysis:
    def isStillActive(pid) -> bool:
        try:
            psutil.Process(pid)
            return True
        except psutil.NoSuchProcess:
            return False
    def waitUntilInactive(pid, time_delay = CHECK_ACTIVE_DELAY, timeout = CHECK_TIMEOUT) -> int:
        iterations = 0
        while Analysis.isStillActive(pid):
            time.sleep(time_delay)
            iterations += 1
            if iterations * time_delay >= timeout:
                raise TimeoutError("Timeout reached")
        return (iterations*time_delay) - (CHECK_ACTIVE_DELAY/2) # time taken to be inactive, average betweeen error intervals

class Interface:
    def catchAsserts(func):
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except AssertionError as e:
                print(f"Invalid options: {e}")
                sys.exit(1)
        return wrapper
    def catchIndexErrors(func):
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except IndexError:
                print(f"Invalid options: The option you provideed is missing a corresponding value")
                sys.exit(1)
        return wrapper
    def catchErrors(ErrorIdentifier, msg):
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    func(*args, **kwargs)
                except ErrorIdentifier as e:
                    print(msg)
                    sys.exit(1)
            return wrapper
        return decorator
    @catchAsserts
    def main(CHECK_ACTIVE_DELAY=CHECK_ACTIVE_DELAY) -> None: 
        ARGS = sys.argv[1:]
        class ArgsParser(object):
            def __init__(self, ARGS, CHECK_ACTIVE_DELAY=CHECK_ACTIVE_DELAY, CHECK_TIMEOUT=CHECK_TIMEOUT, TIME_DELAY=TIME_DELAY): 
                self.ARGS = ARGS
                self.CONFIG = {}
                self.CHECK_ACTIVE_DELAY = CHECK_ACTIVE_DELAY
                self.CHECK_TIMEOUT = CHECK_TIMEOUT
                self.THREAD_DELAY = TIME_DELAY
                self.result = ""
                self.debuglog = ""
                self.lowercaseOptions()
                self.checkNeedsHelp()
                self.validateArgs()
                self.checkVersionArg()
                self.launch()
            # Logging mechanisms
            def debug(self, text) -> None: # debugging info to be sent straight to the log if provided
                # --WARN-- This is a temporary solution, needs to be thread-safe
                print(text)
                self.debuglog += text + "\n"
            def info(self, text) -> None: # info to be sent to the analysis summary
                # --WARN-- This is a temporary solution, needs to be thread-safe
                self.result += text + "\n"
            def showresult(self):
                print(self.result)
                if self.CONFIG["log"]:
                    with open(self.CONFIG["log"], "w") as log:
                        log.write(f"Warning: Some characters may not load in notepad. Read the contents of this file in terminal.\nExecuted: \n{self.debuglog} \n\nResult:\n{self.result}")
                    print(f"Log file saved to {self.CONFIG['log']}")
            def lowercaseOptions(self): 
                for i in range(len(self.ARGS)):
                    if self.ARGS[i][0] == "-":
                        self.ARGS[i] = self.ARGS[i].lower()
            def checkNeedsHelp(self):
                if len(self.ARGS) == 0 or "-h" in self.ARGS or "--help" in self.ARGS:
                    print(HELP_MENU)
                    sys.exit(0)
            def validateArgs(self): # check for invalid arguments and assert before proceeding
                assert Tools.countAllInstances(self.ARGS, ["-f","--file","-d","--directory","-r","--recursive"]) <= 1, "Only one file/directory/recursive flag can be used at one time"
                assert not(Tools.countAllInstances(self.ARGS, ["-f","--file","-d","--directory","-r","--recursive"]) == 0 and Tools.countAllInstances(self.ARGS,["-v","--version"]) == 0), "No operation specified"
            def checkVersionArg(self):
                if "-v" in self.ARGS or "--version" in self.ARGS:
                    print(f"Malx version {VERSION}")
                    sys.exit(0)
            def checkForErrorIdentifier(self, inputDict):
                for key in inputDict.keys():
                    if isinstance(inputDict[key], ErrorIdentifier):
                        raise AssertionError("Options were not in a supported format, or were not found")
            @Interface.catchIndexErrors
            @Interface.catchErrors(ValueError, "Invalid options: An option you provided is of the wrong type")
            def launch(self):
                self.CONFIG = {
                    "mode": "file" if "-f" in self.ARGS or "--file" in self.ARGS else "directory" if "-d" in self.ARGS or "--directory" in self.ARGS else "recursive" if "-r" in self.ARGS or "--recursive" in self.ARGS else ErrorIdentifier(),
                    "location": self.ARGS[self.ARGS.index("-f") + 1] if "-f" in self.ARGS or "--file" in self.ARGS else self.ARGS[self.ARGS.index("-d") + 1] if "-d" in self.ARGS or "--directory" in self.ARGS else self.ARGS[self.ARGS.index("-r") + 1] if "-r" in self.ARGS or "--recursive" in self.ARGS else ErrorIdentifier(),
                    "extension": self.ARGS[self.ARGS.index("-e") + 1] if "-e" in self.ARGS or "--extension" in self.ARGS else None,
                    "log": self.ARGS[self.ARGS.index("-l") + 1] if "-l" in self.ARGS or "--log" in self.ARGS else None,
                    "output": self.ARGS[self.ARGS.index("-o") + 1] if "-o" in self.ARGS or "--output" in self.ARGS else None,
                    "threads": int(self.ARGS[self.ARGS.index("-t") + 1]) if "-t" in self.ARGS or "--thread" in self.ARGS else 1
                }
                self.checkForErrorIdentifier(self.CONFIG)#
                self.startOperation()
            def startOperation(self):
                # output useful info
                print(f"{Back.GREEN}Launch settings{Back.RESET}")
                for key in self.CONFIG.keys():
                    print(f"{Fore.GREEN}{key.capitalize()}: {self.CONFIG[key]}{Fore.RESET}")
                print(f"\n{Back.GREEN}Output{Back.RESET}")
                # start it
                if self.CONFIG["mode"] == "file":
                    self.launchFile()
                elif self.CONFIG["mode"] == "directory":
                    self.launchDirectory()
                elif self.CONFIG["mode"] == "recursive":
                    self.launchRecursive()
                print(f"\n{Back.GREEN}Result{Back.RESET}")
                self.showresult()
            def analyseFile(self, file):
                details = {
                    "filename": file,
                    "timeTaken": 0, # time taken in seconds to be terminated
                    "terminated": False # was the program terminated by the antivirus 
                }
                try:
                    process = subprocess.Popen(file)
                    details["timeTaken"] = Analysis.waitUntilInactive(process.pid)
                    details["terminated"] = True
                except TimeoutError:
                    details["timeTaken"] = self.CHECK_TIMEOUT
                return details
            def launchFile(self, customFileName=None):
                filename = customFileName if customFileName else self.CONFIG["location"]
                self.debug(f"{Fore.RED}File: {filename}{Fore.RESET}")
                try:
                    details = self.analyseFile(filename)
                except:
                    self.info(f"{Fore.RED}File: {filename}{Fore.RESET}")
                    self.info(f"{Fore.RED}Error: {traceback.format_exc()}{Fore.RESET}")
                    return
                self.info(f"""Executing file "{filename}"
{"Time taken: "+str(details["timeTaken"])+" seconds (terminated)" if details["terminated"] else "Timed out: "+str(details["timeTaken"])+" seconds"}
Time tolerance: ±{self.CHECK_ACTIVE_DELAY/2} seconds\n""")
            def scanFileList(self, scan_files):
                threads = []
                THREAD_CONFLICT_DELAY = 0.05 # delay in seconds to prevent threading conflicts, particularly with output logging
                thread_count = 0
                print(f"Estimated time: { THREAD_CONFLICT_DELAY*len(scan_files) + int(len(scan_files)/self.CONFIG['threads'])*5 + self.CHECK_TIMEOUT }s")
                for file in scan_files:
                    threads.append(Threads.newThread(lambda: self.launchFile(file)))
                    thread_count += 1
                    time.sleep(self.THREAD_DELAY if thread_count % self.CONFIG["threads"] == 0 else THREAD_CONFLICT_DELAY) # where THREAD_DELAY is the delay between bulk spawning threads
                # wait for thread completion
                print("Waiting for results...")
                for thread in threads:
                    thread.join()
            def launchDirectory(self): #NB self.CONFIG["location"] is the directory
                print("Indexing directory...")
                total_files = os.listdir(self.CONFIG["location"])
                scan_files = []
                for filename in total_files:
                    if os.path.isfile(self.CONFIG["location"]+filename):
                        if self.CONFIG["extension"] is None or self.CONFIG["extension"] in filename:
                            scan_files.append(self.CONFIG["location"]+filename)
                print(f"{len(scan_files)} file(s) found")
                self.scanFileList(scan_files)
            def searchDirectory(self, directory):
                total_files = []
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if self.CONFIG["extension"] is None or self.CONFIG["extension"] in file:
                            total_files.append(os.path.join(root, file))
                return total_files
            def launchRecursive(self):
                print("Indexing directories...")
                scan_files = self.searchDirectory(self.CONFIG["location"])
                print("{} file(s) found".format(len(scan_files)))
                self.scanFileList(scan_files)
        ArgsParser(ARGS)

if __name__ == "__main__":
    Interface.main()