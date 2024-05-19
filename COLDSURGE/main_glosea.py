#!/usr/bin/env /net/project/ukmo/scitools/opt_scitools/conda/deployments/default-2023_10_10/bin/python
import datetime
import sys
sys.path.append('/net/home/h03/hadpx/MJO/Monitoring_new/COLDSURGE')
from glosea import glosea_process
from display import coldsurge_plot_bokeh
from multiprocessing import Pool

def do_glosea(date):
    reader = glosea_process.GLOProcess('glosea')
    print(reader.config_values)
    # All ensemble members

    status1 = reader.retrieve_glosea_data(date)
    print(status1)

    # Combine and prepare the data
    # combine all members
    members = [str('%03d' % mem) for mem in range(4)]
    status2 = reader.combine_members(date, members)

    reader = coldsurge_plot_bokeh.ColdSurgeDisplay('glosea')
    reader.bokeh_plot_forecast_ensemble_mean(date)
    reader.bokeh_plot_forecast_probability_precip(date)


if __name__ == '__main__':
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    # a second run to make sure all parallel jobs are completed
    do_glosea(yesterday)

    #
    # #
    # start_date = datetime.date(2024, 2, 11)
    # end_date = datetime.date(2024, 2, 19)
    # #
    # # # Generate list of all dates
    # all_dates = [start_date + datetime.timedelta(days=i)
    #              for i in range((end_date - start_date).days + 1)]
    # #
    # # # Number of processes to run in parallel
    # num_processes = 4
    # #
    # # # Create a Pool of worker processes
    # with Pool(num_processes) as pool:
    #      # Map the process_date function to all dates and execute in parallel
    #     results = pool.map(do_glosea, all_dates)
    #
    # print("All dates processed successfully.")




