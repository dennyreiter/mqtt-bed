# mqtt-bed

MQTT control for Serta adjustable beds with Bluetooth

Based upon code from https://github.com/danisla/iot-bed

It requires [[https://pypi.org/project/paho-mqtt/ paho-mqtt]], which can be installed with Pip, and also [[http://manpages.ubuntu.com/manpages/cosmic/man1/gatttool.1.html gatttool]], part of the bluez package (sudo apt install bluez.)
hcitool will probably be needed, to find the address of your bed, which is part of bluez also.

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

Your bed will likely have a name starting with *base*. That is the address you want to put in the config.py file.
