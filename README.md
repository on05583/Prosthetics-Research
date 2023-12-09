# EMG Sensing and Prosthetics Research, led by Dr. Kyle Johnsen at the UGA Virtual Experience Lab
-----------------------------------------------------------
### Jacob Kilburn, Amr Mohamed, Omar Naqib, Rishab Seshadri
___________________________________________________________

# Setup

## Hardware
[OpenBCI Ganglion Board](https://shop.openbci.com/products/ganglion-board?utm_source=Google-Ads&utm_medium=g&utm_campaign=New_User_Prospecting&utm_adgroudp=New_User_Prospecting_-_dynamic_ad_group&utm_term=&gad_source=1&gclid=CjwKCAiAvdCrBhBREiwAX6-6Uu9az7JFnPIeuNssjLoS34EtB_0Akm6FYNOwoDYpc4Nf-gGQWIKaOhoCRF0QAvD_BwE)
[Electrode cables](https://shop.openbci.com/products/emg-ecg-snap-electrode-cables?variant=37345654079646)
Purchase a minimum of 3 of dry or wet snap-on electrodes. Results will be better with a wet electrode.

Connect the positive electrode to the top of channel 1, and the negative to the bottom of channel 1. Connect the
ground to the bottom pin on D_G, or the driven ground. 

Attach the positive electrode on the surface muscle, near the top, and the negative on the bottom
of the same muscle. Ensure that the electrodes are in line with the muscle fibers and are away from joints and bones that
may disrupt the signal. It is important to isolate the muscle so that changes to the rest of the arm do not affect the signal.
Connect the ground to a different arm or to another muscle on the body, as it establishes a baseline that is used in the
computation for the voltage readings.

This program makes use of Bleak's Bluetooth Low Energy library to bypass the required dongle. As such, the 
device running the program __must have Bluetooth capability__.

-----------------------------------------------------------

## Installation

The installation of this program requires the use of Python3, the installation of which
can be found [here](https://realpython.com/installing-python/#how-to-install-python-on-windows).

As of Python 3.4, __all Python3 versions already have pip installed.__ However, if you have
an older version, follow the [pip installation steps](https://pip.pypa.io/en/stable/installation/) as well.

Open an instance of your terminal within the project's directory (Prosthetics-Research)


This project makes use of several Python libraries that can be installed with the command below:

`$ python3 -m pip install aioconsole numpy bleak bokeh brainflow paho-mqtt`


To run the project, run the following command:

`$ bokeh serve --show data_visualizer.py`

-----------------------------------------------------------

## Software

This program makes use of an MQTT broker to publish the data to Unity, and an MQTT Broker
will be necessary for the setup. Change the values within `data_visualizer.py` near the
`# MQTT Broker` comment in order to publish the data. 

The constants provided need to be tuned depending on each device and setup. The current values are
set up to work with dry and wet electrodes, but may need to be increased or decreased depending on the
wanted sensitivity of the power produced by signal. This can be changed with the `DRY_ELEC` and `WET_ELEC`
constants, as well as the `get_input()` function.

___________________________________________________________

