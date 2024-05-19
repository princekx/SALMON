#!/usr/bin/env /net/project/ukmo/scitools/opt_scitools/conda/deployments/default-2023_10_10/bin/python
import datetime
import sys
sys.path.append('/home/h03/hadpx/MJO/Monitoring_new/BSISO')
import time
from mogreps import mogreps_process
from glosea import glosea_process
from display import bokeh_display

def do_mogreps(date):
    reader = mogreps_process.MOGProcess('mogreps')
    print(reader.config_values)
    # All ensemble members
    members = [str('%03d' % mem) for mem in range(36)]
    status1 = reader.bsiso_index_compute_main(date, members)

    rmm_display = bokeh_display.BSISODisplay('mogreps', nforecasts=7)
    rmm_display.bokeh_bsiso_plot(date, members, title_prefix='MOGREPS')

def do_glosea(date):
    reader = glosea_process.GLOProcess('glosea')
    print(reader.config_values)
    # All ensemble members
    members = [str('%03d' % mem) for mem in range(4)]
    status1 = reader.bsiso_index_compute_main(date, members)

    rmm_display = bokeh_display.BSISODisplay('glosea', nforecasts=30)
    rmm_display.bokeh_bsiso_plot(date, members, title_prefix='GLOSEA')


if __name__ == '__main__':
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    '''
    # Define the start and end dates
    start_date = datetime.date(2024, 5, 8)

    # Iterate over each date in the specified range
    current_date = start_date
    while current_date <= yesterday:
        do_mogreps(current_date)
        do_glosea(current_date)
        current_date += datetime.timedelta(days=1)
    '''

    # Run for the final date to ensure all parallel jobs are completed
    # a second run to make sure all parallel jobs are completed
    do_mogreps(yesterday)
    do_glosea(yesterday)



