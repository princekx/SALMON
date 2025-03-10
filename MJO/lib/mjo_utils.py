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

class MJOUtils:
    def __init__(self, model, config_values):
        self.config_values = config_values
        self.num_prev_days = 201
        # 40 days of anlysis to be written out with the forecasts
        self.nanalysis2write = 40
        if model == 'glosea':
            self.nforecasts = 30
        else:
            self.nforecasts = 7

        # Navigate to the parent directory
        #parent_dir = os.getcwd()
        self.parent_dir = '/home/users/prince.xavier/MJO/SALMON/MJO'

    def region(self, coords):
        if len(coords) == 4:
            loni, lati, lonf, latf = coords
            region_subset = iris.Constraint(longitude=lambda cell: loni <= cell <= lonf,
                                            latitude=lambda cell: lati <= cell <= latf)
        else:
            print('Wrong number of elements in the coordinate array.')
        return region_subset

    def prepare_calendar(self, cube, time_coord='time'):
        # Setting up the dates on data
        for coord_name, coord_func in [('year', iris.coord_categorisation.add_year),
                                       ('month_number', iris.coord_categorisation.add_month_number),
                                       ('day_of_month', iris.coord_categorisation.add_day_of_month),
                                       ('day_of_year', iris.coord_categorisation.add_day_of_year),
                                       ('hour', iris.coord_categorisation.add_hour)]:
            if not cube.coords(coord_name):
                coord_func(cube, time_coord, name=coord_name)
        return cube
    def remRunMean(self, cube, NN=120):
        '''
        # 6. remove 120-days running mean
        #  Removes the NN-day mean of the PREVIOUS NN days from a dataset.
        #  Up until the NN-th day, the value removed is the sum of all the
        #  previous values divided by NN.
        #  If there is missing data, the above procedure starts over again.
        '''
        ntime, nlat, nlon = cube.shape

        runmean = cube.copy()
        for n in range(1, ntime):
            if n < NN:
                runmean.data[n] = np.mean(cube.data[:n + 1], axis=0)
            else:
                runmean.data[n] = np.mean(cube.data[n - NN:n + 1], axis=0)
        return cube - runmean

    def read_harmonics(self, harfile):
        # read harmonic coefficients from netcdf file
        mm = iris.load_cube(harfile, 'mm')
        aa = iris.load_cube(harfile, 'aa')
        bb = iris.load_cube(harfile, 'bb')
        return mm, aa, bb

    def remove3har(self, cube, harfile):
        # Uses the mean and 3 harmonics of the seasonal cycle as calculated
        # by the routine calc3har.f to create anomalies for any desired time
        # period. That is, the routine just removes the 3 harmonics, but does
        # not calculate them.
        # read harmonic coefficients from file
        mm, aa, bb = self.read_harmonics(harfile)

        # Add a julian day axis
        if 'julian_day' not in [coord.name() for coord in cube.coords()]:
            iris.coord_categorisation.add_day_of_year(cube, 'time', name='julian_day')

        anom = cube.copy()

        for i, t in enumerate(cube.coord('julian_day').points):
            anom.data[i] = cube.data[i] \
                           - mm.data \
                           - aa.data[0] * np.cos(2 * np.pi * (t - 1.) * 1. / 365.) \
                           - bb.data[0] * np.sin(2. * np.pi * (t - 1.) * 1. / 365.) \
                           - aa.data[1] * np.cos(2 * np.pi * (t - 1.) * 2. / 365.) \
                           - bb.data[1] * np.sin(2. * np.pi * (t - 1.) * 2. / 365.) \
                           - aa.data[2] * np.cos(2 * np.pi * (t - 1.) * 3. / 365.) \
                           - bb.data[2] * np.sin(2. * np.pi * (t - 1.) * 3. / 365.)
        return anom
    def compute_rmms(self, anom_120_filenames, rmm_file_name):
        #parent_dir = os.getcwd()
        eigenfile = os.path.join(self.parent_dir, 'data', 'olr+u850+u200.anom-sst1-120dm.79-.15snAv.ASCII')

        # read from the newly created ascii file of the eigenvalues
        f = open(eigenfile, 'r')
        lines = f.readlines()
        NX, NY, NT, nspace, num, fstyr, nsp1, nsp2, nsp3 = list(map(int, lines[1].split()))
        #print(NX, NY, NT, nspace, num, fstyr, nsp1, nsp2, nsp3)

        # Eigen values
        ll = 13
        eigval = np.array([float(x.strip()) for x in lines[ll:ll + nspace]])

        # Eigen vectors
        ll = 446
        eigvec = np.array([float(x.strip()) for x in lines[ll:ll + nspace * num]])
        eigvec = np.transpose(eigvec.reshape(num, nspace), axes=(1, 0))

        # normalization factor (432)This text was
        ll = 9087
        norm = np.array([float(x.strip()) for x in lines[ll:ll + nspace]])

        # time-average of space-time matrix (432)
        ll = 9520
        databar = np.array([float(x.strip()) for x in lines[ll:ll + nspace]])

        # Reading a sample data to create the array
        cube = iris.load_cube(anom_120_filenames['olr'])

        # 15S-15N lat average
        # here we only need 144 lon values
        cube = cube.extract(self.region([0, -15, 357.5, 15]))
        cube = cube.collapsed(['latitude'], iris.analysis.MEAN)
        ntime, mlon = cube.shape

        # Large array to hold all the variables
        cdata = np.zeros((ntime, 3 * mlon))
        for n, varname in enumerate(['olr', 'u850', 'u200']):  # 0:2 are OLR, u850, u200
            cube = iris.load_cube(anom_120_filenames[varname])

            # lat average
            # here we only need 144 lon values
            cube = cube.extract(self.region([0, -15, 357.5, 15]))
            cube = cube.collapsed(['latitude'], iris.analysis.MEAN)

            # Combine the data into one variable
            cdata[:, n * mlon: (n + 1) * mlon] = cube.data

        # Number of different phases
        print('Computing RMMs')
        nphases = 8
        # Angles to composite for (this is the centre of the +- range)
        phi = np.array([202.5, 247.5, 292.5, 337.5, 22.5, 67.5, 112.5, 157.5])

        rmm1s = []
        rmm2s = []
        phases = []
        amps = []
        # Now work on one time at a time as in the createRMM1RMM2.f
        for t in range(ntime):
            # normalise datmat for each time
            datmat = (cdata[t, :] - databar) / norm

            #  Compute RMM1 and RMM2  (the first two normalized PCs)
            # Do the computation in 3 parts, one for each variable, so
            # that we can compute the contribution from each variable

            pcolr = np.dot(np.transpose(eigvec[0:nsp1, 0:2]), datmat[0:nsp1])
            pcu850 = np.dot(np.transpose(eigvec[nsp1:nsp2, 0:2]), datmat[nsp1:nsp2])
            pcu200 = np.dot(np.transpose(eigvec[nsp2:nsp3, 0:2]), datmat[nsp2:nsp3])
            pc = pcolr + pcu850 + pcu200

            # Now normalize (by EOF-calcualted s.d.) the newly calculated PCs
            pc = pc / np.sqrt(eigval[0:2])
            pcolr = pcolr / np.sqrt(eigval[0:2])
            pcu850 = pcu850 / np.sqrt(eigval[0:2])
            pcu200 = pcu200 / np.sqrt(eigval[0:2])

            # Calculate PHASE and AMPLITUDE described by the 2 PCs.
            ag = (360. / (2. * np.pi)) * np.arctan2(pc[1], pc[0])
            if ag < 0:
                ag = ag + 360.
            if ag >= 360.:
                ag = ag - 360.

            for ipa in np.arange(nphases):
                phiminus = phi[ipa] - 180. / float(nphases)
                phiplus = phi[ipa] + 180. / float(nphases)
                if phiminus < 0.:
                    phiminus = phiminus + 360.
                if phiplus >= 360.:
                    phiplus = phiplus - 360.
                if (phiminus < phiplus):
                    if (ag >= phiminus) and (ag < phiplus):
                        pa = ipa + 1
                else:
                    if (ag >= phiminus) or (ag < phiplus):
                        pa = ipa + 1

            rmm1s.append(pc[0])
            rmm2s.append(pc[1])
            phases.append(pa)
            amp = np.sqrt(pc[0] ** 2. + pc[1] ** 2.)
            amps.append(amp)

            #   WRITE OUT THE FRACTIONAL CONTRIBUTION OF EACH VARIABLE TO RMM AMP**2
            fpcolr = (pcolr[0] * pc[0] + pcolr[1] * pc[1]) / amp ** 2
            fpcu850 = (pcu850[0] * pc[0] + pcu850[1] * pc[1]) / amp ** 2
            fpcu200 = (pcu200[0] * pc[0] + pcu200[1] * pc[1]) / amp ** 2
        print(fpcolr, fpcu850, fpcu200)

        cube = self.prepare_calendar(cube, time_coord='forecast_time')
        # Create an empty DataFrame
        df = pd.DataFrame(columns=['year', 'month', 'day', 'rmm1', 'rmm2', 'phase', 'amp', 'label'])
        df['year'] = cube.coord('year').points
        df['month'] = cube.coord('month_number').points
        df['day'] = cube.coord('day_of_month').points
        df['rmm1'] = rmm1s
        df['rmm2'] = rmm2s
        df['phase'] = phases
        df['amp'] = amps
        df['label'] = ['analysis' for i in range(ntime-self.nforecasts)] + \
                      ['forecast' for i in range(self.nforecasts)]
        # Write the DataFrame to a CSV file
        df.to_csv(rmm_file_name, index=False)
        print(f'DataFrame has been successfully written to {rmm_file_name}')

    def mjo_process_member(self, date, mem):
        #parent_dir = os.getcwd()
        rmms_archive_dir = os.path.join(self.config_values['mogreps_mjo_archive_dir'],
                                        f'{date.strftime("%Y%m%d")}')
        if not os.path.exists(rmms_archive_dir):
            os.makedirs(rmms_archive_dir)

        rmm_file_name = os.path.join(rmms_archive_dir, f'createdPCs.15sn.{date.strftime("%Y%m%d")}.fcast.{mem}.txt')
        if not os.path.exists(rmm_file_name):

            anom_120_filenames = {}
            for varname in ['olr', 'u850', 'u200']:
                forecast_out_dir = os.path.join(
                    self.config_values['forecast_out_dir'], varname)
                sm120d_outfile = os.path.join(forecast_out_dir,
                                              f'{varname}_120dm_40sn_nrt_{date.strftime("%Y%m%d")}_{mem}.nc')

                # save the filenames for the next step
                anom_120_filenames[varname] = sm120d_outfile

                if not os.path.exists(sm120d_outfile):
                    # Harmonic file
                    harfile = os.path.join(self.parent_dir, 'data', f'{varname}.nr.79to01.m+3har.nc')

                    # read the combined data file smoothed anomalies
                    concated_file = os.path.join(forecast_out_dir,
                                                 f'{varname}_concat_nrt_{date.strftime("%Y%m%d")}_{mem}.nc')
                    # Read file
                    print(f'Reading {concated_file}')
                    cube = iris.load_cube(concated_file)

                    ntime, nlat, nlon = cube.shape

                    #assert ntime == self.num_prev_days+self.nforecasts, \
                    #    f'Assert Error: Number of timesteps {ntime}, expecting {(self.num_prev_days+self.nforecasts)}.'

                    # Step 1
                    # remove 3 harmonics
                    cube = self.remove3har(cube, harfile)

                    # Step 2
                    # subset region
                    cube = cube.extract(self.region([0, -40, 360, 40]))

                    # Step 3
                    # 120 days running mean
                    cube = self.remRunMean(cube)
                    # only output 40 days of analysis + nforecasts (7)
                    cube = cube[-(self.nanalysis2write + self.nforecasts):]

                    iris.save(cube, sm120d_outfile, netcdf_format="NETCDF3_CLASSIC")
                    print(f'Forecast: 120 day smoothed data written to {sm120d_outfile}')
                else:
                    print(f'{sm120d_outfile} exists. Skipping computation.')

            # Step 4

            # Check all 3 files exist
            all_files_exist = all(os.path.exists(file_path) for file_path in anom_120_filenames.values())
            assert all_files_exist, 'Some files do not exist.'
            # Compute RMMs
            self.compute_rmms(anom_120_filenames, rmm_file_name)

        else:
            print(f'{rmm_file_name} exists. Skip RMM calculation.')

    def run_parallel_mjo_process(self, date, members, parallel=True):

        if parallel:
            with concurrent.futures.ProcessPoolExecutor() as executor:
                futures = {executor.submit(self.mjo_process_member, date, mem): mem for mem in members}

                concurrent.futures.wait(futures)

            # Check if all tasks are completed successfully
            all_tasks_completed = all(future.done() and not future.cancelled() for future in futures)


            if all_tasks_completed:
                print("All tasks in run_parallel_mjo_process completed successfully.")
            else:
                print("Some tasks failed.")

            return all_tasks_completed
        else:
            # Running in serial mode
            tasks = [(date, mem) for mem in members]
            for task in tasks:
                print(task)
                self.mjo_process_member(*task)

