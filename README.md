# MQTT Bed

A project to enable MQTT control for BLE adjustable beds. Currently supported adjustable beds are:

- Serta adjustable beds with Bluetooth, like the [Serta Motion Perfect III](https://www.serta.com/sites/ssb/serta.com/uploads/2016/adjustable-foundations/MotionPerfectIII_Manual_V004_04142016.pdf)
- 'Glide' with the jiecang BLUE controller (Dream Motion app)
- 'A H Beard' with the DerwentOkin BLE controller ("Comfort Enhancement 2" aka "Comfort Plus" app)
- Linak KA20IC with the "Bed Control" app


## Requirements
First, you need to install bluepy from your package manager of choice. On a pi running Debian, you can use the following apt command to install Poetry, bluez and its dependencies:

```sh
sudo apt update
sudo apt install python3-pip pipx bluez libglib2.0-dev
pipx install poetry
pipx ensurepath
```

You will need to log out and log back in for the PATh chnages to take effect.
You can then install the necessary Python dependencies:

```sh
cd mqtt-bed
poetry install
```

This will automatically istall all of the necessary dependencies outlined in the `pyproject.toml` file. If you prefer not to use Poetry, you can still do the typical `pip3 install .` but will need to maintain your own virtual environment.


## Configuration
To configure all of the setting sused in the program, such as the MQTT credentials, bluetooth address of your bed, etc, you will need to modify the values in `config.yaml`. This setp is **essential** to getting your integration functional.

### Bed address
There are numerous ways to get ther address for your bed. If you can already control the bed via your phone, check the list of paired bluetooth devices, and find the address for your bed's connection in the format `00:00:00:00:00:00`. 

If you have a Serta bed, and are using the [Serta MP Remote app](https://apk-dl.com/serta-mp-remote/), you can find the mac address there.

Otherwise, you can use `hcitool` from the `bluez` package to find the address of your bed:

```console
$ hcitool lescan
LE Scan ...
61:61:61:4E:A0:B0 (unknown)
5F:E4:19:C4:13:CC (unknown)
6F:40:F7:4A:8E:23 (unknown)
7C:EC:79:FF:6D:02 (unknown)
7C:EC:79:FF:6D:02 base-i4.00000233
```

Once you have the address for your bed, you will need to fill that into the `BED_ADDRESS` variable in the `config.yaml` file.


## Usage
To run the program in the poetry virtual environment, you can run:

```sh
poetry run python /path/to/mqtt-bed/mqtt-bed.py
```

You will need to substitute the correct path to the program source depending on where you cloned the repository.

The program has one optional argument, which will control the verbosity of the program. By default, the log level is set to `INFO` but can be easilt changed with the `--log` option. When doing development or troubleshooting, it is recommended to runm with `--log DEBUG`

```console
usage: mqtt-bed.py [-h] [--log LOG_LEVEL]

BLE adjustable bed control over MQTT

options:
  -h, --help       show this help message and exit
  --log LOG_LEVEL  Set the log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
```

## Systemd Service
If you are using a dedicated device (like a Raspberry/Orange Pi Zero W) to run this program, you will likely want to create a Systemd service to run this application at startup, and restart after crashes. To do this on a Debian-based system, you will need to create a file called `/etc/systemd/system/mqtt-bed.service`, and paste the following contents:

```ini
[Unit]
Description=mqtt-bed service
After=network.target

[Service]
ExecStart=/home/pi/.local/bin/poetry run python /home/pi/mqtt-bed/mqtt-bed.py
WorkingDirectory=/home/pi/mqtt-bed
User=pi
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
```

In this file, you may need to swap out the username in the `User` variable, as well as the paths used in `ExecStart` and `WorkingDirectory`. The `ExecStart` command should contain:

1. `/path/to/poetry run python` which can be found by running `which poetry`
2. The absolute path to the `mqtt-bed.py` file.

After creating this file, you will need to run `sudo systemctl daemon-reload` to grab the new service file, `sudo systemctl enable mqtt-bed` to run the service on boot, and `sudo systemctl start mqtt-bed` to start the service for the first time.

You can check the status of the service at any time by running `sudo systemctl status mqtt-bed`.

You can also view the live logs from this service at any time by running `sudo journalctl -u mqtt-bed.service -f`

## Home Assistant Integration
The YAML used in Home Assistant to integrate your bed will vary by your installation and bed type, but you can find example YAML for in the `homeassistant-script.yaml` file in this repository.

In addition, it is common to run the MQTT Broker service in your Home Assitant installation if you do not have a broker running already, in which case you can use the [official Mosquito broker addon](https://github.com/home-assistant/addons/blob/master/mosquitto/DOCS.md). Once you have your broker setup, you will want to fill in your Home Assistant information in the MQTT config section of the `config.yaml` file.

## Trusting Bluetooth device on Linux

If you are running this application on a dedicated device, you likely need to pair and trust the bed on your device. 

First, you need to put your bed into pairing mode. The method to do this will be highly dependent on your bed type.

Once it is in pairing mode, you can run the following `bluetoothctl` commands to enable BLE, scan for the device, pair, and trust the bed:

```sh
bluetoothctl
[bluetooth]# power on
[bluetooth]# agent on
[bluetooth]# default-agent
[bluetooth]# scan on
```

Now, you should be able to find your bed in the list of discovered devices. For example: 

```command
[NEW] Device 00:00:00:00:00:00 Bed
```

Now you'll want to initiate pairing with the device, connect once, trust the device, and disconnect. You will need to substitute in the correct address for your device: 

```sh
[bluetooth]# pair 00:00:00:00:00:00
[bluetooth]# connect 00:00:00:00:00:00
[bluetooth]# trust 00:00:00:00:00:00
[bluetooth]# disconnect 00:00:00:00:00:00
[bluetooth]# exit
```

## Contributing
If your adjustable bed is not integrated into this repository yet, and you create your integration, it would be great to add your controller to this project for other to use!

To integrate your own bed, you should follow the examples in `controllers/dewertokin.py` and `controllers/linak.py` utilizing the bluepy package rather than the deprecated pygatt/gatttool integrations.

Just cretae your own controller class with an `__init__` function to kick off the connection to your bed, and add your contorller to the list of valid controllers in the `main()` function of `mqtt-bed.py`. 


## Resources
* https://github.com/danisla/iot-bed
* https://www.jaredwolff.com/get-started-with-bluetooth-low-energy/
