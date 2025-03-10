import configparser
import datetime
import multiprocessing
import concurrent
import subprocess
import uuid
from iris.fileformats.pp import load_pairs_from_fields
import numpy as np
import logging
import warnings
import os, sys
import scipy.ndimage as ndimage
from skimage import measure
#from tqdm import tqdm
import pandas as pd
import iris

# Set the global warning filter to ignore all warnings
warnings.simplefilter("ignore")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MOGProcess:

    def __init__(self, model):
        self.config_values = {}

        # Navigate to the parent directory
        self.parent_dir = '/home/h03/hadpx/MJO/Monitoring_new/FEATURES'

        # Specify the path to the config file in the parent directory
        config_path = os.path.join(self.parent_dir, 'config.ini')

        # Read the configuration file
        config = configparser.ConfigParser()
        config.read(config_path)

        # Get options in the 'model' section and store in the dictionary
        for option, value in config.items(model):
            self.config_values[option] = value

        # We need analysis config details for concating data
        self.config_values_analysis = {}
        for option, value in config.items('analysis'):
            self.config_values_analysis[option] = value

    def get_all_members(self, hr):
        if hr == 12:
            return [str('%02d' % mem) for mem in range(18)]
        elif hr == 18:
            return [str('%02d' % mem) for mem in range(18, 35)] + ['00']
    def print_progress_bar(self, iteration, total):
        percentage = 100 * iteration / total
        progress_bar = f"Progress: [{percentage:.2f}%]"
        print(progress_bar, end="\r")


    def retrieve_fc_data_parallel(self, date, hr, fc, digit2_mem):
        print('In retrieve_fc_data_parallel()')
        moosedir = os.path.join(self.config_values['moose_dir'], f'{date.strftime("%Y%m")}.pp')
        digit3_mem = '035' if (hr == 18 and digit2_mem == '00') else str('%03d' % int(digit2_mem))

        remote_data_dir = os.path.join(self.config_values['forecast_data_dir'],
                                       date.strftime("%Y%m%d"), digit3_mem)
        if not os.path.exists(remote_data_dir):
            os.makedirs(remote_data_dir)

        print(f'Retrieving hr: {fc}')
        #self.retrieve_fc_data(date, hr, fc, digit2_mem, remote_data_dir, moosedir)
        fct = f'{fc:03d}'  # if fc != 0 else '003'

        # File names changed on moose on 25/09/2018
        filemoose = f'prods_op_mogreps-g_{date.strftime("%Y%m%d")}_{hr}_{digit2_mem}_{fct}.pp'
        outfile = f'englaa_pd{fct}.pp'

        # Generate a unique query file
        local_query_file1 = os.path.join(self.config_values['dummy_queryfiles_dir'],
                                         f'localquery_{uuid.uuid1()}')
        self.create_query_file(local_query_file1, filemoose, fct)

        outfile_path = os.path.join(remote_data_dir, outfile)
        outfile_status = os.path.exists(outfile_path) and os.path.getsize(outfile_path) > 0

        if not outfile_status:
            print('EXECCCC')
            command = f'/opt/moose-client-wrapper/bin/moo select {local_query_file1} {moosedir} {os.path.join(remote_data_dir, outfile)}'
            logger.info('Executing command: %s', command)

            try:
                subprocess.run(command, shell=True, check=True)
                logger.info('Data retrieval successful.')
            except subprocess.CalledProcessError as e:
                logger.error('Error during data retrieval: %s', e)
            except Exception as e:
                logger.error('An unexpected error occurred: %s', e)
        else:
            print(f'{os.path.join(remote_data_dir, outfile)} exists. Skip...')


    def check_if_all_data_exist(self, date, hr, fc, digit2_mem):
        digit3_mem = str('%03d' % int(digit2_mem))
        remote_data_dir = os.path.join(self.config_values['forecast_data_dir'],
                                       date.strftime("%Y%m%d"), digit3_mem)
        fct = f'{fc:03d}'
        outfile = f'englaa_pd{fct}.pp'
        outfile_path = os.path.join(remote_data_dir, outfile)
        outfile_status = os.path.exists(outfile_path) and os.path.getsize(outfile_path) > 0
        return outfile_status

    def create_query_file(self, local_query_file1, filemoose, fct):
        query_file = self.config_values['queryfile']

        replacements = {'fctime': fct, 'filemoose': filemoose}
        with open(query_file) as query_infile, open(local_query_file1, 'w') as query_outfile:
            for line in query_infile:
                for src, target in replacements.items():
                    line = line.replace(src, target)
                query_outfile.write(line)

    def retrieve_mogreps_data(self, date):
        print('Retrieving data for date:', date)

        hr_list = [12, 18]
        fc_times = np.arange(0, 174, 24)
        print(fc_times)

        # Create a list of tuples for all combinations of hr and mem
        tasks = [(date, hr, fc, digit2_mem) for hr in hr_list for fc in fc_times for digit2_mem in
                 self.get_all_members(hr)]

        #for task in tasks:
        #    self.retrieve_fc_data_parallel(*task)

        # Use ThreadPoolExecutor to run tasks in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit tasks to the executor
            futures = [executor.submit(self.retrieve_fc_data_parallel, *task) for task in tasks]

            # Wait for all tasks to complete
            concurrent.futures.wait(futures)

        # Wait for all tasks to complete
        #print(concurrent.futures.as_completed(futures))

        #file_present = all([self.check_if_all_data_exist(*task) for task in tasks ])
        # Check if all tasks are completed
        all_tasks_completed = all(future.done() for future in futures)

        return all_tasks_completed



        # Check if all tasks are completed successfully
        #all_tasks_completed = all(future.done() and not future.cancelled() for future in futures)

        #print("All MOGREPS retrieval tasks completed.")
        #return all_tasks_completed


    def subset_seasia(self, cube):
        return cube.intersection(latitude=(-10, 25), longitude=(85, 145))

    def process_forecast_data(self, date, members):
        fc_times = [str('%03d' % fct) for fct in np.arange(0, 174, 24)]

        for varname in ['precip']:
            concated_dir = os.path.join(
                self.config_values['forecast_out_dir'], varname )

            if not os.path.exists(concated_dir):
                os.makedirs(concated_dir)


            combined_allmember_file = os.path.join(concated_dir,
                                         f'{varname}_Features_24h_allMember_{date.strftime("%Y%m%d")}.nc')

            time_coord = iris.coords.DimCoord(
                points=[int(t) for t in fc_times],  standard_name='time',
                units=f'days since {date.strftime("%Y-%m-%d")}')

            if not os.path.exists(combined_allmember_file):
                cubes = []
                for mem in members:
                    # progress bar
                    self.print_progress_bar(int(mem), len(members))

                    mog_files = [os.path.join(self.config_values['forecast_data_dir'],
                                              date.strftime("%Y%m%d"), mem, f'englaa_pd{fct}.pp')
                                 for fct in fc_times]
                    mog_files.sort()
                    realiz_coord = iris.coords.DimCoord([int(mem)], standard_name='realization',
                                                        var_name='realization')



                    if varname == 'precip':
                        cube = iris.load_cube(mog_files, 'precipitation_amount')
                        cube = self.subset_seasia(cube)
                        cube.data[1:] -= cube.data[:-1]

                    # Massaging the data for merging
                    for coord in ['forecast_reference_time', 'realization', 'time']:
                        cube.remove_coord(coord) if cube.coords(coord) else None
                    cube.add_aux_coord(realiz_coord)
                    cube.coord('forecast_period').points = cube.coord('forecast_period').bounds[:, 1]
                    cubes.append(cube)


                cube = iris.cube.CubeList(cubes).merge_cube()
                cube.add_dim_coord(time_coord, 1)
                print(cube)
                iris.save(cube, combined_allmember_file, netcdf_format='NETCDF4_CLASSIC')
                print(f'Written {combined_allmember_file}')
            else:
                print(f'{combined_allmember_file} exits. Skip.')

    def grid_features(self, cube, thresholds=None, time_index=0, threshold_method='geq'):
        '''
        2D cube tracking for thresholds
        :param cube: Lat-lon cube
        :type cube:
        :param thresholds:
        :type thresholds:
        :param time_index:
        :type time_index:
        :param threshold_method:
        :type threshold_method:
        :return: DataFrame of identified objects and their properties
        :rtype: Pandas DataFrame
        '''
        assert thresholds is not None, "Threshold values not found."

        # indices = []
        time_indices = []
        cube_dates = []
        object_coords = []
        object_labels = []
        threshold_values = []
        areas = []
        perimeters = []
        eccs = []
        orients = []
        centroids = []
        mean_values = []
        std_values = []
        max_values = []
        min_values = []
        ngrid_points = []
        forecast_period = []
        forecast_reference_time = []
        data_values = []
        surface_type = []
        index = time_index
        if cube.ndim == 2:
            ny, nx = cube.shape
            lons, lats = cube.coord('longitude').points, cube.coord('latitude').points

            # Cube date
            if cube.coords('time'):
                c_date = cube.coord('time').units.num2date(cube.coord('time').points)[0]
                cube_date = datetime.datetime(c_date.year, c_date.month, c_date.day)

            if cube.coords('forecast_reference_time'):
                frt = cube.coord('forecast_reference_time').units.num2date(
                    cube.coord('forecast_reference_time').points)[0]
                forecast_rt = datetime.datetime(frt.year, frt.month, frt.day)
            else:
                forecast_rt = np.nan

            if cube.coords('forecast_period'):
                forecast_p = cube.coord('forecast_period').points[0]
            else:
                forecast_p = np.nan

            for threshold in thresholds:
                # print('Thresholding %s' %threshold)
                cube_data = cube.data.copy()
                mask = generate_mask(cube_data, threshold, threshold_method)

                # Label each feature in the mask
                labeled_array, num_features = ndimage.measurements.label(mask)
                # print('%s features labelled.' % num_features)
                # labelled_array is a mask hence != operator below
                for feature_num in range(1, num_features):
                    print_progress_bar(feature_num + 1, num_features)

                    # threshold
                    threshold_values.append(threshold)
                    object_labels.append('%s_%s_%s' % (index, threshold, feature_num))
                    loc = labeled_array != feature_num
                    data_object = np.ma.masked_array(cube_data, loc)

                    ###### Skimage needs the mask reversed
                    lab_image = measure.label(labeled_array == feature_num)
                    region = measure.regionprops(lab_image, np.ma.masked_array(cube_data, ~loc))

                    # perimeter, eccentricity, orientation
                    areas.append([p.area for p in region][0])
                    perimeters.append([p.perimeter for p in region][0])
                    eccs.append([p.eccentricity for p in region][0])
                    orients.append([p.orientation for p in region][0])
                    # print(eccs)
                    ###############

                    data_values.append(data_object.compressed())
                    mean_values.append(np.ma.mean(data_object))
                    std_values.append(np.ma.std(data_object))
                    max_values.append(np.ma.max(data_object))
                    min_values.append(np.ma.min(data_object))

                    try:
                        y, x = ndimage.measurements.center_of_mass(data_object)
                        centroids.append((lons[round(x)], lats[round(y)]))
                    except:
                        centroids.append((np.nan, np.nan))

                    object_inds = np.where(loc == False)
                    object_lats = [lats[i] for i in object_inds[0]]
                    object_lons = [lons[i] for i in object_inds[1]]

                    object_coords.append([(x, y) for x, y in zip(object_lons, object_lats)])

                    # surface type
                    # This slows the computation down significantly
                    # surface_type.append(check_land_or_ocean(object_lons, object_lats))

                    ngrid_points.append(len(object_lats))

                    cube_dates.append(cube_date)
                    forecast_period.append(forecast_p)
                    forecast_reference_time.append(forecast_rt)
                    # indices.append(index)
                    time_indices.append(index)

            index += 1
        features = {'TimeInds': time_indices, 'Date': cube_dates,
                    'Forecast_period': forecast_period, 'Forecast_reference_time': forecast_reference_time,
                    'Threshold': threshold_values, 'ObjectLabel': object_labels, 'Area': areas,
                    'GridPoints': ngrid_points,
                    'Mean': mean_values, 'Std': std_values,
                    'Max': max_values, 'Min': min_values,
                    'Centroid': centroids, 'Polygon': object_coords, 'Data_values': data_values,
                    'Perimeter': perimeters, 'Eccentricity': eccs, 'Orientation': orients}

        features = pd.DataFrame(features, columns=['TimeInds', 'Date', 'Forecast_period',
                                                   'Forecast_reference_time', 'Threshold', 'ObjectLabel', 'Area',
                                                   'Perimeter',
                                                   'GridPoints', 'Eccentricity', 'Orientation',
                                                   'Mean', 'Std', 'Max', 'Min', 'Centroid', 'Polygon', 'Data_values'])
        return features

    def grid_features_3d(self, date, members, thresholds=None, threshold_method='geq', varname='precip'):
        '''
        Returns a DataFrame of detected object properties for various thresholds
        :param cubes:
        :type cubes:
        :param thresholds:
        :type thresholds:
        :param threshold_method:
        :type threshold_method:
        :return:
        :rtype:
        '''

        concated_dir = os.path.join(self.config_values['forecast_out_dir'], varname)

        combined_allmember_file = os.path.join(concated_dir,
                                         f'{varname}_Features_24h_allMember_{date.strftime("%Y%m%d")}.nc')

        cubes = iris.load_cube(combined_allmember_file)
        nmembers, ntime, _, _ = cubes.shape
        print(nmembers, ntime)
        sys.exit()
        frames = []
        if len(cubes.shape) == 3:
            ntime, _, _ = cubes.shape
            for i in range(ntime):
                # print('%s/%s' %(i, ntime))
                frames.append(grid_features(cubes[i], thresholds=thresholds, time_index=i,
                                            threshold_method=threshold_method))
        else:
            frames.append(grid_features(cubes, thresholds=thresholds, time_index=0,
                                        threshold_method=threshold_method))
        return pd.concat(frames, ignore_index=True)