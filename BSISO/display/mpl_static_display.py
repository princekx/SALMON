import glob, os, sys
import os
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
import matplotlib.patches as mpatches
import seaborn as sns
import pandas as pd
import iris
import iris.quickplot as qplt
import iris.plot as iplt
import cartopy.crs as ccrs
import datetime
import iris
import numpy as np
import configparser
import json
import warnings
from PIL import Image

# Set the global warning filter to ignore all warnings
warnings.simplefilter("ignore")

class BSISODisplay:
    def __init__(self, model):
        self.model = model
        self.config_values = {}
        self.num_prev_days = 201
        # 40 days of anlysis to be written out with the forecasts
        self.nanalysis2write = 40

        # Navigate to the parent directory
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

    def read_phase_composite_cubes(self):
        phase_cubes = []
        for phase in range(1, 9):
            file_name = os.path.join(self.parent_dir, 'data',
                                     f'pr_data_phase{phase}_anomaly.nc')
            phase_cubes.append(iris.load_cube(file_name))
        return phase_cubes

    def plot_background(self, phase_cubes):
        sns.set_theme()
        fig = plt.figure(figsize=(10, 10))
        x = 4
        y = 0.707107
        linewidth = 0.25

        # Original figure
        ax = fig.add_subplot(111, aspect='equal')
        ax.plot([-x, -y], [-x, -y], 'k', lw=linewidth)
        ax.plot([y, x], [y, x], 'k', lw=linewidth)
        ax.plot([-x, -y], [x, y], 'k', lw=linewidth)
        ax.plot([y, x], [-y, -x], 'k', lw=linewidth)
        ax.plot([-x, -1], [0, 0], 'k', lw=linewidth)
        ax.plot([1, x], [0, 0], 'k', lw=linewidth)
        ax.plot([0, 0], [-x, -1], 'k', lw=linewidth)
        ax.plot([0, 0], [1, x], 'k', lw=linewidth)
        ax.set_ylim(-x, x)
        ax.set_xlim(-x, x)
        circle = mpatches.Circle((0, 0), 1, fc="white", ec="k", lw=linewidth)
        ax.add_patch(circle)

        # Enable grid
        ax.grid(True)

        # Remove tick labels but keep the grid
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        # Optionally, remove the axis entirely if you want a clean image with just the plot
        # ax.axis('off')  # This command turns off the axes completely, including the borders

        # Set aspect of the plot to be equal, to keep the image from distorting
        ax.set_aspect('equal')

        width = 0.25
        height = 0.15
        positions_dict = {
            1: [0.05, 0.3, width, height],
            2: [0.25, 0.1, width, height],
            3: [0.525, 0.1, width, height],
            4: [0.725, 0.3, width, height],
            5: [0.725, 0.55, width, height],
            6: [0.525, 0.775, width, height],
            7: [0.25, 0.775, width, height],
            8: [0.05, 0.55, width, height]
        }
        cmap = plt.get_cmap('BrBG')
        levels = np.linspace(-3, 3, 11)
        norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

        # Draw subpanels on top of the original figure
        for i, phase in enumerate(range(1, 9)):
            subax = fig.add_axes(positions_dict[phase], projection=ccrs.PlateCarree())
            xp = iplt.pcolormesh(phase_cubes[i], axes=subax, norm=norm, cmap=cmap, alpha=0.75)
            subax.coastlines()
            subax.set_title(f'Phase {phase}')

        plt.tight_layout()
        plt.savefig(os.path.join(self.parent_dir, 'data', 'BSISO_Phases_BG.png'))
        plt.close()

    def plot_bsiso_indices(self, date, members, combined_df, ens_mean_df, plot_file):
        # Load the background image
        img = Image.open(os.path.join(self.parent_dir, 'data', 'BSISO_Phases_BG.png'))

        # Set up the plot
        fig, ax = plt.subplots(figsize=(10, 10))
        xx = 4.15
        ax.imshow(img, extent=[-xx, xx, -xx, xx])  # Adjust these values based on your actual data
        # ax.plot(range(2),range(2))
        x = 4
        ax.set_ylim(-x, x)
        ax.set_xlim(-x, x)
        # Remove grid
        ax.grid(True)  # This disables the grid

        # Remove axis labels and tick marks
        # ax.set_xticks([])  # No x ticks
        # ax.set_yticks([])  # No y ticks

        # Optionally, remove the axis entirely if you want a clean image with just the plot
        ax.axis('on')  # This command turns off the axes completely, including the borders

        # Set aspect of the plot to be equal, to keep the image from distorting
        ax.set_aspect('equal')

        cmap = plt.get_cmap('BrBG')
        levels = np.linspace(-3, 3, 11)
        norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)
        for mem in members:
            df = combined_df.loc[combined_df.mem == int(mem)].iloc[-8:]
            ax.scatter(df.PC1, df.PC2, s=df.amp * 50, color='grey', alpha=0.2)
            ax.plot(df.PC1, df.PC2, color='grey', alpha=0.2)

        analysis = ens_mean_df.iloc[-20:-7]
        ax.scatter(analysis.PC1, analysis.PC2, s=analysis.amp * 20, alpha=0.8)
        ax.plot(analysis.PC1, analysis.PC2, color='grey', linewidth=3, alpha=0.8)

        forecast = ens_mean_df.iloc[-8:]
        ax.scatter(forecast.PC1, forecast.PC2, s=forecast.amp * 50, color='blue', alpha=0.8)
        ax.plot(forecast.PC1, forecast.PC2, color='blue', linewidth=3, alpha=0.8)
        for i, row in forecast.iterrows():
            ax.text(row.PC1 + 0.075, row.PC2 + 0.075, str(row.date), ha="left", va="center",
                    bbox=dict(boxstyle="round", alpha=0.4, ec=(1., 0.5, 0.5), fc=(1., 0.8, 0.8), ))
        plt.title(f"BSISO Index forecast: {date.strftime('%Y-%m-%d')}")
        plt.tight_layout()
        plt.savefig(plot_file)
        print(f'{plot_file} plotted.')

    def mpl_static_bsiso_plot(self, date, members, title_prefix='MOGREPS'):
        date_label = date.strftime("%Y%m%d")

        html_file_dir = os.path.join(self.config_values['plot_ens'], date_label)
        if not os.path.exists(html_file_dir):
            os.makedirs(html_file_dir)
        html_file = os.path.join(html_file_dir,
                                 f'BSISO_Index_{date_label}_EnsMean.png')

        combined_df = self.make_combined_df(date, members)
        ens_mean_df = self.make_ens_mean_df(combined_df)

        phase_cubes = self.read_phase_composite_cubes()

        # Generate the background for the plot
        # Only need to run it once
        #self.plot_background(phase_cubes)

        self.plot_bsiso_indices(date, members, combined_df, ens_mean_df, html_file  )
        print('Plotted %s' % html_file)

        self.write_dates_json(date)






