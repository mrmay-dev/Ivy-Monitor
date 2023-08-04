# Ivy Monitor

import os

# Settings
# -------------------------
my_timezone = -7
plant_name = 'englishivy_70da9e'
publish_interval = (60 * 30)
aqi_interval = (60 * 5)


""" SGP30 has a 12 hour calibration window. If set to `True` the sensor will calibrate.
Otherwise it will attempt to fetch calibration from the `mqtt_topic` set below.
If no calibration is found, or MQTT fails, it will use calibration_fallback below.
Regularly updating the fallback values will ensure there is always a reasonable output.

See here for more on calibration:
https://learn.adafruit.com/adafruit-sgp30-gas-tvoc-eco2-mox-sensor
"""
calibrating_state = True
calibration_fallback = (36515, 37460)  # (eCO2, TVOC)

mqtt_broker = 'ip or address'
mqtt_port = 1883  # if not using SSL it's usually 1883
mqtt_username = os.getenv("mqtt_username")
mqtt_password = os.getenv("mqtt_password")
mqtt_base = 'mac2010/circuitpython/plants'
mqtt_topic = f'{mqtt_base}/{plant_name}'
mqtt_topic_aqi = f'{mqtt_base}/{plant_name}/sgp30'

warmup_time = 60 * 2

# Modules
# -------------------------
import gc
import time
import board
import busio
import json
import microcontroller
import rtc

# Hardware
import neopixel
import adafruit_sht4x
import adafruit_tsl2591
import adafruit_sgp30
from adafruit_seesaw.seesaw import Seesaw

# Networking
import wifi
import socketpool
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import adafruit_ntp

# Variables
publish_time = None
mqtt_fail_count = 0


# ----------------------
# Setup
# ----------------------
start = time.monotonic()
pool = socketpool.SocketPool(wifi.radio)


# NTP Time Setup
# -------------------------
days = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
months = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def time_check():
    """helper function to check time that has passed"""
    result = time.monotonic() - start
    return result
    

def the_time():
    """this function returns a date string"""
    t_object = time.localtime()
    # tm_wday = 0-6, 0 is Monday
    # tm_mon = 1-12, 1 is January
    result = (f'{days[t_object.tm_wday + 0]}, {months[t_object.tm_mon + -1]} {t_object.tm_mday}, {t_object.tm_year} at {t_object.tm_hour:02}:{t_object.tm_min:02}:{t_object.tm_sec:02}')
    return result


def set_time():
    """this function updates the time using ntp.org. """
    ntp_fail_count = 0
    update_success = False 
    while not update_success:
        try:
            ntp = adafruit_ntp.NTP(pool, server = '0.pool.ntp.org', tz_offset = my_timezone)
            r = rtc.RTC()
            r.datetime = ntp.datetime
            update_success = True
            print('New time has been set!')
            
        except (ValueError, RuntimeError, ConnectionError, OSError) as e:
            ntp_fail_count += 1
            print(f"Failed to get time. ({ntp_fail_count})\nRetry in 10 seconds.\n\n", e)
            time.sleep(10)
            if ntp_fail_count >= 6:
                microcontroller.reset()
            continue


# MQTT Setup
# -------------------------------------------------------

the_broker = "Mosquitto"

# Initialize a new MQTT Client object
io = MQTT.MQTT(
    broker = mqtt_broker,
    port = mqtt_port,
    username = mqtt_username,
    password = mqtt_password,
    socket_pool = pool,
    # ssl_context = ssl.create_default_context(),
)


def connect(mqtt_client, userdata, flags, rc):
    # This function will be called when the mqtt_client is connected
    # successfully to the broker.
    print("Connected to MQTT Broker!")
    print("Flags: {0}\n RC: {1}".format(flags, rc))


def new_message(client, topic, message):
    # Method called whenever user/feeds/led has a new value
    print(f'\nNew message on: {topic}:\n{message}\n')
    time_now = time.time()
    if not calibrating_state:
        a_new_message = json.loads(message)
        co2eq_base = a_new_message['sgp30']['baseline_eCO2']
        tvoc_base =  a_new_message['sgp30']['baseline_TVOC']
        
        sgp.set_iaq_baseline(co2eq_base, tvoc_base) calibration_fallback_eCO2
        print(f'\nCalibration set: ({sgp.baseline_eCO2}, {sgp.baseline_TVOC}).')
        
    if calibrating_state:
        print(f'Calibrating: {sgp30_calibration_time - time_now} seconds remaining.')
        
    
