# Fluorescent Macroscopy Timelapse

Idea: shoot timelapses of bacterial colonies, genetically modified to produce fluorescent proteins, using LEDs of different colors to trigger the different fluorescent populations' responses, optical filters to isolate the fluorescent signals, and a DSLR camera to capture images. All credit for the idea goes to Michael Baym @ [baymlab.hms.harvard.edu](https://baymlab.hms.harvard.edu/)

## Run it
`./fluo_timelapse.py config.json`

An example of configuration dictionary is included at the beginning of the script, which is used automatically if no command line argument is passed.

Stop it using SIGINT (`Ctrl`+`C`).

## Dev it
LEDs are controlled using a USB relay switch like [this](https://numato.com/docs/8-channel-usb-relay-module/), controlled through its serial interface. If you are using other brands than Numato, change the `relay on [n]` and `relay off [n]` commands used to control lighting accordingly.

The filters are selected using an [USB filter wheel](https://www.sxccd.com/sx-usb-filter-wheel). This model implements the HID protocol (like mice and keyboards) and its manual is available [here](https://www.sxccd.com/handbooks/The%20Universal%20Filter%20Wheel.pdf).

Cameras are controlled using a Python wrapper for [gphoto](http://gphoto.org/), a free, redistributable, ready to use set of digital camera software applications for Unix-like systems which supports more than 2500 cameras. While only Sony camera are working at the moment, any camera supported by `libgphoto` can be used with virtually no modification other than the PTP configuration field names (e.g. `f-value`, `iso` etc.), which unfortunately are manufacturer-dependant.

## Requirements
- Unix environment (tested on OSX and ArchLinux)
- Python 3
- [`pyserial`](https://pypi.org/project/pyserial/) Python library for controlling filter wheel
- [`hid`](https://pypi.org/project/hid/) Python library
- [`gphoto2`](https://pypi.org/project/gphoto2/) Python library

## TODO
- Support for all cameras by modifying the configuration dictionary depending on the manufacturer (current version only works with Sony)
- Add multithreading and error detection for a smoother and reliable experience
- Develop simple UI for previewing, starting the timelapse and changing parameters without using CLI or modifying code
