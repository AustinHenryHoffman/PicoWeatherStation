import utime
import st7789
import tft_config
import vga2_bold_16x32 as bigFont
import vga2_16x32 as medFont
import vga1_8x16 as smallFont
import network   # handles connecting to WiFi
import urequests    # handles making and servicing network requests
from machine import Pin, I2C
import ahtx0

tft = tft_config.config(3)
# Connect to network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Fill in your network name (ssid) and password here:
ssid = 'Tauttechsystems'
password = 'Ellajane4485!'
wlan.connect(ssid, password)

#AHT 10 init
i2c2 = I2C(1, scl=Pin(27), sda=Pin(26))

"""
used to get the device i2c address which needs to be updated in the ahtx0 driver
devices = i2c2.scan()
0x39
if devices:
    for d in devices:
        print(hex(d))
"""

# Create the sensor object using I2C
sensor = ahtx0.AHT10(i2c2)

def center(text):
    length = 1 if isinstance(text, int) else len(text)
    tft.text(
        bigFont,
        text,
        tft.width() // 2 - length // 2 * bigFont.WIDTH,
        tft.height() // 2 - bigFont.HEIGHT // 2,
        st7789.GREEN,
        st7789.BLUE)


def get_current_forecast():
    # r = urequests.get("http://api.weatherapi.com/v1/forecast.json?key=1523873bc3d04c4f823185542232405&q=63031&days=2&aqi=no&alerts=no")
    r = urequests.get("http://api.weatherapi.com/v1/forecast.json?key=1523873bc3d04c4f823185542232405&q=63031&days=1&aqi=no&alerts=no")
    weather_data = r.json()
    """The plan here is to return only the data that I need rather than keep the entire json stored in memory. This
    should resolve the memory errors that I was getting when attempting to refresh weather data."""
    current_condition = str(weather_data['current']['condition']['text'])
    current_temp = str(weather_data['current']['temp_f'])
    max_temp = weather_data['forecast']['forecastday'][0]['day']['maxtemp_f']
    min_temp = weather_data['forecast']['forecastday'][0]['day']['mintemp_f']
    rain = weather_data['forecast']['forecastday'][0]['day']['daily_chance_of_rain']
    weather_data = [current_condition, current_temp, max_temp, min_temp, rain, weather_data]
    return weather_data


def get_current_date():
    r = urequests.get("http://192.168.1.4:5000")  # Server that returns the current GMT+0 time.
    date = r.json()["date"]
    return date


def print_weather_data(weather_data):
    # condition
    current_condition = str(weather_data[0])
    if current_condition == "Sunny":
        tft.text(smallFont, str(weather_data[0]), 0, 65, st7789.YELLOW, st7789.BLUE)
    if current_condition == "Clear":
        tft.text(smallFont, str(weather_data[0]), 0, 65, st7789.WHITE, st7789.BLUE)
    if current_condition == "Partly cloudy":
        tft.text(smallFont, str(weather_data[0]), 0, 65, st7789.BLACK, st7789.BLUE)
    else:
        tft.text(smallFont, str(weather_data[0]), 0, 65, st7789.GREEN, st7789.BLUE)
    # current temp
    tft.text(smallFont, f"Current Temp:{weather_data[1]}F", 0, 85, st7789.GREEN, st7789.BLUE)
    # max temp
    max_temp = weather_data[2]
    if float(max_temp) >= float(90):
        tft.text(smallFont, f"High Temp:{weather_data[2]}F", 0, 105,
                 st7789.RED, st7789.BLUE)
    else:
        tft.text(smallFont, f"Max Temp:{weather_data[2]}F  ", 0, 105,
                 st7789.GREEN, st7789.BLUE)
    # min temp
    tft.text(smallFont, f"Low Temp:{weather_data[3]}F", 0, 125,
             st7789.GREEN, st7789.BLUE)
    # Rain?
    tft.text(smallFont, f"Rain:{weather_data[4]}% Chance", 0,
             145, st7789.GREEN, st7789.BLUE)

def print_indoor_climate():
    temperature = "%0.2f" % (sensor.temperature * 1.8 + 32)
    humidity = "%0.2f" % sensor.relative_humidity
    length = len(str(temperature))+1
    tft.text(smallFont, f"{temperature}F", tft.width() - length * smallFont.WIDTH, 65, st7789.GREEN, st7789.BLUE)
    length = len(str(humidity)) + 1
    tft.text(smallFont, f"{humidity}%", tft.width() - length * smallFont.WIDTH, 85, st7789.GREEN, st7789.BLUE)

def main():
    failed_connect = 0
    tft.init()
    tft.fill(st7789.BLACK)
    try:
        weather_data = get_current_forecast()
        current_date = get_current_date()
        print_weather_data(weather_data)
    except Exception as e:
        pass
    while True:
        if failed_connect == 1:
            tft.fill(st7789.BLACK)
        try:
            r = urequests.get("http://192.168.1.4:5000")  # Server that returns the current GMT+0 time.
            failed_connect = 0
            date = r.json()["date"]
            time = r.json()["time"]
            minute = time.split(":")[1]
            second = time.split(":")[2]
        except Exception as e:
            tft.fill(st7789.BLACK)
            failed_connect = 1
            tft.text(smallFont, "Failed to Reach Time Server.", 0, 0, st7789.GREEN, st7789.BLUE)
            utime.sleep(2)
            continue
        # refresh weather data daily
        if date != current_date:
            current_date = get_current_date()
            weather_data = get_current_forecast()
            print_weather_data(weather_data)
            print("weather data refreshed")
        # refresh weather data every hour
        if minute == "59" and int(second) > 58:
            weather_data = get_current_forecast()
            print_weather_data(weather_data)
            print("weather data refreshed")
        tft.text(bigFont, date, 80, 0, st7789.GREEN, st7789.BLUE)
        tft.text(bigFont, time, 90, 30, st7789.GREEN, st7789.BLUE)
        print_indoor_climate()


main()
