import utime
import st7789
import tft_config
import vga2_bold_16x32 as bigFont
import vga1_8x16 as smallFont
import network   # handles connecting to WiFi
import urequests    # handles making and servicing network requests
from machine import Pin, I2C
import machine
import ahtx0
import json

tft = tft_config.config(3)
# Connect to network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Start networking
with open("./etc/network_config.json", "r") as file:
    config_data = json.load(file)
print(config_data)

network_info = config_data["network"]
ssid = network_info["ssid"]
password = network_info["network_password"]
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

SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240
CHAR_WIDTH = 6  # Width of each character
print(f"small Font width: {smallFont.WIDTH}")
print(f"small Font height: {smallFont.HEIGHT}")
CHAR_HEIGHT = 16  # Height of each character
# Function to print text with wrapping


def set_pico_time_from_server():

    response = urequests.get("http://192.168.1.4:5000/datetime")
    data = response.json()

    year, month, day = map(int, data["date"].split("-"))
    hour, minute, second = map(int, data["time"].split(":"))

    rtc = machine.RTC()
    rtc.datetime((year, month, day, 0, hour, minute, second, 0))


def print_pico_time():
    rtc = machine.RTC()
    year, month, day, weekday, hours, minutes, seconds, subseconds = rtc.datetime()
    current_date = "{:04d}-{:02d}-{:02d}".format(year, month, day)
    current_time = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
    # print("Current Date:", current_date)
    # print("Current time:", current_time)
    date_time = [current_date, current_time]
    return date_time


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
    # new experiemental http://api.weatherapi.com/v1/forecast.json?key=1523873bc3d04c4f823185542232405&q=63031&days=1&aqi=no&alerts=yes
    # OLD and WORKING "http://api.weatherapi.com/v1/forecast.json?key=1523873bc3d04c4f823185542232405&q=63031&days=1&aqi=no&alerts=no"
    r = urequests.get("http://api.weatherapi.com/v1/forecast.json?key=1523873bc3d04c4f823185542232405&q=63031&days=1&aqi=no&alerts=yes")
    weather_data = r.json()
    #The plan here is to return only the data that I need rather than keep the entire json stored in memory. This
    #should resolve the memory errors that I was getting when attempting to refresh weather data.
    current_condition = str(weather_data['current']['condition']['text'])
    current_temp = str(weather_data['current']['temp_f'])
    max_temp = weather_data['forecast']['forecastday'][0]['day']['maxtemp_f']
    min_temp = weather_data['forecast']['forecastday'][0]['day']['mintemp_f']
    rain = weather_data['forecast']['forecastday'][0]['day']['daily_chance_of_rain']
    moon_phase = weather_data['forecast']['forecastday'][0]['astro']['moon_phase']
    alerts = weather_data['alerts']['alert'][0]['headline']
    weather_data = [current_condition, current_temp, max_temp, min_temp, rain, moon_phase, alerts]
    return weather_data


def get_current_date():
    r = urequests.get("http://192.168.1.4:5000/datetime")  # Server that returns the current GMT+0 time.
    date = r.json()["date"]
    return date


def print_wrapped_text(text, y):
    x = 0
    y = y
    max_lines = SCREEN_HEIGHT // CHAR_HEIGHT
    max_chars_per_line = SCREEN_WIDTH // CHAR_WIDTH

    # Split the text into words
    words = text.split()

    for word in words:
        word_length = len(word)
        if x + word_length * CHAR_WIDTH >= SCREEN_WIDTH:
            # If the word exceeds the screen width, move to the next line
            x = 0
            y += CHAR_HEIGHT
            if y >= SCREEN_HEIGHT:
                break
        tft.text(smallFont, word, x, y, st7789.RED, st7789.BLUE)

        # Update the x coordinate for the next word
        x += word_length * CHAR_WIDTH + CHAR_WIDTH

        if x >= SCREEN_WIDTH:
            # If the x coordinate exceeds the screen width, move to the next line
            x = 0
            y += CHAR_HEIGHT
            if y >= SCREEN_HEIGHT:
                break


