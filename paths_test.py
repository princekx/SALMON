#!/usr/bin/env /data/apps/sss/environments/default-2024_09_02/bin/python
from datetime import datetime
import sys, os
import time
import yaml
import argparse

# Get the absolute path of the project root (one level up from MJO)
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
print(PROJECT_ROOT)
# Path to the config file
CONFIG_FILE = os.path.join(PROJECT_ROOT, "salmon_config.yaml")
print(CONFIG_FILE)

import sys
import argparse
import os
from datetime import datetime


def read_inputs_from_command_line():
    """
    Parse command-line arguments for date, hour, area, and model.

    This function reads and validates the command-line arguments passed to the script.
    It expects a date in 'YYYY-MM-DD' format, an optional hour in 'HH' format (default: '00'),
    a valid area, and a valid model.

    Returns:
        dict: A dictionary containing the parsed date, hour, area, and model.

    Exits:
        If arguments are missing, invalid, or in the wrong format, the function prints
        usage instructions and exits the script.
    """
    parser = argparse.ArgumentParser(description="Process date, hour, area, and model inputs.")

    parser.add_argument('-d', '--date', type=str, required=True, help='Date in YYYY-MM-DD format')
    parser.add_argument('-t', '--time', type=str, required=False, default='00', help='Optional hour in HH format (default: 00)', choices=['00', '06', '12', '18'])
    parser.add_argument('-a', '--area', type=str, required=True, choices=['mjo', 'coldsurge', 'eqwaves', 'bsiso'],
                        help='Area of interest')
    parser.add_argument('-m', '--model', type=str, required=True, choices=['mogreps', 'glosea'], help='Model selection')

    args = parser.parse_args()

    # Validate date format
    try:
        date_obj = datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError as e:
        print(f"Error: {e}. Please provide the date in YYYY-MM-DD format.")
        parser.print_help()
        sys.exit(1)


    # Validate hour if provided
    if not args.time.isdigit() or not (0 <= int(args.time) <= 23):
        print(f"Error: Invalid hour '{args.time}'. Please provide an hour from ['00', '06', '12', '18']")
        parser.print_help()
        sys.exit(1)

    hour = int(args.time)  # Convert to integer
    date_obj = date_obj.replace(hour=hour)
    print(date_obj)

    return {
        'date': date_obj,
        'area': args.area.lower(),
        'model': args.model.lower()
    }



def print_dict(config_values):
    if config_values:
        for option, value in config_values.items():
            print(f'{option}: {value}')


def create_directories(config_values):
    """
    Reads a config.ini file, extracts directory paths, and creates the directories if they don't exist.

    Args:
        config_file (str): Path to the configuration file.
    """

    for key, path in config_values.items():
        # Skip paths that contain "moose" or have a "." (likely a file)
        if "moose" in path or "." in os.path.basename(path):
            print(f"Skipping: {path}")
            continue

        # Create directory if it doesn't exist
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Created: {path}")
        else:
            print(f"Already exists: {path}")


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

    # Create the directories in the salmon_config.yaml file unless exist
    create_directories(config_values)

    return config_values


