#!/usr/bin/env /net/project/ukmo/scitools/opt_scitools/conda/deployments/default-2023_10_10/bin/python
import datetime
import sys
sys.path.append('/net/home/h03/hadpx/MJO/Monitoring_new/COLDSURGE')
from mogreps import mogreps_process
from display import coldsurge_plot_bokeh
from multiprocessing import Pool
#from display import bokeh_display

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
    status2 = reader.process_forecast_data(date, members)

    reader = coldsurge_plot_bokeh.ColdSurgeDisplay('mogreps')
    reader.bokeh_plot_forecast_ensemble_mean(date)
    reader.bokeh_plot_forecast_probability_precip(date)


if __name__ == '__main__':
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    #yesterday = datetime.datetime(2024, 2, 7)

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

    start_date = datetime.date(2024, 2, 18)
    end_date = datetime.date(2024, 2, 24)

    # Generate list of all dates
    all_dates = [start_date + datetime.timedelta(days=i)
                 for i in range((end_date - start_date).days + 1)]

    # Number of processes to run in parallel
    num_processes = 4

    # Create a Pool of worker processes
    with Pool(num_processes) as pool:
        # Map the process_date function to all dates and execute in parallel
        results = pool.map(do_mogreps, all_dates)

    print("All dates processed successfully.")

    '''