def print_weather_data(weather_data):
    # condition
    current_condition = str(weather_data[0])
    print(current_condition)
    if current_condition == "Sunny":
        tft.fill_rect(0, 65, 160, smallFont.HEIGHT, st7789.BLACK)
        tft.text(smallFont, str(weather_data[0]), 0, 65, st7789.YELLOW, st7789.BLUE)
    elif current_condition == "Clear":
        tft.fill_rect(0, 65, 160, smallFont.HEIGHT, st7789.BLACK)
        tft.text(smallFont, str(weather_data[0]), 0, 65, st7789.WHITE, st7789.BLUE)
    elif current_condition == "Partly cloudy":
        tft.fill_rect(0, 65, 160, smallFont.HEIGHT, st7789.BLACK)
        tft.text(smallFont, str(weather_data[0]), 0, 65, st7789.BLACK, st7789.BLUE)
    else:
        tft.fill_rect(0, 65, 160, smallFont.HEIGHT, st7789.BLACK)
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
    # moon phase
    tft.fill_rect(0, 165, 300, smallFont.HEIGHT, st7789.BLACK)
    tft.text(smallFont, f"Moon Phase:{weather_data[5]}", 0,
             165, st7789.GREEN, st7789.BLUE)
    # Alerts
    tft.fill_rect(0, 185, 300, smallFont.HEIGHT, st7789.BLACK)
    print_wrapped_text(f"Alert:{weather_data[6]}", 185)


def print_indoor_climate(date, time):
    temperature = "%0.2f" % (sensor.temperature * 1.8 + 32)
    humidity = "%0.2f" % sensor.relative_humidity
    length = len("Indoor Climate:")
    tft.text(smallFont, "Indoor Climate:", tft.width() - length * smallFont.WIDTH, 65, st7789.GREEN, st7789.BLUE)
    length = len(str(temperature))+1
    tft.text(smallFont, f"{temperature}F", tft.width() - length * smallFont.WIDTH, 85, st7789.GREEN, st7789.BLUE)
    length = len(str(humidity)) + 1
    tft.text(smallFont, f"{humidity}%", tft.width() - length * smallFont.WIDTH, 105, st7789.GREEN, st7789.BLUE)
    data = {
        'date': date,
        'time': time,
        'temperature': temperature,
        'humidity': humidity,
        'location': 'Master Bedroom'
    }
    # log only on even minutes
    # if int(time.split(":")[1]) % 10 == 0:
    try:
        response = urequests.post('http://192.168.1.4:5000/climate', json=data)
        print(response.text)
    except Exception as e:
        print(e)
        pass


def main():
    failed_connect = 0
    tft.init()
    tft.fill(st7789.BLACK)
    current_date = ""
    try:
        set_pico_time_from_server()
        weather_data = get_current_forecast()
        current_date = get_current_date()
        print_weather_data(weather_data)

    except Exception as e:
        print(e)
        pass
    while True:
        if failed_connect == 1:
            tft.fill(st7789.BLACK)
        try:
            #r = urequests.get("http://192.168.1.4:5000/datetime")  # Server that returns the current GMT+0 time.
            failed_connect = 0
            date_time = print_pico_time()
            #date = r.json()["date"]
            #time = r.json()["time"]
            date = date_time[0]
            time = date_time[1]
            minute = str(date_time[1]).split(":")[1]
            second = str(date_time[1]).split(":")[2]

        except Exception as e:
            print(e)
            print("Failure at time")
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
        # refresh weather data every half hour
        if minute == "59" and int(second) > 58:
            weather_data = get_current_forecast()
            print_weather_data(weather_data)
        tft.text(bigFont, date, 80, 0, st7789.GREEN, st7789.BLUE)
        tft.text(bigFont, time, 90, 30, st7789.GREEN, st7789.BLUE)
        print_indoor_climate(date, time)


main()