if __name__ == '__main__':
    inputs = read_inputs_from_command_line()

    date = inputs['date']
    model = inputs['model']
    area = inputs['area']

    if area == 'mjo':
        from MJO.analysis import analysis_process as mjo_analysis_process
        from MJO.mogreps import mogreps_process as mjo_mogreps_process
        from MJO.glosea import glosea_process as mjo_glosea_process
        from MJO.lib import mjo_utils
        from MJO.display import bokeh_display as mjo_bokeh_display

        # do Analysis first
        config_values_analysis = load_config(model='analysis')
        print(config_values_analysis)
        reader = mjo_analysis_process.AnalysisProcess(config_values_analysis)
        status = reader.check_retrieve_201_prev_days(date, parallel=False)
        status = reader.combine_201_days_analysis_data(date, parallel=False)

        if model == 'mogreps':
            # All ensemble members
            members = [str('%03d' % mem) for mem in range(36)]
            print(members)

            config_values = load_config(model=model)

            reader = mjo_mogreps_process.MOGProcess(config_values_analysis, config_values)
            status1 = reader.retrieve_mogreps_data(date, parallel=False)
            status1 = reader.combine_201_days_analysis_and_forecast_data(date, members, parallel=False)

            mjo_proc = mjo_utils.MJOUtils(model, config_values)
            status3 = mjo_proc.run_mjo_process(date, members, model=model, parallel=False)

            rmm_display = mjo_bokeh_display.MJODisplay(model, config_values)
            rmm_display.bokeh_rmm_plot(date, members, title_prefix='MOGREPS')

        if model == 'glosea':
            config_values = load_config(model=model)
            print(config_values)
            reader = mjo_glosea_process.GLOProcess(config_values_analysis, config_values)
            reader.retrieve_glosea_data(date)

            # All ensemble members
            members = [str('%03d' % mem) for mem in range(4)]
            print(members)

            mjo_proc = mjo_utils.MJOUtils(model, config_values)
            status3 = mjo_proc.run_mjo_process(date, members, model=model, parallel=False)
            print(f'run_parallel_mjo_process: {status3}')

            rmm_display = mjo_bokeh_display.MJODisplay(model, config_values)
            rmm_display.bokeh_rmm_plot(date, members, title_prefix='GLOSEA')

    if area == 'coldsurge':
        from COLDSURGE.mogreps import mogreps_process as cs_mogreps_process
        from COLDSURGE.glosea import glosea_process as cs_glosea_process
        from COLDSURGE.display import coldsurge_plot_bokeh

        if model == 'mogreps':
            # All ensemble members
            members = [str('%03d' % mem) for mem in range(36)]
            print(members)

            config_values = load_config(model=model)
            print(config_values)

            reader = cs_mogreps_process.MOGProcess(config_values)
            print(reader.config_values)
            # This retrieves 35 members
            status1 = reader.retrieve_mogreps_data(date, parallel=True)
            print(status1)

            status2 = reader.process_forecast_data(date, members)

            reader = coldsurge_plot_bokeh.ColdSurgeDisplay(model, config_values)
            reader.bokeh_plot_forecast_ensemble_mean(date)
            reader.bokeh_plot_forecast_probability_precip(date)

        if model == 'glosea':
            config_values = load_config(model=model)
            print(config_values)

            reader = cs_glosea_process.GLOProcess(config_values)
            print(reader.config_values)

            status1 = reader.retrieve_glosea_data(date)
            print(status1)

            # combine all members
            members = [str('%03d' % mem) for mem in range(4)]
            status2 = reader.combine_members(date, members)

            reader = coldsurge_plot_bokeh.ColdSurgeDisplay(model, config_values)
            reader.bokeh_plot_forecast_ensemble_mean(date)
            reader.bokeh_plot_forecast_probability_precip(date)

    if area == 'eqwaves':
        from EQWAVES.analysis import analysis_process as eqw_analysis_process
        from EQWAVES.mogreps import mogreps_process as eqw_mogreps_process

        if model == 'mogreps':
            # do Analysis first
            config_values_analysis = load_config(model='analysis')
            config_values = load_config(model=model)
            print(config_values_analysis)

            # Retrieve analysis data
            reader = eqw_analysis_process.AnalysisProcess(config_values_analysis)
            status1 = reader.retrieve_analysis_data(date)
            status2 = reader.process_analysis_cubes(date)

            # Retrieve MOGREPS data
            reader = eqw_mogreps_process.MOGProcess(config_values_analysis, config_values)
            # retrieve data
            futures1 = reader.retrieve_mogreps_forecast_data(date, parallel=True)

            # process data by combining analysis and forecasts
            reader.process_mogreps_forecast_data(date)