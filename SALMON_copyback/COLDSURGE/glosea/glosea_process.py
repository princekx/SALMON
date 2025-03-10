import configparser
import glob
import os, sys
import numpy as np
import pandas as pd
import datetime
import iris
from iris import coords
import logging
import warnings
import uuid

# Set the global warning filter to ignore all warnings
warnings.simplefilter("ignore")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GLOProcess:

    def __init__(self, model):
        self.config_values = {}
        self.nforecasts = 15
        #self.base_cube = self.load_base_cube()

        # Navigate to the parent directory
        #parent_dir = os.getcwd()
        self.parent_dir = '/home/h03/hadpx/MJO/Monitoring_new/COLDSURGE'

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

        # We need analysis config details for concating data
        self.config_values_analysis = {}
        for option, value in config.items('analysis'):
            self.config_values_analysis[option] = value
        print(self.config_values_analysis)

    def command_helper(self, command):
        print(command)
        # Execute command
        status = os.system(command)
        print('Command Execution status: %s' % str(status))
        return status

    def subset_seasia(self, cube):
        return cube.intersection(latitude=(-10, 25), longitude=(85, 145))


    def retrieve_glosea_forecast_data(self, date, prod='prodf',
                             gs_mass_get_command='~sfcpp/bin/MassGet/gs_mass_get'):
        '''
        Retrieve Glosea data using the gs_mass_get tool.
        It first reads the data catalogue and make sure the data is available
        Then generates a mass query based on sample with modifications to date, suite etc.
        :param date:
        :type date:
        :param prod:
        :type prod:
        :param fcast_in_dir_new:
        :type fcast_in_dir_new:
        :param gs_mass_get_command:
        :type gs_mass_get_command:
        :return:
        :rtype:
        '''
        # read data catalogue
        df = pd.read_csv('~sfcpp/bin/MassGet_py3/archived_data/%s.csv' % prod)
        # select moose info for the date
        df = df.loc[(df.iyr == date.year) & (df.imon == date.month) & (df.iday == date.day)]
        if not df.empty:
            # Add a few helper columns in to the DataFrame
            df['sys'] = df['sys'].replace('op', 'operational')
            df['psnum'] = [ps[2:] for ps in df['osuite'].values]
            df.loc[(df['prod'] == ('prodf')), 'suite'] = 'forecast'
            df.loc[(df['prod'] == ('prodm')), 'suite'] = 'monthly'

            sample_query_file = self.config_values['queryfile']
            # read query sample files
            # the file to dump the new query based on sample above

            # Generate a unique query file
            local_query_file = os.path.join(self.config_values['dummy_queryfiles_dir'],
                                             f'localquery_{uuid.uuid1()}')
            fcast_in_dir = self.config_values['forecast_data_dir']
            # Replace the key words with real filter info in query file
            replacements = {'MODE': df.iloc[0].sys, 'PSNUM': df.iloc[0].psnum, 'SUITE': df.iloc[0].suite,
                            'SYSTEM': df.iloc[0].config, 'START_DATE': date.strftime("%d/%m/%Y"),
                            'FINAL_DATE': date.strftime("%d/%m/%Y"), 'OUTPUT_DIR': fcast_in_dir}
            # Replace keywords
            with open(sample_query_file) as query_infile, open(local_query_file, 'w') as query_outfile:
                for line in query_infile:
                    for src, target in replacements.items():
                        line = line.replace(src, target)
                    query_outfile.write(line)


            flag_file = os.path.join(fcast_in_dir, df.iloc[0].suite, date.strftime("%Y%m%d"),
                                     'glosea_data_retrieval_flag')

            print(flag_file)

            # Write a flag if data is written
            if not os.path.exists(flag_file):
                # linux command to execute
                command = '%s %s' % (gs_mass_get_command, local_query_file)
                print(command)

                # call the linux command
                status = self.command_helper(command)


                if status == 0:
                    command = '/usr/bin/touch %s' % flag_file
                    self.command_helper(command)
                    print('Retrieval flag: %s' %flag_file)
                elif os.path.exists(flag_file):
                    command = '/usr/bin/rm -f %s' %flag_file
                    self.command_helper(command)

                # list files
                list_command = 'ls -lrt  %s' % os.path.join(fcast_in_dir, df.iloc[0].suite, date.strftime("%Y%m%d"))
                self.command_helper(list_command)

        else:
            print('Data not found in catelogue. Not retrieving.')

    def combine_members(self, date, members):
        varnames = ['precip', 'u850', 'v850']

        for varname in varnames:
            concated_dir = os.path.join(
                self.config_values['forecast_out_dir'], varname)
            combined_allmember_file = os.path.join(concated_dir,
                                                   f'{varname}_ColdSurge_24h_allMember_{date.strftime("%Y%m%d")}.nc')

            if not os.path.exists(combined_allmember_file):
                fcast_files = [os.path.join(concated_dir,
                                          f'{varname}_nrt_{date.strftime("%Y%m%d")}_{mem}.nc') for mem in members]

                cube = iris.load_cube(fcast_files)
                print(cube)
                iris.save(cube, combined_allmember_file, netcdf_format='NETCDF4_CLASSIC')
                print(f'Written {combined_allmember_file}')
            else:
                print('%s exists. Skipping conversion.' % combined_allmember_file)


    def combine_data(self, date, prod='prodf', mem_name_start='000'):
        '''
        Data is by default retrieved as 10-day chunks which needs to be combined
        to 60 days time series
        :param date:
        :type date:
        :param prod:
        :type prod:
        :param fcast_in_dir_new:
        :type fcast_in_dir_new:
        :param gs_out_dir:
        :type gs_out_dir:
        :return:
        :rtype:
        '''
        # Combine 10-day chunks in to combined files
        suite_dic = {'prodm': 'monthly', 'prodf': 'forecast'}
        date_label = date.strftime("%Y%m%d")

        gs_out_dir = os.path.join(self.config_values['forecast_out_dir'], date_label)
        if not os.path.exists(gs_out_dir):
            os.makedirs(gs_out_dir)

        # get all members
        command = '%s/%s_*_%s_*.pp' % (os.path.join(self.config_values['forecast_data_dir'],
                                                    suite_dic[prod], date_label), prod, date_label)
        files = glob.glob(command)
        members = list(set([file.split('_')[-1].split('.')[0] for file in files]))
        members.sort()

        print('Total number of files: %s' % len(files))
        print('Ensemble members:')
        print(members)

        varnames = ['precip', 'u850', 'v850']

        time_coord = iris.coords.DimCoord(
            points=[int(t) for t in range(0, self.nforecasts*24, 24)], standard_name='forecast_period',
            units=f'days since {date.strftime("%Y-%m-%d")}')

        for varname in varnames:
            concated_dir = os.path.join(
                self.config_values['forecast_out_dir'], varname)

            if not os.path.exists(concated_dir):
                os.makedirs(concated_dir)

            cubes = []
            for m, mem in enumerate(members):
                xmem = str('%03d' % (int(mem_name_start)+m))

                fcast_file = os.path.join(concated_dir,
                                             f'{varname}_nrt_{date.strftime("%Y%m%d")}_{xmem}.nc')

                realiz_coord = iris.coords.DimCoord([int(xmem)], standard_name='realization',
                                                    var_name='realization')

                if not os.path.exists(fcast_file):
                    command = '%s/%s_*_%s_*_%s.pp' % (
                        os.path.join(self.config_values['forecast_data_dir'],
                                     suite_dic[prod], date_label), prod, date_label, mem)
                    member_files = glob.glob(command)
                    member_files.sort()

                    if varname == 'precip':
                        print('reading PRECIP...')
                        fcast_cube = iris.load_cube(member_files, 'precipitation_flux')
                        fcast_cube *= 86400.
                    if varname == 'u850':
                        print('reading U850...')
                        fcast_cube = iris.load_cube(member_files, 'x_wind')
                        fcast_cube = fcast_cube.extract(iris.Constraint(pressure=850))

                    if varname == 'v850':
                        print('reading V850...')
                        fcast_cube = iris.load_cube(member_files, 'y_wind')
                        fcast_cube = fcast_cube.extract(iris.Constraint(pressure=850))

                    # Subset for SEAsia
                    cube = self.subset_seasia(fcast_cube)
                    # Only take first 60 time points
                    cube = cube[:self.nforecasts]

                    for coord in ['realization', 'forecast_reference_time', 'forecast_period', 'time']:
                        cube.remove_coord(coord) if cube.coords(coord) else None

                    cube.add_aux_coord(realiz_coord)
                    cube.add_dim_coord(time_coord, 0)
                    print(cube)

                    iris.save(cube, fcast_file, netcdf_format='NETCDF4_CLASSIC')
                    print(f'Written {fcast_file}')
                else:
                    print('%s exists. Skipping conversion.' % fcast_file)

    def retrieve_glosea_data(self, date):

        self.retrieve_glosea_forecast_data(date, prod='prodf')
        self.retrieve_glosea_forecast_data(date, prod='prodm')

        # mem_name_start indicates the label of the first member
        self.combine_data(date, prod='prodf', mem_name_start='000')
        self.combine_data(date, prod='prodm', mem_name_start='002')



