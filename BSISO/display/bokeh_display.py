import glob, os, sys
import pandas as pd
import datetime
from bokeh.plotting import figure, show, save, output_file, gridplot
from bokeh.layouts import column, row
from bokeh.models import Range1d, LinearColorMapper, ColorBar
from bokeh.palettes import GnBu9, Magma6, Greys256, Greys9, GnBu9, RdPu9, TolRainbow12, Sunset8
from bokeh.models import GeoJSONDataSource
from bokeh.models import ColumnDataSource, HoverTool, Select, Div
from bokeh.models import DatetimeTickFormatter
from bokeh.models import Label
from bokeh.transform import linear_cmap
import iris
import numpy as np
import configparser
import json
from PIL import Image
import warnings

# Set the global warning filter to ignore all warnings
warnings.simplefilter("ignore")


class BSISODisplay:
    def __init__(self, model, nforecasts=30):
        self.model = model
        self.config_values = {}
        self.num_prev_days = 201
        # 40 days of anlysis to be written out with the forecasts
        self.nanalysis2write = 40
        self.nforecasts = nforecasts

        # Navigate to the parent directory
        self.parent_dir = '/net/home/h03/hadpx/MJO/Monitoring_new/BSISO'

        # Specify the path to the config file in the parent directory
        config_path = os.path.join(self.parent_dir, 'config.ini')
        print(config_path)

        # Read the configuration file
        config = configparser.ConfigParser()
        config.read(config_path)

        # Get options in the 'analysis' section and store in the dictionary
        for option, value in config.items(model):
            self.config_values[option] = value
        # print(self.config_values)

        # countries_source
        with open(os.path.join(self.parent_dir, 'data', 'countries.geo.json'), 'r', encoding="utf-8") as f:
            self.countries = GeoJSONDataSource(geojson=f.read())

    def write_dates_json(self, date):

        json_file = os.path.join(self.config_values['plot_ens'], f'{self.model}_dates.json')
        print(json_file)
        # Add a new date to the list
        new_date = date.strftime('%Y%m%d')

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

    def make_combined_df(self, date, members):
        date_label = date.strftime("%Y%m%d")
        bsiso_archive_dir = os.path.join(self.config_values['fcast_out_archive_dir'],
                                         f'{date_label}')
        dfs = []
        for m, mem in enumerate(members):
            bsiso_index_file_name = os.path.join(bsiso_archive_dir,
                                                 f'BSISO.{date_label}.fcast.{mem}.txt')
            # Concatenate all DataFrames in the list along rows
            pcs = pd.read_csv(bsiso_index_file_name)
            # Append the computed PCs for the current member to the list
            dfs.append(pcs)

        combined_df = pd.concat(dfs, ignore_index=True)
        return combined_df

    def make_ens_mean_df(self, combined_df):
        ens_mean_df = combined_df.groupby('date', as_index=False)[['PC1', '8_phases', 'PC2', 'amp']].mean()
        return ens_mean_df

    def bokeh_bsiso_plot(self, date, members, title_prefix='GLOSEA'):
        date_label = date.strftime("%Y%m%d")

        html_file_dir = os.path.join(self.config_values['plot_ens'], date_label)
        if not os.path.exists(html_file_dir):
            os.makedirs(html_file_dir)
        html_file = os.path.join(html_file_dir,
                                 f'BSISO_Index_{date_label}_EnsMean.html')

        combined_df = self.make_combined_df(date, members)
        ens_mean_df = self.make_ens_mean_df(combined_df)
        one_mem_df = combined_df.loc[combined_df.mem == 0]
        ens_mean_df['label'] = one_mem_df['label']
        ens_mean_df['mem'] = ['ens_mean' for i in range(len(ens_mean_df))]

        # Load background image
        im = Image.open(os.path.join(self.parent_dir, 'data', 'BSISO_Phases_BG.png'))
        imarray = np.array(im.convert("RGBA"))
        imarray = imarray[::-1]

        hover = HoverTool(tooltips=[
            ("Date", "@date"),
            ("PC1", "@PC1"),
            ("PC2", "@PC2"),
            ("Phase", "@8_phases"),
            ("Amp", "@amp"),
            ("Label", "@label"),
            ("Member", "@mem")
        ], mode='mouse')

        title = f'{title_prefix} BSISO Forecasts {date.strftime("%Y-%m-%d")}'

        p = figure(width=500, height=500, x_range=[-4, 4], y_range=[-4, 4],
                   tools=["pan, reset, save, wheel_zoom, box_zoom", hover])

        p.title.text = title

        p.image_rgba(image=[imarray.view("uint32").reshape(imarray.shape[:2])], x=-4.275, y=-4.275, dw=8.525, dh=8.52,
                     alpha=0.8)

        fcast_start_index = min(one_mem_df.loc[one_mem_df['label'] == 'forecast'].index)

        # connect the forecasts to the analysis
        ens_mean_df = ens_mean_df.iloc[fcast_start_index - 1:]

        for mem in members:
            df = combined_df.loc[combined_df.mem == int(mem)][-self.nforecasts:]
            p.line('PC1', 'PC2', alpha=0.3, source=df)

        # Analysis
        p.line('PC1', 'PC2', alpha=0.8, color='grey', line_width=5,
               source=one_mem_df[-(self.nforecasts + 15):-self.nforecasts])
        p.circle('PC1', 'PC2', alpha=0.8, color='grey', radius=0.05,
                 source=one_mem_df[-(self.nforecasts + 15):-self.nforecasts])
        p.line('PC1', 'PC2', alpha=0.8, line_width=5, source=ens_mean_df)
        p.circle('PC1', 'PC2', radius=0.05, alpha=0.8, source=ens_mean_df)

        output_file(html_file)
        save(p)
        print('Plotted %s' % html_file)

        self.write_dates_json(date)
