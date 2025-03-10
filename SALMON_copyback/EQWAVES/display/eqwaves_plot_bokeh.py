import os, sys
import glob
import iris
import datetime
import numpy as np
import configparser
import json
import iris.coord_categorisation
import pandas as pd
from bokeh.plotting import figure, show, save, output_file
from bokeh.models import ColumnDataSource, Patches, Plot, Title
from bokeh.models import HoverTool
from bokeh.models import Range1d, LinearColorMapper, ColorBar
from bokeh.models import GeoJSONDataSource
from bokeh.palettes import GnBu9, Magma6, Greys256, Greys9, GnBu9, RdPu9, TolRainbow12
from bokeh.palettes import Iridescent23, TolYlOrBr9, Bokeh8, Greys9, Blues9


class EqWavesDisplay:
    def __init__(self, model):
        """
        Initializes the EqWavesDisplay class with configuration values.

        Args:
            model (str): The model section in the configuration file.
        """
        self.model = model
        self.parent_dir = '/home/h03/hadpx/MJO/Monitoring_new/EQWAVES'
        self.config_values = {}
        self.config_values_analysis = {}
        self.load_config_values(model)
        self.ntimes_total = 360
        self.ntimes_analysis = 332
        self.ntimes_forecast = 28
        self.wave_names = np.array(['Kelvin', 'WMRG', 'R1', 'R2'])  # List of wave types to output

        self.pressures = ['850']
        # Plot thresholds for probabilities
        self.thresholds = {'precip': 5,
                           'Kelvin_850': -1 * 1e-6, 'Kelvin_200': -2 * 1e-6,
                           'WMRG_850': -1 * 1e-6, 'WMRG_200': -2 * 1e-6,
                           'R1_850': 5 * 1e-6, 'R1_200': 2 * 1e-6,
                           'R2_850': 2.5 * 1e-6, 'R2_200': 2 * 1e-6}
        self.times2plot = [t for t in range(-96, 174, 6)]
        # Map outline
        self.map_outline_json_file = os.path.join(self.parent_dir,
                                                  'display', 'custom.geo.json')
        self.plot_width = 1100

    def load_config_values(self, model):
        """
        Loads configuration values from the config.ini file.

        Args:
            model (str): The model section in the configuration file.
        """
        config_path = os.path.join(self.parent_dir, 'config.ini')
        config = configparser.ConfigParser()
        config.read(config_path)

        self.config_values = dict(config.items(model))
        self.config_values_analysis = dict(config.items('analysis'))

    def prepare_calendar(self, cube):
        # Setting up the dates on data
        for coord_name, coord_func in [('year', iris.coord_categorisation.add_year),
                                       ('month_number', iris.coord_categorisation.add_month_number),
                                       ('day_of_month', iris.coord_categorisation.add_day_of_month),
                                       ('hour', iris.coord_categorisation.add_hour)]:
            if not cube.coords(coord_name):
                coord_func(cube, 'time', name=coord_name)
        return cube

    def create_dates_dt(self, cube):
        cube = self.prepare_calendar(cube)
        cube_dates_dt = [datetime.datetime(y, m, d, h) for y, m, d, h in zip(cube.coord('year').points,
                                                                             cube.coord('month_number').points,
                                                                             cube.coord('day_of_month').points,
                                                                             cube.coord('hour').points)]
        return cube_dates_dt

    def write_dates_json(self, date, json_file):

        # Add a new date to the list
        new_date = date.strftime('%Y%m%d_%H')

        if not os.path.exists(json_file):
            with open(json_file, 'w') as jfile:
                json.dump([new_date], jfile)

        # Load existing dates from dates.json
        with open(json_file, 'r') as file:
            existing_dates = json.load(file)


        # Check if the value exists in the list
        if new_date not in existing_dates:
            # Append the value if it doesn't exist
            existing_dates.append(new_date)

        existing_dates.sort()

        # Save the updated list back to dates.json
        with open(json_file, 'w') as file:
            json.dump(existing_dates, file, indent=2)

        print(f"The {json_file} file has been updated. New date added: {new_date}")

    def bokeh_plot2html(self, shade_var=None, contour_var=None, figure_tite=None,
                        shade_cbar_title=None, contour_cbar_title=None, html_file='test.html'):

        x_range = (0, 180)  # could be anything - e.g.(0,1)
        y_range = (-24, 24)


        width = self.plot_width
        aspect = (max(x_range) - min(x_range)) / (max(y_range) - min(y_range))
        height = int(width / (0.6 * aspect))

        plot = figure(height=height, width=width, x_range=x_range, y_range=y_range,
                      tools=["pan, reset, save, wheel_zoom, hover"],
                      x_axis_label='Longitude', y_axis_label='Latitude', aspect_scale=4,
                      title=figure_tite, tooltips=[("Lat", "$y"), ("Lon", "$x"), ("Value", "@image")])

        plot.title.text_font_size = "14pt"

        shade_levels = np.arange(0.1, 1.1, 0.1)

        color_mapper_z = LinearColorMapper(palette='Iridescent23', low=shade_levels.min(), high=shade_levels.max())
        color_bar = ColorBar(color_mapper=color_mapper_z, major_label_text_font_size="12pt",
                             label_standoff=6, border_line_color=None, orientation="horizontal",
                             location=(0, 0), width=400, title=shade_cbar_title, title_text_font_size="12pt")

        plot.image(image=[shade_var.data], x=0, y=-24,
                   dw=360, dh=48, alpha=0.8,
                   color_mapper=color_mapper_z)
        plot.add_layout(color_bar, 'below')

        if contour_var is not None:
            lons, lats = np.meshgrid(contour_var.coord('longitude').points, contour_var.coord('latitude').points)
            contour_levels = np.arange(0.4, 1.2, 0.2)
            contour_renderer = plot.contour(lons, lats, contour_var.data, contour_levels, fill_color=None,
                                            fill_alpha=0.3,
                                            line_color=Bokeh8, line_alpha=0.5, line_width=5)
            colorbar = contour_renderer.construct_color_bar(major_label_text_font_size="12pt",
                                                            orientation="horizontal", location=(-500, -135), width=400,
                                                            title=contour_cbar_title, title_text_font_size="12pt")
            plot.add_layout(colorbar, "right")

        with open(self.map_outline_json_file, "r") as f:
            countries = GeoJSONDataSource(geojson=f.read())

        plot.patches("xs", "ys", color=None, line_color="grey", source=countries, alpha=0.75)

        output_file(html_file)
        save(plot)
        print('Plotted %s' % html_file)

    def bokeh_plot_forecast_ensemble_probability(self, date):
        mem_labels = [f'{fc:03}' for fc in range(0, 17)]

        str_hr = date.strftime('%H')
        date_label = date.strftime('%Y%m%d_%H')
        outfile_dir = os.path.join(self.config_values['mog_forecast_processed_dir'], date_label)

        html_file_dir = os.path.join(self.config_values['mog_plot_ens'], date_label)
        if not os.path.exists(html_file_dir):
            os.makedirs(html_file_dir)

        # Realistically you will probably only want to write out say (T-4:T+7) so that
        # you can plot an animation of the last few days and the forecast
        # total of 45 time points
        # write_out_times = 45
        # This has been moved to the plotting step.

        precip_files = [os.path.join(outfile_dir, f'precipitation_flux_combined_{date_label}Z_{mem}.nc') for mem in
                        mem_labels]
        print(precip_files)
        precip_files = [file for file in precip_files if os.path.exists(file)]

        # Precip cubes
        pr_cube = iris.load_cube(precip_files)

        print(pr_cube)

        ntimes = len(self.times2plot)

        pr_cube = pr_cube[:, -ntimes:]
        # Assuming `times2plot` and `create_dates_dt(pr_cube)` are lists
        data = [(i, l, d) for i, l, d in zip(range(ntimes), self.times2plot, self.create_dates_dt(pr_cube))]

        # Creating DataFrame
        df = pd.DataFrame(data, columns=['Index', 'Lead', 'Date'])

        shade_var = pr_cube.collapsed('realization', iris.analysis.PROPORTION,
                                      function=lambda values: values > self.thresholds['precip'])
        shade_cbar_title = f"Probability of precipitation >= {self.thresholds['precip']} mm day-1"

        for wname in self.wave_names:
            print(f'PLOTTING WAVE {wname}!!!!!!!!!!!!!!!!!!!!!!!!!')
            for pressure_level in self.pressures:
                if wname in ['Kelvin', 'WMRG']:
                    wave_files = [os.path.join(outfile_dir, f'div_wave_{wname}_{date_label}Z_{mem}.nc') for mem in
                                  mem_labels]
                    wave_files = [file for file in wave_files if os.path.exists(file)]
                    print(wave_files)
                    wave_variable = iris.load_cube(wave_files)
                    wave_variable = wave_variable.extract(iris.Constraint(pressure=float(pressure_level)))
                    wave_variable = wave_variable[:, -ntimes:]
                    contour_var = wave_variable.collapsed('realization', iris.analysis.PROPORTION,
                                                          function=lambda values: values <= self.thresholds[
                                                              f'{wname}_{pressure_level}'])
                    contour_cbar_title = f"Probability of {wname} divergence <= {self.thresholds[f'{wname}_{pressure_level}']:0.1e} s-1"
                elif wname in ['R1', 'R2']:
                    wave_files = [os.path.join(outfile_dir, f'vort_wave_{wname}_{date_label}Z_{mem}.nc') for mem in
                                  mem_labels]
                    wave_files = [file for file in wave_files if os.path.exists(file)]
                    print(wave_files)

                    wave_variable = iris.load_cube(wave_files)
                    wave_variable = wave_variable.extract(iris.Constraint(pressure=float(pressure_level)))
                    wave_variable = wave_variable[:, -ntimes:]
                    contour_var = wave_variable.collapsed('realization', iris.analysis.PROPORTION,
                                                          function=lambda values: values >= self.thresholds[
                                                              f'{wname}_{pressure_level}'])
                    contour_cbar_title = f"Probability of {wname} vorticity >= {self.thresholds[f'{wname}_{pressure_level}']:0.1e} s-1"

                for lead in self.times2plot:
                    t = df.loc[df['Lead'] == lead].Index.values[0]
                    datetime_string = df['Date'].loc[df['Lead'] == lead].astype('O').tolist()[0].strftime(
                        '%Y/%m/%d %HZ')
                    if int(lead) < 0:
                        figure_tite = f"{shade_cbar_title};  {contour_cbar_title} \nValid on {datetime_string} at T{lead}"
                    else:
                        figure_tite = f"{shade_cbar_title};  {contour_cbar_title} \nValid on {datetime_string} at T+{lead}"

                    html_file = os.path.join(html_file_dir,
                                             f'{wname}_{pressure_level}_EnsProb_{date_label}Z_T{(lead)}h.html')

                    self.bokeh_plot2html(shade_var=shade_var[t], contour_var=contour_var[t],
                                         figure_tite=figure_tite,
                                         shade_cbar_title=shade_cbar_title, contour_cbar_title=contour_cbar_title,
                                         html_file=html_file)

        json_file = os.path.join(self.config_values['mog_plot_ens'], f'{self.model}_eqw_ens_plot_dates.json')
        self.write_dates_json(date, json_file)

        '''
        for wname, index in self.wave_names.items():
            print(wname, index)
            var_file_out = os.path.join(outfile_dir, f'{var_name}_{wname}_{date_label}Z_{mem_label}.nc')
            iris.save(wave_cube[index], var_file_out)
            print(var_file_out)
        '''
