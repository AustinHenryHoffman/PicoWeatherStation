import random
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
    r = urequests.get("http://api.weatherapi.com/v1/forecast.json?key=1523873bc3d04c4f823185542232405&q=63031&days=2&aqi=no&alerts=no")
    weather_data = r.json()
    #temp = data['current']['temp_f']
    #looks = data['current']['text']
    return weather_data

def get_current_date():
    r = urequests.get("http://192.168.1.4:5000")  # Server that returns the current GMT+0 time.
    date = r.json()["date"]
    return date
def main():

    tft.init()
    tft.fill(st7789.BLUE)
    weather_data = get_current_forecast()
    current_date = get_current_date()

    while True:
        r = urequests.get("http://192.168.1.4:5000")  # Server that returns the current GMT+0 time.
        date = r.json()["date"]
        time = r.json()["time"]
        if date != current_date:
            current_date = get_current_date()
            weather_data = get_current_forecast()
        tft.text(bigFont, date, 80, 0, st7789.GREEN, st7789.BLUE)
        tft.text(bigFont, time, 90, 30, st7789.GREEN, st7789.BLUE)
        tft.text(medFont, str(weather_data['current']['condition']['text']), 0, 60, st7789.GREEN, st7789.BLUE)
        # current temp
        tft.text(medFont, (f"Current Temp:{weather_data['current']['temp_f']}F"), 0, 90, st7789.GREEN, st7789.BLUE)
        # max temp
        tft.text(medFont, (f"Max Temp:{weather_data['forecast']['forecastday'][0]['day']['maxtemp_f']}F"), 0, 120, st7789.GREEN, st7789.BLUE)
        # min temp
        tft.text(medFont, (f"Min Temp:{weather_data['forecast']['forecastday'][0]['day']['mintemp_f']}F"), 0, 150, st7789.GREEN, st7789.BLUE)

    #while True:
        #tft.fill(st7789.RED)
        #center("Hello")
        #utime.sleep(2)
    #tft.fill(st7789.BLACK)


main()
