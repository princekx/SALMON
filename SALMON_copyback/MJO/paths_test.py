#!/usr/bin/env /data/apps/sss/environments/default-2024_09_02/bin/python
from datetime import datetime
import sys, os
sys.path.append('/home/users/prince.xavier/MJO/SALMON/MJO')
import time
import yaml
from analysis import analysis_process
from mogreps import mogreps_process
from glosea import glosea_process
from lib import mjo_utils
from display import bokeh_display

# Get the absolute path of the project root (one level up from MJO)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
print(PROJECT_ROOT)
# Path to the config file
CONFIG_FILE = os.path.join(PROJECT_ROOT, "salmon_config.yaml")
print(CONFIG_FILE)
def read_date_from_command_line():
    if len(sys.argv) != 2:
        print("Usage: python script.py <date>")
        print("Date format should be YYYY-MM-DD")
        return

    date_str = sys.argv[1]
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        print(f"Successfully created datetime object: {date_obj}")
    except ValueError as e:
        print(f"Error: {e}. Please provide the date in YYYY-MM-DD format.")

    return date_obj

def print_dict(config_values):
    for option, value in config_values.items():
        print(f'{option}: {value}')
def load_config(model=None, section=None):
    # Load the YAML file
    config_values = {}
    with open(CONFIG_FILE, "r") as file:
        config = yaml.safe_load(file)
        # Get options in the 'analysis' section and store in the dictionary
        for option, value in config[model].items():
            if isinstance(value, dict):
                for op, val in value.items():
                    config_values[op] = val
            else:
                config_values[option] = value
    print(config_values.keys())
    return config_values

if __name__ == '__main__':
    date = read_date_from_command_line()

    config_values_analysis = load_config(model='analysis')
    print(config_values_analysis)
    reader = analysis_process.AnalysisProcess(config_values_analysis)
    status = reader.check_retrieve_201_prev_days(date, parallel=False)
    #config_values = load_config('mogreps')
    #print(config_values_analysis['analysis_raw_dir'])
    sys.exit()
    #today = datetime.date.today()
    #yesterday = today - datetime.timedelta(days=1)
    #yesterday = datetime.datetime(2024, 1, 17)

    yesterday = read_date_from_command_line()

    # MOGREPS
    #do_analysis(yesterday)
    #time.sleep(60)  # Wait for 60 seconds
    #do_analysis(yesterday)
    #time.sleep(60)  # Wait for 60 seconds


    # a second run to make sure all parallel jobs are completed
    do_mogreps(yesterday)
    #time.sleep(60)  # Wait for 60 seconds
    #do_mogreps(yesterday)

    # GLOSEA
    #do_analysis(yesterday)
    #do_glosea(yesterday)
    #time.sleep(60)  # Wait for 60 seconds
    #do_glosea(yesterday)
    '''
    start_date = datetime.date(2024, 1, 31)
    end_date = datetime.date(2024, 2, 4)

    current_date = start_date
    while current_date <= end_date:
        # Glosea
        do_analysis(current_date)
        do_mogreps(current_date)
        do_mogreps(current_date)
        current_date += datetime.timedelta(days=1)
    '''


