"""
Duventchezmoi main script.
"""

# standard packages
import os
import sys
import shutil
import configparser
import math
import datetime

# third party packages
import pygrib
import numpy as np

# local modules
from download_gfs import download_gfs


def write_report(data, file_name):
    """
    Write alert report displaying wind speed values.
    Input:
        -data       [dict, ...]
            contains for each row:
            {"date_str": str, "date_obj": datetime object, "wind_speed": float, "alert": bool}
        -file_name  str
    """
    print("not implemented yet")

def compute_mean_wind_speed(grib2_file):
    """
    Compute mean wind speed from GFS products.
    Input:
        -grib2_file     str
    Output:
        -               float
    """

    # open grib2 file
    grbs = pygrib.open(grib2_file)

    # fetch datasets
    u_grb = grbs.select(name="U component of wind")[0]
    v_grb = grbs.select(name="V component of wind")[0]

    # compute areal mean of U and V velocity
    u_vel = np.mean(u_grb.values)
    v_vel = np.mean(v_grb.values)

    # compute mean wind speed
    mean_wind_speed = np.sqrt(u_vel ** 2 + v_vel ** 2)

    return mean_wind_speed


def duventchezmoi(config_path):
    """
    Duventchezmoi main function.
    Input:
        -config_path    str
    """

    # read config
    config = configparser.ConfigParser()
    config.read(config_path)
    lat = float(config["main"]["lat"])
    lon = float(config["main"]["lon"])
    threshold = float(config["main"]["threshold"])
    data_path = config["main"]["data_path"]
    email_address = config["main"]["email"]
    cleaning = config["main"]["cleaning"].lower() in ["true"]

    # create extent on 0.25 deg grid around given coordinates
    extent = [
        math.floor(lon * 4) / 4,  # smallest lon (W bound)
        math.ceil(lat * 4) / 4,  # greatest lat (N bound)
        math.ceil(lon * 4) / 4,  # greatest lon (E bound)
        math.floor(lat * 4) / 4,  # smallest lat (S bound)
    ]

    # creating download directory
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    todays_data_path = os.path.join(data_path, today_str)
    if not os.path.exists(todays_data_path):
        os.makedirs(todays_data_path)

    # download gfs data
    try:
        download_gfs(extent, todays_data_path)
    except:
        sys.exit("Error in GFS data download")

    # loop through all hourly forecast gfs files
    data = [] # initiate list to store results for each forecast
    is_alert_triggered = False # initiate boolean to trigger alerts
    for file in os.listdir(todays_data_path):

        # compute mean wind speed
        wind_speed = compute_mean_wind_speed(os.path.join(todays_data_path, file))

        # compare value to threshold
        is_threshold_surpassed = wind_speed > threshold
        if is_threshold_surpassed: # trigger alert
            is_alert_triggered = True

        # store results in list
        data.append(
            {
                "date_str": os.path.splitext(file)[0],
                "date_obj": datetime.datetime.strptime(os.path.splitext(file)[0], "%Y%m%d_%H%M"),
                "wind_speed": wind_speed,
                "alert": is_threshold_surpassed
            }
        )

    # if alert triggered
    if is_alert_triggered:

        # write report
        report_filename = os.path.join(data_path, "{}.pdf".format(today_str))
        write_report(data, report_filename)

        # send email
        send_email(email_address, report_filename)

    # clear data path
    if cleaning:
        for d in [di for di in os.listdir(data_path) if os.path.isdir(os.path.join(data_path, di))]:
            shutil.rmtree(os.path.join(data_path, di))


if __name__ == "__main__":

    duventchezmoi_path = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(duventchezmoi_path, "config", "config.ini")

    duventchezmoi(config_path)
