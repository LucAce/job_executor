#!/usr/bin/python3
#------------------------------------------------------------------------------
# Copyright (c) 2023 LucAce
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#------------------------------------------------------------------------------
#
#   Linux Parallel Job Executor
#   Filename: job_executor.py
#
#   Functional Description:
#
#       Read in a command file containing operations to run in parallel.
#
#   Library Dependencies:
#       - psutil
#       - PyYAML
#
#   Usage:
#
#       ./job_executor.py [-h] --jobs FILE
#
#   Options:
#
#       -h, --help      Show the help message then exit
#       -jobs FILE      Use the Yaml FILE as the job items file
#
#------------------------------------------------------------------------------

import sys
sys.dont_write_bytecode = True
import os
import argparse
import datetime
import psutil
import re
import shlex
import subprocess
import threading
import time
import traceback
import yaml


#------------------------------------------------------------------------------
# Default Global Settings
#------------------------------------------------------------------------------

# Default maximum number of job items that will be run in parallel
THREADS = 4

# Default maximum wall time of a job item (in seconds)
WALL_TIME = 86400

# Methodology used to schedule job items.  Pre and post job items
# are always executed in sequential order.
#
# Strategies:
# - priority:   Schedule based on the job items priority.
# - wall_time:  Schedule based on the job items wall time. Job Items with
#               higher wall times will be executed first.
# - sequential: Schedule based on the job items sequential order.
STRATEGY = "priority"

# Default priority when using priority scheduling strategy.
# Field ignored when using wall_time or sequential scheduling strategies.
PRIORITY = 100


#------------------------------------------------------------------------------
# JobItem Class
#------------------------------------------------------------------------------
class JobItem:

    #--------------------------------------------------------------------------
    # Function: __init__
    # JobItem object constructor.
    #
    # Parameters:
    # name      - Name of the job item
    # index     - Numerical index of the job item
    # command   - Command to be executed
    # priority  - Priority of the job time (if applicable)
    # wall_time - Maximum wall time of the job item
    # stdout    - Standard Output path
    # stderr    - Standard Error path
    #--------------------------------------------------------------------------
    def __init__(self, name, index, command, priority, wall_time, stdout, stderr):
        self.name = name
        self.index = int(index)
        self.command = command
        self.priority = int(priority)
        self.wall_time = wall_time
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = 0
        self.job_state = "CREATED"

        self.create_time = datetime.datetime.now()
        self.start_time = None
        self.end_time = None

    #--------------------------------------------------------------------------
    # Function: convert2string
    # Convert an object's attributes to a string.
    #
    # Returns:
    # string - String represenation of the job item
    #--------------------------------------------------------------------------
    def convert2string(self):
        msg =  "Job Item:\n"
        msg += "  Name:      %s\n"  % self.name
        msg += "  Index:     %1d\n" % self.index
        msg += "  Command:   %s\n"  % self.command
        msg += "  Priority:  %1d\n" % self.priority
        msg += "  Wall Time: %s\n"  % self.wall_time
        msg += "  stdout:    %s\n"  % self.stdout
        msg += "  stderr:    %s\n"  % self.stderr
        msg += "  Exit Code: %s\n"  % self.exit_code
        msg += "  Job State: %s\n"  % self.job_state
        return msg


#------------------------------------------------------------------------------
# DataMap Class
#------------------------------------------------------------------------------
class DataMap:

    #--------------------------------------------------------------------------
    # Function: load_yaml
    # Parse the yaml jobs file into a Data Map.
    #
    # Parameters:
    # yaml_file - Yaml job items file path.
    #
    # Returns:
    # object - Multi-dimensional dictionary that represents the job items
    #          yaml file.
    #--------------------------------------------------------------------------
    @staticmethod
    def load_yaml(yaml_file):
        data_map = None
        with open(yaml_file, "r") as stream:
            try:
                data_map = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        return data_map


#------------------------------------------------------------------------------
# Settings Class
#------------------------------------------------------------------------------
class GlobalSettings:

    #--------------------------------------------------------------------------
    # Function: __init__
    # JobItem object constructor.
    #--------------------------------------------------------------------------
    def __init__(self):
        self.threads   = THREADS
        self.wall_time = WALL_TIME
        self.strategy  = STRATEGY
        self.priority  = PRIORITY

    #--------------------------------------------------------------------------
    # Function: load
    # Load the global attributes from the Yaml data object map.
    #
    # Parameters:
    # data_map - Yaml data object map.
    #
    # Returns:
    # object - Settings object
    #--------------------------------------------------------------------------
    @classmethod
    def load(cls, data_map):
        settings = cls()

        if "threads" in data_map["global"]:
            settings.threads = data_map["global"]["threads"]
        if "wall_time" in data_map["global"]:
            settings.wall_time = data_map["global"]["wall_time"]
        if "strategy" in data_map["global"]:
            settings.strategy = data_map["global"]["strategy"]
        if "priority" in data_map["global"]:
            settings.priority = data_map["global"]["priority"]

        return settings


