from utime import sleep, time
import st7789
import tft_config
import vga2_bold_16x32 as bigFont
import vga1_8x16 as smallFont
from network import WLAN, STA_IF   # handles connecting to WiFi
import urequests    # handles making and servicing network requests
from machine import Pin, I2C
import machine
import ahtx0
import json

tft = tft_config.config(3)


class NetworkManager:
    def __init__(self):
        self.wlan = WLAN(STA_IF)
        self.wlan.active(True)

    def connect_to_network(self):
        with open("./etc/network_config.json", "r") as file:
            config_data = json.load(file)
        network_info = config_data["network"]
        ssid = network_info["ssid"]
        password = network_info["network_password"]
        self.wlan.connect(ssid, password)
        while not self.wlan.isconnected():
            sleep(1)

    def is_connected(self):
        return self.wlan.isconnected()


class AHT10Sensor:
    def __init__(self):
        self.i2c = I2C(1, scl=Pin(27), sda=Pin(26))
        self.sensor = ahtx0.AHT10(self.i2c)
        # used to get the device i2c address which needs to be updated in the ahtx0 driver
        # devices = self.i2c.scan()
        # 0x39
        # if devices:
            # for d in devices:
                # print(hex(d))

    def get_temperature(self):
        # getting an error from the sensor here OSError: [Errno 5] EIO
        try:
            return "%0.2f" % ((self.sensor.temperature * 1.8 + 32)-2.43)  # offset correction based on average of 4 sensors
        except OSError as err:
            return 00.00

    def get_humidity(self):
        try:
            return "%0.2f" % self.sensor.relative_humidity
        except OSError as err:
            return 00.00


# Start networking
network_manager = NetworkManager()
network_manager.connect_to_network()
sleep(3)
# instantiate aht10 sensor
aht10 = AHT10Sensor()

SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240
CHAR_WIDTH = 8  # Width of each character
CHAR_HEIGHT = 16  # Height of each character
# print(f"small Font width: {smallFont.WIDTH}")
# print(f"small Font height: {smallFont.HEIGHT}")


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


def print_centered_text(text, y):
    text_width = len(text) * CHAR_WIDTH
    x = (SCREEN_WIDTH - text_width) // 2
    tft.text(smallFont, text, x, y, st7789.RED, st7789.BLUE)


def get_current_forecast():
    r = urequests.get("http://api.weatherapi.com/v1/forecast.json?key=1523873bc3d04c4f823185542232405&q=63031&days=1&aqi=no&alerts=yes")
    weather_data = r.json()
    # The plan here is to return only the data that I need rather than keep the entire json stored in memory. This
    # should resolve the memory errors that I was getting when attempting to refresh weather data.
    current_condition = str(weather_data['current']['condition']['text'])
    current_temp = str(weather_data['current']['temp_f'])
    max_temp = weather_data['forecast']['forecastday'][0]['day']['maxtemp_f']
    min_temp = weather_data['forecast']['forecastday'][0]['day']['mintemp_f']
    rain = weather_data['forecast']['forecastday'][0]['day']['daily_chance_of_rain']
    moon_phase = weather_data['forecast']['forecastday'][0]['astro']['moon_phase']
    try:
        alerts = weather_data['alerts']['alert'][0]['headline']
    except Exception as e:
        alerts = str("NO ALERTS CURRENTLY.")
    weather_data = [current_condition, current_temp, max_temp, min_temp, rain, moon_phase, alerts]
    return weather_data


def get_current_date():
    r = urequests.get("http://192.168.1.4:5000/datetime")  # Server that returns the current GMT+0 time.
    date = r.json()["date"]
    return date


def print_wrapped_text(text, start_y, text_color):
    """Function to print text with wrapping. Requires a string and y
        value as arguments."""

    x = 0
    y = start_y

    words = text.split()
    for word in words:
        word_length = len(word)

        if x + word_length * CHAR_HEIGHT >= SCREEN_WIDTH:
            # If the word exceeds the screen width, move to the next line
            x = 0
            y += CHAR_HEIGHT
            if y >= SCREEN_HEIGHT:
                break

        # Determine the remaining space on the current line
        remaining_space = SCREEN_WIDTH - x

        if word_length * CHAR_HEIGHT > remaining_space:
            # The word won't fit on the current line, so move to the next line
            x = 0
            y += CHAR_HEIGHT
            if y >= SCREEN_HEIGHT:
                break

            # Calculate the number of characters that will fit on the new line
            max_chars_on_line = SCREEN_WIDTH // CHAR_HEIGHT

            # Split the word into multiple parts that fit on the line
            parts = [word[i:i + max_chars_on_line] for i in range(0, len(word), max_chars_on_line)]

            # Print the parts on the new line with spaces in between
            for i, part in enumerate(parts):
                tft.text(smallFont, part, x, y + (i * CHAR_HEIGHT), text_color, st7789.BLUE)
                x = 0

            # Update the x and y coordinates for the next word
            x = (len(parts[-1]) * CHAR_WIDTH)
            y += CHAR_HEIGHT

        else:
            # Print the word
            tft.text(smallFont, word, x, y, text_color, st7789.BLUE)

            x += (word_length * CHAR_WIDTH)

            if x >= SCREEN_WIDTH:
                # If the x coordinate exceeds the screen width, move to the next line
                x = 0
                y += CHAR_HEIGHT
                if y >= SCREEN_HEIGHT:
                    break
            # Add spaces if there is enough remaining space
            if x + CHAR_WIDTH <= SCREEN_WIDTH:
                tft.text(smallFont, ' ', x, y, text_color, st7789.BLUE)
                x += CHAR_WIDTH


