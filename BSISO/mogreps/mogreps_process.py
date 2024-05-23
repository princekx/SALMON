import configparser
import datetime
import multiprocessing
import concurrent
import os
import subprocess
import sys
import iris
import numpy as np
import logging
import warnings
import pandas as pd
from iris.coord_categorisation import add_year, \
    add_month_number, add_day_of_month, add_day_of_year
# Set the global warning filter to ignore all warnings
warnings.simplefilter("ignore")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MOGProcess:

    def __init__(self, model):
        self.config_values = {}
        self.num_prev_days = 201
        self.nforecasts = 7
        self.nanalysis2write = 40

        # Navigate to the parent directory
        self.parent_dir = '/net/home/h03/hadpx/MJO/Monitoring_new/BSISO'

        # Specify the path to the config file in the parent directory
        config_path = os.path.join(self.parent_dir, 'config.ini')
        print(config_path)

        # Read the configuration file
        config = configparser.ConfigParser()
        config.read(config_path)

        # Get options in the 'model' section and store in the dictionary
        for option, value in config.items(model):
            self.config_values[option] = value
        print(self.config_values)

    def print_progress_bar(self, iteration, total):
        percentage = 100 * iteration / total
        progress_bar = f"Progress: [{percentage:.2f}%]"
        print(progress_bar, end="\r")

    def prepare_calendar(self, cube):
        # Setting up the dates on data
        for coord_name, coord_func in [('year', iris.coord_categorisation.add_year),
                                       ('month_number', iris.coord_categorisation.add_month_number),
                                       ('day_of_month', iris.coord_categorisation.add_day_of_month),
                                       ('day_of_year', iris.coord_categorisation.add_day_of_year),
                                       ('hour', iris.coord_categorisation.add_hour)]:
            if not cube.coords(coord_name):
                coord_func(cube, 'forecast_time', name=coord_name)
        return cube

    def create_dates_df(self, cube):
        cube = self.prepare_calendar(cube)
        cube_dates_dt = [datetime.datetime(y, m, d) for y, m, d in zip(cube.coord('year').points,
                                                                       cube.coord('month_number').points,
                                                                       cube.coord('day_of_month').points)]
        # Extract year, month, and day from each datetime object
        data = {
            'Year': [dt.year for dt in cube_dates_dt],
            'Month': [dt.month for dt in cube_dates_dt],
            'Day': [dt.day for dt in cube_dates_dt]
        }

        # Create a Pandas DataFrame
        df = pd.DataFrame(data)

        # Create a new 'date' column with datetime objects
        df['date'] = pd.to_datetime(df[['Year', 'Month', 'Day']])
        return df

    def read_bsiso_eofs(self):
        eof_data_file = os.path.join(self.parent_dir, 'data', 'BSISO.EOFstruc.data')
        eofs = pd.read_csv(eof_data_file, delim_whitespace=True)

        nlat = eofs['YY'].max()
        nlon = eofs['XX'].max()
        lons = np.linspace(40, 160, nlon)
        lats = np.linspace(-10., 40., nlat)

        comb_eof1 = np.concatenate((eofs.OLR1, eofs.U8501), axis=0)
        comb_eof2 = np.concatenate((eofs.OLR2, eofs.U8502), axis=0)

        return comb_eof1, comb_eof2

    def calculate_bsiso_phase(self, rmm1, rmm2):
        # Calculate the phase angle
        phase_angle = np.arctan2(rmm2, rmm1)

        # Convert negative angles to positive
        phase_angle = np.where(phase_angle < 0, phase_angle + 2 * np.pi, phase_angle)

        # Define the phase categories based on the phase angle
        phase = np.zeros(len(phase_angle), dtype=int)
        phase = np.where((phase_angle >= 0) & (phase_angle < np.pi / 4), 5,
                         np.where((phase_angle >= np.pi / 4) & (phase_angle < np.pi / 2), 6,
                                  np.where((phase_angle >= np.pi / 2) & (phase_angle < 3 * np.pi / 4), 7,
                                           np.where((phase_angle >= 3 * np.pi / 4) & (phase_angle < np.pi), 8,
                                                    np.where((phase_angle >= np.pi) & (phase_angle < 5 * np.pi / 4), 1,
                                                             np.where((phase_angle >= 5 * np.pi / 4) & (
                                                                     phase_angle < 3 * np.pi / 2), 2,
                                                                      np.where((phase_angle >= 3 * np.pi / 2) & (
                                                                              phase_angle < 7 * np.pi / 4), 3,
                                                                               4)))))))

        return phase

    def load_and_constrain_data(self, filenames):
        """Loads and applies regional constraints to the data cubes."""
        reg_constraints = iris.Constraint(latitude=lambda cell: -10 <= cell <= 40) & iris.Constraint(
            longitude=lambda cell: 40. <= cell <= 160.)
        try:
            olr_cube = iris.load_cube(filenames['olr']).extract(reg_constraints)
            u850_cube = iris.load_cube(filenames['u850']).extract(reg_constraints)
            return olr_cube, u850_cube
        except:
            pass

    def assign_mem_and_labels(self, pcs, mem, ntime, nforecasts):
        """Assign memory and label columns based on provided configurations."""
        pcs['mem'] = [mem] * len(pcs)
        pcs['label'] = ['analysis'] * (ntime - nforecasts) + ['forecast'] * nforecasts
        return pcs

    def compute_bsiso_index_mem(self, date, mem, anom_120_filenames, bsiso_file_name):
        """Compute the BSISO index for given data, and write to CSV.

        Args:
            date (datetime): The date for which to compute the index.
            mem (str): Memory or identification tag for the run.
            anom_120_filenames (dict): Filenames for the OLR and U850 data.
            bsiso_file_name (str): Output filename for the CSV.
        """
        date_label = date.strftime("%Y%m%d")

        # read normalisation coefficients
        df = pd.read_csv(os.path.join(self.parent_dir, 'data', 'BSISO_coefficients.csv'))

        # Read the OLR and u850 data - 3 harmonics and 120 days running mean removed
        olr_cube, u850_cube = self.load_and_constrain_data(anom_120_filenames)

        # Normalization by area averaged temporal standard deviation over the Asian region
        olr_cube /= df['olr_sd_x']
        u850_cube /= df['u850_sd_x']

        ntime, nlat_cube, nlon_cube = olr_cube.shape
        # Create the template for PCs
        pcs_df = self.create_dates_df(olr_cube)

        olr_resh = np.reshape(olr_cube.data, (ntime, -1))
        u850_resh = np.reshape(u850_cube.data, (ntime, -1))

        # Combining the data along the lat-lon dimensions
        comb_fcast_data = np.concatenate((olr_resh, u850_resh), axis=1)

        # Read Predefined EOF structures
        comb_eof1, comb_eof2 = self.read_bsiso_eofs()

        # Assuming comb_eof1 is a 1D array of shape (2058,)
        # and comb_fcast_data is a 2D array of shape (261, 2058)
        pcs_df['PC1'] = np.dot(comb_fcast_data, comb_eof1)
        pcs_df['PC2'] = np.dot(comb_fcast_data, comb_eof2)

        # Normalise PC1 and PC2 by predefined values 12, 10
        pcs_df['PC1'] = pcs_df['PC1'] / df['pc1_sd'].values
        pcs_df['PC2'] = pcs_df['PC2'] / df['pc2_sd'].values

        pcs_df['8_phases'] = self.calculate_bsiso_phase(pcs_df['PC1'].values, pcs_df['PC2'].values)
        pcs_df['amp'] = np.sqrt(pcs_df['PC1'].values ** 2 + pcs_df['PC2'].values ** 2)
        pcs_df['mem'] = [mem for i in range(len(pcs_df))]

        pcs_df = self.assign_mem_and_labels(pcs_df, mem, ntime, self.nforecasts)
        pcs_df.to_csv(bsiso_file_name, index=False)
        print(f'DataFrame has been successfully written to {bsiso_file_name}')

    def bsiso_index_compute_main(self, date, members):
        bsiso_archive_dir = os.path.join(self.config_values['fcast_out_archive_dir'],
                                         f'{date.strftime("%Y%m%d")}')
        if not os.path.exists(bsiso_archive_dir):
            os.makedirs(bsiso_archive_dir)

        for m, mem in enumerate(members):
            self.print_progress_bar(m, len(members))
            bsiso_index_file_name = os.path.join(bsiso_archive_dir,
                                                 f'BSISO.{date.strftime("%Y%m%d")}.fcast.{mem}.txt')

            if not os.path.exists(bsiso_index_file_name):
                anom_120_filenames = {}
                for varname in ['olr', 'u850']:
                    f_name = os.path.join(self.config_values['forecast_out_dir'],
                                                               varname,
                                                               f'{varname}_120dm_40sn_nrt_{date.strftime("%Y%m%d")}_{mem}.nc')
                    if os.path.exists(f_name):
                        anom_120_filenames[varname] = f_name
                    else:
                        anom_120_filenames[varname] = None

                self.compute_bsiso_index_mem(date, mem, anom_120_filenames, bsiso_index_file_name)
            else:
                print(f'{bsiso_index_file_name} exists. Skip.')

