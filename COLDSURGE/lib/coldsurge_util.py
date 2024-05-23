import configparser
import datetime
import multiprocessing
import os
import subprocess
import sys
import uuid
import iris
import iris.coord_categorisation
import numpy as np
import pandas as pd
import concurrent
from concurrent.futures import ProcessPoolExecutor, wait, ALL_COMPLETED
import logging

class ColdSurgeUtils:
    def __init__(self, model):
        self.config_values = {}
        self.num_prev_days = 201
        # 40 days of anlysis to be written out with the forecasts
        self.nanalysis2write = 40
        if model == 'glosea':
            self.nforecasts = 30
        else:
            self.nforecasts = 7

        # Navigate to the parent directory
        parent_dir = os.getcwd()

        # Specify the path to the config file in the parent directory
        config_path = os.path.join(parent_dir, 'config.ini')
        print(config_path)

        # Read the configuration file
        config = configparser.ConfigParser()
        config.read(config_path)

        # Get options in the 'analysis' section and store in the dictionary
        for option, value in config.items(model):
            self.config_values[option] = value
        # print(self.config_values)


