#!/usr/bin/env /net/project/ukmo/scitools/opt_scitools/conda/deployments/default-2023_10_10/bin/python
import datetime
import sys
sys.path.append('/home/h03/hadpx/MJO/Monitoring_new/MJO')
import time
from analysis import analysis_process
from mogreps import mogreps_process
from glosea import glosea_process
from lib import mjo_utils
from display import bokeh_display
def do_analysis(date):
    #
    # Usage:
    reader = analysis_process.AnalysisProcess('analysis')
    status = reader.check_retrieve_201_prev_days(date, parallel=True)
    #print(status)
    #if status == 0:
    status = reader.combine_201_days_analysis_data(date)
    print(status)
    #else:
    #    print(f'Error: Not all jobs in AnalysisProcess().check_retrieve_201_prev_days completed.')
    #    #sys.exit()

def do_mogreps(date):
    reader = mogreps_process.MOGProcess('mogreps')
    print(reader.config_values)
    # This retrieves 35 members
    status1 = reader.retrieve_mogreps_data(date)
    print(status1)

    # All ensemble members
    members = [str('%03d' % mem) for mem in range(36)]
    print(members)

    #if status1:
    #    # Combine and prepare the data
    status2 = reader.combine_201_days_analysis_and_forecast_data(date, members)
    print(f'combine_201_days_analysis_and_forecast_data: {status2}')
    #else:
    #    print(f'Error: Not all jobs in retrieve_mogreps_data() completed.')
    #    #sys.exit()
    #time.sleep(60)  # Wait for 60 seconds

    # MJO calculations
    #if status2:
    mjo_proc = mjo_utils.MJOUtils('mogreps')
    status3 = mjo_proc.run_parallel_mjo_process(date, members)
    print(f'run_parallel_mjo_process: {status3}')
    #else:
    #    print('Task Error in : reader.combine_201_days_analysis_and_forecast_data(date, members)')
    #    #sys.exit()

    #time.sleep(60)  # Wait for 60 seconds
    #if status3:
    rmm_display = bokeh_display.MJODisplay('mogreps')
    rmm_display.bokeh_rmm_plot(date, members, title_prefix='MOGREPS')
    #else:
    #    print(f'Error: Not all jobs in mjo_utils.run_parallel_mjo_process() completed.')


def do_glosea(date):
    reader = glosea_process.GLOProcess('glosea')
    reader.retrieve_glosea_data(date)

    # All ensemble members
    members = [str('%03d' % mem) for mem in range(4)]
    print(members)

    mjo_proc = mjo_utils.MJOUtils('glosea')
    status3 = mjo_proc.run_parallel_mjo_process(date, members, parallel=False)
    print(f'run_parallel_mjo_process: {status3}')

    time.sleep(60)  # Wait for 60 seconds

    rmm_display = bokeh_display.MJODisplay('glosea')
    rmm_display.bokeh_rmm_plot(date, members, title_prefix='GLOSEA')

if __name__ == '__main__':
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    #yesterday = datetime.datetime(2024, 1, 17)

    # MOGREPS
    do_analysis(yesterday)
    time.sleep(60)  # Wait for 60 seconds
    do_analysis(yesterday)
    time.sleep(60)  # Wait for 60 seconds


    # a second run to make sure all parallel jobs are completed
    do_mogreps(yesterday)
    time.sleep(60)  # Wait for 60 seconds
    do_mogreps(yesterday)

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