#------------------------------------------------------------------------------
# JobsParser Class
#------------------------------------------------------------------------------
class JobsParser:

    #--------------------------------------------------------------------------
    # Function: parse
    # Parse Job Items, convert to an JobItem object.
    #
    # Parameters:
    # data_map - Yaml data object map
    # job_type - Job type to return
    # settings - Optional GlobalSettings object
    #
    # Returns:
    # list - A list of job items of the provided job type
    #--------------------------------------------------------------------------
    @staticmethod
    def parse(data_map, job_type, settings=None):
        job_items = []
        job_item = None
        index = 0

        # Create a setting class if one is not provided
        if settings is None:
            settings = GlobalSettings()

        # Add each job item to a list of job items of the provided job type
        for i in data_map[job_type]:

            # Required name
            if "job" in i:
                name = i["job"]
            else:
                print ("ERROR: Required \"job\" field not defined for Job Item")
                sys.exit(1)

            # Required Command
            if "command" in i:
                command = i["command"]
            else:
                print ("ERROR: Required \"command\" field not defined for Job Item")
                sys.exit(1)

            # Optional Priority
            priority = settings.priority
            if "priority" in i:
                priority = i["priority"]

            # Optional Max Wall Time
            wall_time = int(settings.wall_time)
            if "wall_time" in i:
                if isinstance(i["wall_time"], int):
                    wall_time = int(i["wall_time"])
                if isinstance(i["wall_time"], float):
                    wall_time = int(i["wall_time"])
                if isinstance(i["wall_time"], str):
                    h, m, s = i["wall_time"].split(':')
                    wall_time = int(h) * 3600 + int(m) * 60 + int(s)

            # Optional stdout
            stdout = name + ".out"
            if "stdout" in i:
                stdout = i["stdout"]

            # Optional stderr
            stderr = name + ".err"
            if "stderr" in i:
                stderr = i["stderr"]

            job_item = JobItem(name, index, command, priority, wall_time, stdout, stderr)
            job_items.append(job_item)
            index += 1

        # Validate the job names
        job_names = []
        for job in job_items:
            if job.name not in job_names:
                job_names.append(job.name)
            else:
                print("ERROR: Duplicate Job Name: \"" + job.name + "\"")
                sys.exit(1)
        job_names = []

        return job_items


#------------------------------------------------------------------------------
# JobsScheduler Class
#------------------------------------------------------------------------------
class JobsScheduler:

    #--------------------------------------------------------------------------
    # Function: sequential_schedule
    # Reorder job items list based on index.
    #
    # Parameters:
    # job_items - List of job items
    #
    # Returns:
    # job_items - Ordered list of job items
    #--------------------------------------------------------------------------
    @staticmethod
    def sequential_schedule(job_items):
        ordered_job_items = sorted(job_items, key=lambda h: (h.index))
        return ordered_job_items

    #--------------------------------------------------------------------------
    # Function: priority_schedule
    # Reorder job items list based on priority.
    #
    # Parameters:
    # job_items - List of job items
    #
    # Returns:
    # job_items - Ordered list of job items
    #--------------------------------------------------------------------------
    @staticmethod
    def priority_schedule(job_items):
        ordered_job_items = sorted(
            job_items,
            key=lambda h: (h.priority, h.name),
            reverse=True
        )
        return ordered_job_items

    #--------------------------------------------------------------------------
    # Function: wall_time_schedule
    # Reorder job items list based on wall times.
    #
    # Parameters:
    # job_items - List of job items
    #
    # Returns:
    # job_items - Ordered list of job items
    #--------------------------------------------------------------------------
    @staticmethod
    def wall_time_schedule(job_items):
        ordered_job_items = sorted(
            job_items,
            key=lambda h: (h.wall_time, h.name),
            reverse=True
        )
        return ordered_job_items


