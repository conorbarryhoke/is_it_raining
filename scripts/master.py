import os, sys
cwd = os.getcwd()
sys.path.append(cwd)
from importlib import import_module
import_module("run_twitter")
import_module("run_weather")
import run_twitter
import run_weather


from time import sleep
import datetime


def run_main():
    hour_counter = 0
    while hour_counter < 24*7*8:
        run_weather.run_main()
        if hour_counter % 24 == 0:
            run_twitter.run_main()

        hour_counter+=1    

        sleep(60*60)



if __name__ = "__main__":
    run_main()