def disconnect(mqtt_client, userdata, rc):
    # This method is called when the mqtt_client disconnects
    # from the broker.
    print("Disconnected from MQTT Broker!")


def publish_all(data_string):
    print(f'\n\n    ---- PUBLISHING DATA ----\n\n')
    publish_success = False
    try: 
        print(f"Connecting to {the_broker}...")
        io.connect()
        mqtt_payload = json.dumps(data_string)
        io.publish(mqtt_topic, mqtt_payload, True)
        print(f'PUBLISHED TO:\n{mqtt_topic}\n{mqtt_payload}\n')
        io.disconnect()
        publish_success = True
    except Exception as e:
        print("Error:\n", str(e))
        print("Retrying later")
        # microcontroller.reset()
    
    if publish_success:
        publish_time = t_now + publish_interval
        mqtt_fail_count = 0
        print(f'\n\n    ---- DATA PUBLISHED #{mqtt_fail_count} ----\n\n')
    else:
        publish_time = t_now + 60
        mqtt_fail_count += 1
        print(f'\n\n    ---- data NOT published #{mqtt_fail_count} (waiting 60s) ----\n\n')
        if mqtt_fail_count >= 5:
            print('MQTT publishing has failed critically. Restarting board in 10s.')
            print('\n\n')
            pixel.fill((255, 0, 0))
            time.sleep(10)
            microcontroller.reset()
            # stop()
            
    time.sleep(3)
    return(publish_time)
    

def publish_AQI(aqi_data):
    print(f'\n\n    ---- PUBLISHING AQI ----\n\n')
    publish_success = False
    try: 
        print(f"Connecting to {the_broker}...")
        io.connect()
        aqi_payload = json.dumps(aqi_data)
        io.publish(mqtt_topic_aqi, aqi_payload, True)
        print(f'PUBLISHED TO:\n{mqtt_topic_aqi}\n{aqi_payload}\n')
        io.disconnect()
        publish_success = True
    except Exception as e:
        print("Error:\n", str(e))
        print("Retrying later")
        # microcontroller.reset()
    
    if publish_success:
        publish_aqi_time = t_now + aqi_interval
        mqtt_fail_count = 0
        print(f'\n\n    ---- AQI PUBLISHED #{mqtt_fail_count} ----\n\n')
    else:
        publish_aqi_time = t_now + 60
        mqtt_fail_count += 1
        print(f'\n\n    ---- AQI NOT published #{mqtt_fail_count} (waiting 60s) ----\n\n')
        if mqtt_fail_count >= 5:
            print('MQTT publishing has failed critically. Restarting board in 10s.')
            print('\n\n')
            pixel.fill((255, 0, 0))
            time.sleep(10)
            microcontroller.reset()
            
    time.sleep(3)
    return(publish_aqi_time)
    
    
io.on_connect = connect
io.on_message = new_message
io.on_disconnect = disconnect


# Device Setup
# ------------------------------------------------------

# i2c = board.STEMMA_I2C()  # frequency=100000)
i2c = busio.I2C(board.SCL1, board.SDA1, frequency=100000)
sht = adafruit_sht4x.SHT4x(i2c)
tsl = adafruit_tsl2591.TSL2591(i2c)
sgp = adafruit_sgp30.Adafruit_SGP30(i2c)
ss = Seesaw(i2c, addr=0x36)
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)


print("\nSGP30 serial #", [hex(i) for i in sgp.serial])
sgp30_calibration_time = None

sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION
# Can also set the mode to enable heater
# sht.mode = adafruit_sht4x.Mode.LOWHEAT_100MS
print("Current mode is: ", adafruit_sht4x.Mode.string[sht.mode], "\n")


# Data Collection Setup
# ------------------------------------------------------

def soil_sensor():
    # read moisture level through capacitive touch pad
    touch = ss.moisture_read()
    # read temperature from the temperature sensor
    soil_temp = ss.get_temp()
    return touch, soil_temp


def sht40():
    temperature, relative_humidity = sht.measurements
    return temperature, relative_humidity


def tsl2591():
    lux = tsl.lux
    infrared = tsl.infrared
    visible = tsl.visible
    full_spectrum = tsl.full_spectrum
    return lux, infrared, visible, full_spectrum


