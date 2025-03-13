#!/usr/bin/env /data/apps/sss/environments/default-2024_09_02/bin/python
from datetime import datetime
import sys, os
import time
import yaml
from analysis import analysis_process
from mogreps import mogreps_process
from glosea import glosea_process
from lib import mjo_utils
from display import bokeh_display
import argparse

# Get the absolute path of the project root (one level up from MJO)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
print(PROJECT_ROOT)
# Path to the config file
CONFIG_FILE = os.path.join(PROJECT_ROOT, "salmon_config.yaml")
print(CONFIG_FILE)


def read_inputs_from_command_line():
    """
    Parse command-line arguments for date, area, and model.

    This function reads and validates the command-line arguments passed to the script.
    It expects a date in 'YYYY-MM-DD' format, a valid area, and a valid model.

    Returns:
        dict: A dictionary containing the parsed date, area, and model.

    Exits:
        If arguments are missing, invalid, or in the wrong format, the function prints
        usage instructions and exits the script.
    """
    parser = argparse.ArgumentParser(description="Process date, area, and model inputs.")

    parser.add_argument('-d', '--date', type=str, required=True, help='Date in YYYY-MM-DD format')
    parser.add_argument('-a', '--area', type=str, required=True, choices=['mjo', 'coldsurge', 'eqwaves', 'bsiso'],
                        help='Area of interest')
    parser.add_argument('-m', '--model', type=str, required=True, choices=['mogreps', 'glosea'], help='Model selection')

    try:
        args = parser.parse_args()
    except SystemExit:
        parser.print_help()
        sys.exit(1)

    try:
        date_obj = datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError as e:
        print(f"Error: {e}. Please provide the date in YYYY-MM-DD format.")
        parser.print_help()
        sys.exit(1)

    return {
        'date': date_obj,
        'area': args.area.lower(),
        'model': args.model.lower()
    }


def print_dict(config_values):
    if config_values:
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
    inputs = read_inputs_from_command_line()

    date = inputs['date']
    model = inputs['model']
    area = inputs['area']

    if area == 'mjo':
        # do Analysis first
        config_values_analysis = load_config(model='analysis')
        print(config_values_analysis)
        reader = analysis_process.AnalysisProcess(config_values_analysis)
        status = reader.check_retrieve_201_prev_days(date, parallel=False)
        status = reader.combine_201_days_analysis_data(date, parallel=False)

        if model == 'mogreps':
            # All ensemble members
            members = [str('%03d' % mem) for mem in range(36)]
            print(members)

            config_values = load_config(model=model)
            print(config_values)

            reader = mogreps_process.MOGProcess(config_values_analysis, config_values)
            status1 = reader.retrieve_mogreps_data(date, parallel=False)
            status1 = reader.combine_201_days_analysis_and_forecast_data(date, members, parallel=False)
            print(status1)

            mjo_proc = mjo_utils.MJOUtils(model, config_values)
            status3 = mjo_proc.run_mjo_process(date, members, model=model, parallel=False)

            #print(f'run_parallel_mjo_process: {status3}')

            rmm_display = bokeh_display.MJODisplay(model, config_values)
            rmm_display.bokeh_rmm_plot(date, members, title_prefix='MOGREPS')

        if model == 'glosea':
            config_values = load_config(model=model)
            print(config_values)
            reader = glosea_process.GLOProcess(config_values_analysis, config_values)
            reader.retrieve_glosea_data(date)

            # All ensemble members
            members = [str('%03d' % mem) for mem in range(4)]
            print(members)

            mjo_proc = mjo_utils.MJOUtils(model, config_values)
            status3 = mjo_proc.run_mjo_process(date, members, model=model, parallel=False)
            print(f'run_parallel_mjo_process: {status3}')