#------------------------------------------------------------------------------
# JobsScheduler Class
#------------------------------------------------------------------------------
class JobsExecuter:

    #--------------------------------------------------------------------------
    # Function: execute
    # Execute job items in parallel up to the max number of threads.
    #
    # Parameters:
    # job_items   - List of job items
    # num_threads - Number of parallel threads
    #--------------------------------------------------------------------------
    @classmethod
    def execute(cls, job_items, num_threads):
        cls = JobsExecuter()
        thread_list = []

        # Execute job items
        for job in job_items:

            # Determine if the next thread can start
            while True:
                # Get the number of running threads
                running_threads = 0
                for x in thread_list:
                    if x.is_alive():
                        running_threads += 1

                # Breakout if running threads below threshold
                if (running_threads < num_threads):
                    break
                else:
                    time.sleep(0.25)

            # Start next thread
            x = threading.Thread(target=cls.execute_job, kwargs={'job_item': job}, daemon=True)
            thread_list.append(x)
            x.start()

        # Wait for all remaining threads to complete
        for x in thread_list:
            x.join()


    #--------------------------------------------------------------------------
    # Function: execute_job
    # Execute job a item.
    #
    # Parameters:
    # job_item - Job Item to Execute
    #--------------------------------------------------------------------------
    def execute_job(self, job_item):
        command = job_item.command + " > " + job_item.stdout + " 2> " + job_item.stderr
        job_item.start_time = datetime.datetime.now()
        job_item.job_state  = "EXECUTING"

        # Update console message
        msg  = "[" + str(job_item.start_time) + "] "
        msg += "{job_state: " + job_item.job_state
        msg += ", job: " + job_item.name
        msg += ", command: " + str(command)+ "}"
        print(msg)

        # Execute Job Item
        timeout = False
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        pid = p.pid

        # Handle Time-outs and terminations
        try:
            stdout, stderr = p.communicate(timeout=int(job_item.wall_time))
        except subprocess.TimeoutExpired:
            process = psutil.Process(pid)
            for proc in process.children(recursive=True):
                proc.kill()
            process.kill()
            stdout, stderr = p.communicate()
            timeout = True

        # Capture end of job state
        job_item.exit_code = p.returncode
        job_item.end_time  = datetime.datetime.now()
        if timeout:
            job_state = "TIMEOUT"
        else:
            job_state = "COMPLETED"
        job_item.job_state = job_state

        # Update console message
        time_delta = job_item.end_time - job_item.start_time
        secs = int(time_delta.total_seconds())
        mins = secs // 60
        hrs = mins // 60
        time_delta = "%02d:%02d:%02d" % (hrs, (mins%60), (secs%60))

        msg  = "[" + str(job_item.end_time) + "] "
        msg += "{job_state: " + "%-10s" % (job_state + ",")
        msg += " job: " + job_item.name
        msg += ", exit_code: " + str(job_item.exit_code)
        msg += ", run_time: " + time_delta + "}"
        print(msg)


#------------------------------------------------------------------------------
# main()
#------------------------------------------------------------------------------
def main():

    #--------------------------------------------------------------------------
    # Gather, Parse, and Verify Command Line Switches
    #--------------------------------------------------------------------------

    # Create Option Parser
    # (--version and -h, --help is defined based on the script header)
    parser = argparse.ArgumentParser(description='Parallel Job Executor')

    # Job items file
    parser.add_argument(
        '--jobs',
        dest="jobs_file",
        action='store',
        default=None,
        required=True,
        help='Yaml Job Items File'
    )

    # Parse command line
    args = parser.parse_args()

    # Verify job items file was provided
    if not args.jobs_file:
        print("ERROR: Jobs file not provided")
        sys.exit(1)

    # Verify job items file exists
    if not os.path.exists(args.jobs_file):
        print("ERROR: Jobs file \"" + args.jobs_file + "\" does not exist")
        sys.exit(1)

    #--------------------------------------------------------------------------
    # Execute Script
    #--------------------------------------------------------------------------

    # Parse the YAML jobs file
    data_map = DataMap.load_yaml(args.jobs_file)

    # Parse the job settings
    settings = GlobalSettings.load(data_map)

    # Parse the job items
    pre_job_items  = JobsParser.parse(data_map, "pre_job_items", settings)
    job_items      = JobsParser.parse(data_map, "job_items", settings)
    post_job_items = JobsParser.parse(data_map, "post_job_items", settings)

    # Schedule/Order Job Items
    pre_job_items  = JobsScheduler.sequential_schedule(pre_job_items)
    post_job_items = JobsScheduler.sequential_schedule(post_job_items)

    if   (settings.strategy == "sequential"):
        job_items = JobsScheduler.sequential_schedule(job_items)
    elif (settings.strategy == "wall_time"):
        job_items = JobsScheduler.wall_time_schedule(job_items)
    else:
        job_items = JobsScheduler.priority_schedule(job_items)

    # Execute Job Items
    print ("\nPre Job Items:")
    JobsExecuter.execute(pre_job_items, 1)
    print ("\nJob Items:")
    JobsExecuter.execute(job_items, settings.threads)
    print ("\nPost Job Items:")
    JobsExecuter.execute(post_job_items, 1)
    return


#------------------------------------------------------------------------------
# Call main()
#------------------------------------------------------------------------------
if __name__ == '__main__':

    try:
        main()
    # Ctrl-C
    except KeyboardInterrupt as e:
        print("\nBreak Requested ... exiting")
        sys.exit(1)
    # System Exit
    except SystemExit as e:
        sys.exit(0)
    # Other Exit
    except Exception as e:
        traceback.print_exc()
        print("Unexpected exception: %s" % str(e))
