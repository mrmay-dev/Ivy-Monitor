# Ivy Monitor

This sensor array, attatched to an Adafruit QT Py S2 monitors a plants environment:

- *SHT40:* temperature and humidity
- *Adaruit Soil Sensor:* soil moisture
- *TSL2591:* light
- *SGP30:* eCO2 (equivalent CO2) and TVOC (Total Organic Compounds)

Data is published on an MQTT broker in two intervals. Every 30 minutes all datapoints are sent. Every five miutes only eCO2 and TVOC are updated.

This data helps better understand the plants' needs and environment. It is recovering from not knowing how to care for it.

![Recovering English Ivy plant in a pink pot with with a three sensor array attatched.](photos/whole_plant.jpg "English Ivy in Pink Pot")
![Three sensors, an Adafruit QT Py S2 attatched to an SHT40, SGP30, and a TLS2591 all attatched to a pink pot.](photos/front_view.jpg "English Ivy")
![Closeup of an Adafruit Soil Sensor in the ground.](photos/soil_detail.jpg "English Ivy")
