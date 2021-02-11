# mqtt-bed

MQTT control for Serta adjustable beds with Bluetooth, like the [Serta Motion Perfect III](https://www.serta.com/sites/ssb/serta.com/uploads/2016/adjustable-foundations/MotionPerfectIII_Manual_V004_04142016.pdf)

Based upon code from https://github.com/danisla/iot-bed

## Requirements
It requires [paho-mqtt](https://pypi.org/project/paho-mqtt/), which can be installed with Pip, and also [gatttool](http://manpages.ubuntu.com/manpages/cosmic/man1/gatttool.1.html), part of the [bluez](http://www.bluez.org/) package (sudo apt install bluez.)
[hcitool](http://manpages.ubuntu.com/manpages/focal/en/man1/hcitool.1.html) will probably be needed, to find the address of your bed, which is part of bluez also.

## Finding the address of your bed
```
$ hcitool lescan 
LE Scan ...
61:61:61:4E:A0:B0 (unknown)
5F:E4:19:C4:13:CC (unknown)
6F:40:F7:4A:8E:23 (unknown)
7C:EC:79:FF:6D:02 (unknown)
7C:EC:79:FF:6D:02 base-i4.00000233
$
```
or if you have the [Serta MP Remote app](https://apk-dl.com/serta-mp-remote/) installed on your phone, you can find the mac address there.

Your bed will likely have a name starting with *base-i4*. That is the address you want to put in the config.py file.

## Resources
* https://github.com/danisla/iot-bed
* https://www.jaredwolff.com/get-started-with-bluetooth-low-energy/
