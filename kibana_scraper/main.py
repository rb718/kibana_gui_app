from .config import config
from .robot import Robot
from .target import Target
from .models import HPModel as Model
from .signals import signals

import pandas as pd
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

log_file_name = datetime.now().strftime("%Y%m%d-%H%M%S.log")

logging.basicConfig(level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s')


def scrape(username, password):
    done = set()
    while True:
        with Robot(username, password) as robot:
            for section in config.sections():
                if signals.stop:
                    print("Good bye!")
                    return

                if section in done:
                    continue
                    
                enabled = config[section].getboolean("enabled", True)

                if enabled:
                    print("Target:", section)
                    with Target(section, config[section], Model) as target:
                        try:
                            robot.go(target)
                            done.add(section)
                            
                        except Exception as robot_exception:
                            logger.critical(robot_exception, exc_info=True)
                            try:
                                robot.screenshot()
                            except Exception as screenshot_exception:
                                logger.critical("Failed to save screenshot. Geckodriver is possibly crashed.")
                            
                            continue
                else:
                    print(f"Section {section} is disabled. Skipping.")
                    done.add(section)
                    
            return


def export(file_path):
    cache = []
    for section in config.sections():
        enabled = config[section].getboolean("enabled", True)

        if enabled:
            target = Target(section, config[section])
            if target.record_cache is not None:
                section_results = target.record_cache.assign(**{"_index(Search type)":section})
                cache.append(section_results)
            
    df = pd.concat(cache)
    df.sort_values(["Timestamp"], inplace=True)
    
    df.to_csv(file_path, index=False)
    