def print_weather_data(weather_data):
    # condition
    if weather_data[0] == "Sunny":
        tft.fill_rect(0, 65, 160, smallFont.HEIGHT, st7789.BLACK)
        tft.text(smallFont, str(weather_data[0]), 0, 65, st7789.YELLOW, st7789.BLUE)
    elif weather_data[0] == "Clear":
        tft.fill_rect(0, 65, 160, smallFont.HEIGHT, st7789.BLACK)
        tft.text(smallFont, str(weather_data[0]), 0, 65, st7789.WHITE, st7789.BLUE)
    elif weather_data[0] == "Partly cloudy":
        tft.fill_rect(0, 65, 160, smallFont.HEIGHT, st7789.BLACK)
        tft.text(smallFont, str(weather_data[0]), 0, 65, st7789.BLACK, st7789.BLUE)
    else:
        tft.fill_rect(0, 65, 160, smallFont.HEIGHT, st7789.BLACK)
        # slice the general forcast info so that it doesn't overlap more than half the screen.
        tft.text(smallFont, str(weather_data[0])[:155], 0, 65, st7789.GREEN, st7789.BLUE)
    # current temp
    if float(weather_data[1]) >= float(90):
        tft.text(smallFont, f"Current Temp:{weather_data[1]}F", 0, 85,
                 st7789.RED, st7789.BLUE)
    else:
        tft.text(smallFont, f"Current Temp:{weather_data[1]}F  ", 0, 85,
                 st7789.GREEN, st7789.BLUE)
    # max temp
    if float(weather_data[2]) >= float(90):
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
    # tft.fill_rect(0, 185, 320, smallFont.HEIGHT, st7789.BLACK)
    # tft.fill_rect(0, 205, 320, smallFont.HEIGHT, st7789.BLACK)
    tft.fill_rect(0, 185, 320, 55, st7789.BLACK)
    if weather_data[6] == "NO ALERTS CURRENTLY.":
        print_wrapped_text(f"Alert:{weather_data[6]}", 185, st7789.YELLOW)
    else:
        print_wrapped_text(f"Alert:{weather_data[6]}", 185, st7789.RED)


def print_indoor_climate(date, actual_time):
    global last_db_write_time
    temperature = aht10.get_temperature()
    humidity = aht10.get_humidity()
    length = len("Indoor Climate:")
    tft.text(smallFont, "Indoor Climate:", tft.width() - length * smallFont.WIDTH, 65, st7789.GREEN, st7789.BLUE)
    length = len(str(temperature))+1
    tft.text(smallFont, f"{temperature}F", tft.width() - length * smallFont.WIDTH, 85, st7789.GREEN, st7789.BLUE)
    length = len(str(humidity)) + 1
    tft.text(smallFont, f"{humidity}%", tft.width() - length * smallFont.WIDTH, 105, st7789.GREEN, st7789.BLUE)

    current_time = time()
    if current_time - last_db_write_time >= 300:
        data = {
            'date': date,
            'time': actual_time,
            'temperature': temperature,
            'humidity': humidity,
            'location': 'Master Bedroom'
        }
        # log only on even minutes
        # if int(time.split(":")[1]) % 10 == 0:

        try:
            response = urequests.post('http://192.168.1.4:5000/climate', json=data)
            print("Posting indoor climate data.")
            print(response.text)

        except Exception as e:
            print("print_indoor_climate:")
            print(e)
            pass
        last_db_write_time = current_time


last_db_write_time = 0


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
        print("Main first try:")
        print(e)
        pass
    while True:
        if failed_connect == 1:
            tft.fill(st7789.BLACK)
        try:
            failed_connect = 0
            date_time = print_pico_time()
            minute = str(date_time[1]).split(":")[1]
            second = str(date_time[1]).split(":")[2]

        except Exception as e:
            print(e)
            print("Failure at time")
            tft.fill(st7789.BLACK)
            failed_connect = 1
            tft.text(smallFont, "Failed to Reach Time Server.", 0, 0, st7789.GREEN, st7789.BLUE)
            sleep(2)
            continue
        # refresh weather data daily
        if date_time[0] != current_date:
            try:
                current_date = get_current_date()
                weather_data = get_current_forecast()
                print_weather_data(weather_data)
            except Exception as e:
                print(e)
                pass
        # refresh weather data every half hour
        if minute == "59" and int(second) > 58:
            try:
                weather_data = get_current_forecast()
                print_weather_data(weather_data)
            except Exception as e:
                print(e)
                pass
        tft.text(bigFont, date_time[0], 80, 0, st7789.GREEN, st7789.BLUE)
        tft.text(bigFont, date_time[1], 95, 30, st7789.GREEN, st7789.BLUE)
        print_indoor_climate(date_time[0], date_time[1])


main()
