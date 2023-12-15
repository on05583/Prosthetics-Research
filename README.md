# EMG Sensing and Prosthetics Research at the UGA Virtual Experience Lab
___________________________________________________________

# About

This research project explores the integration of Electromyography (EMG) sensors to capture muscle data for controlling a human-like avatar limb in a Unity environment. The system 
translates real-time EMG signals into avatar movements. The goal of this project is to provide amputees with a system that will allow them to regain the feeling of their limb and 
reduce the effects of phantom limb pain (PLP). It uses a minimum of 3 electrodes (dry or wet), two are placed on each of the muscles of interest and one electrode is used as the 
ground. Electrodes are connected to an OpenBCI Ganglion Board which captures the muscle data from the electrodes. The data is obtained from the ganglion using Bleak's Bluetooth
Low Energy Library for data processing and filtering. The processed data is published to Unity through an MQTT broker. Once the data is published to Unity it is used to control the
avatar limb in real time.

___________________________________________________________


# Setup

## Hardware
[OpenBCI Ganglion Board](https://shop.openbci.com/products/ganglion-board?utm_source=Google-Ads&utm_medium=g&utm_campaign=New_User_Prospecting&utm_adgroudp=New_User_Prospecting_-_dynamic_ad_group&utm_term=&gad_source=1&gclid=CjwKCAiAvdCrBhBREiwAX6-6Uu9az7JFnPIeuNssjLoS34EtB_0Akm6FYNOwoDYpc4Nf-gGQWIKaOhoCRF0QAvD_BwE)

[Electrode cables](https://shop.openbci.com/products/emg-ecg-snap-electrode-cables?variant=37345654079646)

[M5 StickC](https://shop.m5stack.com/products/stick-c)

Purchase a minimum of 3 of dry or wet snap-on electrodes. Results will be better with a wet electrode.

Connect the positive electrode to the top of channel 1, and the negative to the bottom of channel 1. Connect the
ground to the bottom pin on D_G, or the driven ground. 

Attach the positive electrode on the surface muscle, near the top, and the negative on the bottom
of the same muscle. Ensure that the electrodes are in line with the muscle fibers and are away from joints and bones that
may disrupt the signal. It is important to isolate the muscle so that changes to the rest of the arm do not affect the signal.
Connect the ground to a different arm or to another muscle on the body, as it establishes a baseline that is used in the
computation for the voltage readings.

Power values are calculated by taking the sum of the absolute value of the magnitudes minus a standard baseline magnitude, over a range of frequencies, which gives us a more consistent “on-off” signal:

$$
input = (\sum_{i=start frequency}^{end frequency} (|magnitude[i] - {\text{WET ELEC}}|))/({\text{number of frequencies}})
$$

The standard baseline value, or WET_ELEC, needs to be tuned to each individual - you can tune this value by setting up the hardware and wiring, and then finding the value that the line falls to approximately on the left, from 13-40Hz. This is the baseline value.

This program makes use of Bleak's Bluetooth Low Energy library to bypass the required dongle. As such, the 
device running the program __must have Bluetooth capability__.

-----------------------------------------------------------

## Installation

Setting up the gyroscope will also be included with the installation. This process is fairly simple; the first step will be to download the Arduino IDE from the website with the link included (https://www.arduino.cc/en/software). The next step will be to add the m5StickC to the list of boards in the manager menu. This can be done by pasting the following link into the additional boards manager section (https://m5stack.oss-cn-shenzhen.aliyuncs.com/resource/arduino/package_m5stack_index.json). The next step will be to run the program on the board while installing any required dependencies. Once the program compiles and runs successfully, it will start publishing the gyroscope data over mqtt at which point it is retrievable using the same process as the other data.

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

This system requires the use of Unity, the download link can be found [here](https://unity.com/download).

Once Unity is downloaded and an account is made, create a 3D Project. Then copy the folders Assets, Packages, and Project Settings in this repository to your project. The necessary 
scripts and files should now be in your project. 

The avatar used in this project was created using [Meta Person Avatar](https://avatarsdk.com/).

You may create your own avatar to be used in your project for free using the website. Once created export the avatar to your local computer. In Unity, move your avatar file into
the assets folder of your Unity project. The avatar file should appear in your 3D Project. Once uploaded into Unity, select the avatar in the Assets folder. Within the inspector 
window on the right, ensure Material Creation Mode is set to "Standard (Legacy)", Location is set to "Use External Materials (Legacy)", Naming is set to "Model Name + Model's 
Material", and search is set to "Recursive-Up".

For connecting the broker to Unity see: https://workshops.cetools.org/codelabs/CASA0019-unity-mqtt/index.html?index=..%2F..index#0
___________________________________________________________

### Authors:
Dr. Kyle Johnsen, Jacob Kilburn, Amr Mohamed, Omar Naqib, Rishab Seshadri