def sgp30(temp, rh):
    sgp.set_iaq_relative_humidity(celsius=temp, relative_humidity=rh)
    eCO2 = sgp.eCO2
    TVOC = sgp.TVOC
    baseline_eCO2 = sgp.baseline_eCO2
    baseline_TVOC = sgp.baseline_TVOC
    return eCO2, TVOC, baseline_eCO2, baseline_TVOC


# -------------------------------------
# Pre-Run One Shot
# -------------------------------------

set_time()

sgp30_calibration_time = None
if calibrating_state:
    sgp30_calibration_time = time.time() + (12*60*60)
if calibrating_state == False:
    sgp30_calibration_time = 0
    error_count = 0
    update_success = False
    while not update_success:
        try: 
            print(f"\nConnecting to {the_broker}...")
            io.connect()
            io.subscribe(mqtt_topic)
            io.loop()
            io.disconnect()
            update_success = True
        except Exception as e:
            error_count += 1
            if error_count > 6:
                sgp.set_iaq_baseline(calibration_fallback[0], calibration_fallback[1])
                print(f'Retried {error_count} times. Using fallback calibration.')
                # microcontroller.reset()  # ucomment if resetting the microcontroller is preferred
                break
            print("Error:\n", str(e), "(xerror_count)")
            print("Retrying later")
            time.sleep(10)

running_since = the_time()

device_info = f"""
         running_since = {running_since}
            plant_name = {plant_name}
      publish_interval = {publish_interval} seconds
     calibrating_state = {calibrating_state}
sgp30_calibration_time = {sgp30_calibration_time}
            mqtt_topic = {mqtt_topic}
         baseline_eCO2 = {sgp.baseline_eCO2}
         baseline_TVOC = {sgp.baseline_TVOC}
"""
print(device_info)

counter = 10
while counter > 0:
    print (f'\rContinuing in: {counter}s    ', end='')
    counter += -1
    time.sleep(1)
print('\n\n')



# ----------------------------------------
# Main Loop
# ----------------------------------------
t_now = time.time()
# sgp30_calibration_time = t_now + (60*5)
# publish_interval = 60*3
# publish_time = t_now + publish_interval
publish_time = t_now + warmup_time  # warmup sensors before first publish
publish_aqi_time = t_now + warmup_time + 10

while True:
    if t_now > sgp30_calibration_time:
        calibrating_state = False
    now_time = the_time()
    UTC_time = t_now + 28800
    update_remaining_time = publish_time - t_now
    next_aqi_update_in = publish_aqi_time - t_now
    calib_remaining_time = t_now - sgp30_calibration_time
    lux, infrared, visible, full_spectrum = tsl2591()
    soil_moisture, soil_temp = soil_sensor()
    temperature, relative_humidity = sht40()
    eCO2, TVOC, baseline_eCO2, baseline_TVOC = sgp30(temperature, relative_humidity)
    
    data_string = {
        'ip_address': f'{wifi.radio.ipv4_address}',
        'mqtt_fail_count': mqtt_fail_count,
        "running_since": running_since,
        "now_time": now_time,
        "UTC_time": UTC_time,
        "calibrating_state": calibrating_state,
        "calib_remaining_time": calib_remaining_time,
        "update_remaining_time": update_remaining_time,
        "tsl2591":{
            "full_spectrum": full_spectrum,
            "visible": visible,
            "infrared": infrared,
            "lux": lux,
            },
        "soil_sensor":{
            "soil_moisture": soil_moisture,
            "soil_temp": soil_temp,
            },
        "ambient": {
            "temperature": temperature,
            "relative_humidity": relative_humidity,
            },
        "sgp30": {
            "baseline_TVOC": baseline_TVOC,
            "baseline_eCO2": baseline_eCO2,
            "eCO2": eCO2,
            "TVOC": TVOC,
            },
    }

    # {str(" = "):>25}{}
    print(f'{json.dumps(data_string)} \nTIME TO NEXT UPDATE: {update_remaining_time} \nCALIBRATING: {calibrating_state} ({calib_remaining_time})\nAQI UPDATE in: {next_aqi_update_in}\n')
    
    
    if publish_aqi_time < t_now:
        aqi_data = {
            "UTC_time": UTC_time,
            "baseline_TVOC": baseline_TVOC,
            "baseline_eCO2": baseline_eCO2,
            "eCO2": eCO2,
            "TVOC": TVOC,
            }
        
        publish_aqi_time = publish_AQI(aqi_data)
    
    if publish_time < t_now:
        publish_time = publish_all(data_string)
    
    gc.collect()
    t_now = time.time()
    time.sleep(1)

