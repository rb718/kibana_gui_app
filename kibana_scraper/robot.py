"""
kibana_export/robot.py

Implements the scraping functionality of the package

Exports the Robot class, which has only one public method:

Robot.go(target)
"""
import os
import json
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import TimeoutException
from time import sleep
from datetime import datetime, timezone
from urllib.parse import urlparse

import logging
logger = logging.getLogger(__name__)

from .config import config
from .signals import signals

SHORT_WAIT = config["DEFAULT"].getint("short_wait", 5)
MEDIUM_WAIT = config["DEFAULT"].getint("medium_wait", 30)
LONG_WAIT = config["DEFAULT"].getint("long_wait", 60)

class Robot:
    def __init__(self, username, password):
        firefox_profile = config["DEFAULT"].get("firefox_profile", None)
        self.username = username
        self.password = password
        
        options = Options()
        service_args = []
        
        # use profile only if specified
        if firefox_profile is not None:
            options.add_argument("-profile")
            options.add_argument(firefox_profile)
            # explicit marionette port, so we can connect to the instance
            service_args.append("--marionette-port")
            service_args.append("2828")
            
        self.driver = webdriver.Firefox(options=options, service_args=service_args)
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if config["DEFAULT"].getboolean("auto_close_browser", True):
            self.driver.quit()
     
    # Page layout:
    #
    # @ date-filter-modal -> end-date-input
    #
    #   
    # discover-app
    #    + kbn-top-nav
    #        + date-filter
    #            + end-date button
    #            + update button
    #    + main
    #        + doc-table
    #           + summary_row
    #           + document_row
    #           + summary_row
    #           + document_row
    #           + ... # Rows are dynamically added when the page is scorred to its bottom
    #        + footer
    
    # Functions to access relevant nodes on the page
    
    def get_discover_app(self):
        wait = WebDriverWait(self.driver, LONG_WAIT)
        return wait.until(EC.presence_of_element_located((By.XPATH, "//discover-app")))
        
    def get_dsc_table(self):
        wait = WebDriverWait(self.get_discover_app(), LONG_WAIT)
        return wait.until(EC.presence_of_element_located((By.XPATH, "./main//section[contains(@class, 'dscTable')]")))
            
    def get_doc_table(self):
        try:
            wait = WebDriverWait(self.get_dsc_table(), LONG_WAIT)
            return wait.until(EC.presence_of_element_located((By.XPATH, "./doc-table//table/tbody")))
        except:
            return None
        
    def get_footer(self):
        try:
            wait = WebDriverWait(self.get_dsc_table(), SHORT_WAIT)
            return wait.until(EC.presence_of_element_located((By.XPATH, "./div[contains(@class, 'dscTable__footer')]/span")))
        except TimeoutException:
            return None
            
    def get_date_filter(self):
        wait = WebDriverWait(self.get_discover_app(), SHORT_WAIT)
        return wait.until(EC.presence_of_element_located((By.XPATH, ".//kbn-top-nav-helper//div[contains(@class, 'globalQueryBar')]//div/div[contains(@class, 'kbnQueryBar__datePickerWrapper')]/..")))

    def get_absolute_button(self):
        wait = WebDriverWait(self.driver, SHORT_WAIT)
        return wait.until(EC.presence_of_element_located((By.XPATH, "//button[@id='absolute']")))
        
    def get_end_date_button(self):
        wait = WebDriverWait(self.get_date_filter(), SHORT_WAIT)
        return wait.until(EC.presence_of_element_located((By.XPATH, ".//button[contains(@class, 'euiDatePopoverButton--end')]")))

    def get_update_button(self):
        wait = WebDriverWait(self.get_date_filter(), SHORT_WAIT)
        return wait.until(EC.presence_of_element_located((By.XPATH, ".//button[@data-test-subj='querySubmitButton']")))
    
    def get_date_popover(self):
        wait = WebDriverWait(self.driver, SHORT_WAIT)
        return wait.until(EC.presence_of_element_located((By.XPATH, ".//div[@class='euiDatePopoverContent']")))
        
    def get_end_time_input(self):
        wait = WebDriverWait(self.driver, SHORT_WAIT)
        return wait.until(EC.presence_of_element_located((By.XPATH, ".//input[@data-test-subj='superDatePickerAbsoluteDateInput']")))
            
    def get_infinite_scroller(self):
        wait = WebDriverWait(self.get_dsc_table(), SHORT_WAIT)
        return wait.until(EC.presence_of_element_located((By.XPATH, './doc-table//kbn-infinite-scroll')))

    def get_user_id(self, row):
        """Returns User ID from a summary_row"""
        try:
            return row.find_element_by_xpath("./td[3]//dl/dt[text()='id:']/following-sibling::dd/span").text
        except:
            # Element not found
            return None
    
    def get_timestamp(self, row):
        wait = WebDriverWait(row, SHORT_WAIT)
        return wait.until(EC.presence_of_element_located((By.XPATH, "./td[2]/span[1]"))).text

    def get_no_results_warnig(self):
        try:
            wait = WebDriverWait(self.get_discover_app(), SHORT_WAIT)
            return wait.until(EC.visibility_of_element_located((By.XPATH, ".//discover-no-results")))
        except:
            return None
        
    
    def get_login_form(self):
        wait = WebDriverWait(self.driver, LONG_WAIT)
        return wait.until(EC.presence_of_element_located((By.XPATH, ".//div[contains(@class, 'login-form')]//form")))
    
    def get_username_field(self):
        wait = WebDriverWait(self.get_login_form(), SHORT_WAIT)
        return wait.until(EC.presence_of_element_located((By.XPATH, ".//input[@name='username']")))
        
    def get_password_field(self):
        wait = WebDriverWait(self.get_login_form(), SHORT_WAIT)
        return wait.until(EC.presence_of_element_located((By.XPATH, ".//input[@name='password']")))
    
    def get_login_button(self):
        wait = WebDriverWait(self.get_login_form(), SHORT_WAIT)
        return wait.until(EC.presence_of_element_located((By.XPATH, ".//button[@type='submit']")))
    
    def get_login_error_message(self):
        try:
            wait = WebDriverWait(self.driver, SHORT_WAIT)
            return wait.until(EC.presence_of_element_located((By.XPATH, "//div[@data-test-subj='loginErrorMessage']")))
        except:
            return None
        
    def get_page_failed_to_load_warning(self):
        try:
            wait = WebDriverWait(self.driver, SHORT_WAIT)
            return wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/h1[contains(text(), 'did not load properly')]")))
        except:
            return None
    
    # Convenience functions
    
    def await_table_to_be_populated(self):
        """Awaits table to be present and have at least one row"""
        wait = WebDriverWait(self.get_doc_table(), LONG_WAIT)
        wait.until(EC.presence_of_element_located((By.XPATH, './tr[1]/td[1]')))
        
    def get_row_at_index(self, index):
        try:
            wait = WebDriverWait(self.get_doc_table(), SHORT_WAIT)
            return wait.until(EC.presence_of_element_located((By.XPATH, f'./tr[{index}]')))
        except:
            return None
            
    
    def click(self, element):
        """Clicks on an element, if fails, tries again using javascript"""
        try:
            wait = WebDriverWait(element, MEDIUM_WAIT)
            wait.until(EC.element_to_be_clickable((By.XPATH, ".")))
            element.click()
        except:
        #except ElementClickInterceptedException:
            sleep(1)
            self.driver.execute_script("arguments[0].click();", element)
        
    def extract_document(self, row):
        """Extracts JSON data from under a row"""
        
        # Expand details
        arrow = WebDriverWait(row, SHORT_WAIT).until(EC.element_to_be_clickable((By.XPATH, './td[1]')))
        self.click(arrow)
                
        # Select JSON format
        json_label = WebDriverWait(self.driver, MEDIUM_WAIT).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="JSON"]')))
        self.click(json_label)
        
        document_node = WebDriverWait(row, MEDIUM_WAIT).until(EC.presence_of_element_located((By.XPATH,'./following-sibling::tr//doc-viewer//code')))
                
        text = document_node.get_attribute("innerText")
        
        # Close details
        arrow = WebDriverWait(row, SHORT_WAIT).until(EC.element_to_be_clickable((By.XPATH, './td[1]')))
        self.click(arrow)

        return text

    def store_record(self, target, record, document, user_id):
        """Takes a string, containing a json document, and sores it using the given target"""
        
        target.store(record)
        if config["DEFAULT"].getboolean("save_json_files", False):
            target.store_json(document, user_id)

    def process_table(self, target):
        table = self.get_doc_table()

        logger.info("Waiting for data to be loaded on the page")
        self.load_all_elements()
        
        if config["DEFAULT"].getboolean("fast_scan", False):
            logger.info("fast_scan mode")
            return
                
        for index in range(1, self.count_rows()+1, 2):
            if signals.stop:
                return

            row = self.get_row_at_index(index)
            
            # End of table reached
            if row is None:
                break
                
            # The table contains two rows per element: One for the summary and one for the document
            # So we advance two rows at a time
            index += 2
            
            user_id = self.get_user_id(row)
            
            if user_id is None:
                # Id is not available in the summary
                document = self.extract_document(row)
                record = target.parse(document)
                user_id = record["User ID"]
                
                if target.seen(user_id):
                        logger.info("Already in cache: %s", user_id)
                        continue
            else:
                if target.seen(user_id):
                        logger.info("Already in cache: %s", user_id)
                        continue
            
                document = self.extract_document(row)
                record = target.parse(document)
            
            self.store_record(target, record, document, user_id)
            logger.info("Stored: %s", user_id)

    def count_rows(self):
        return len(self.get_doc_table().find_elements_by_xpath("./tr"))
        
    def load_all_elements(self, timeout=SHORT_WAIT):
        """Triggers infinite scolling until all elements are loaded"""
        def new_rows_are_loaded(row_count):
            for i in range(timeout):
                sleep(1)
                if row_count != self.count_rows():
                    return True
            return False
        
        while True:
            if signals.stop:
                return

            row_count = self.count_rows()
            
            # Scroll infite_scoller into view
            infinite_scroller = self.get_infinite_scroller()
            self.driver.execute_script("arguments[0].scrollIntoView(true);", infinite_scroller);
            
            # If no new elements are loaded, return
            if not new_rows_are_loaded(row_count):
                return
            
    def query_has_more_elements(self):
        """Return true if footer exists on page"""
        return self.get_footer() is not None
    
    def get_last_displayed_elements_timestamp(self):
        row_count = self.count_rows()
        last_summary_row_index = row_count-1
        last_summary_row = self.get_row_at_index(last_summary_row_index)
        
        timestamp = self.get_timestamp(last_summary_row)
        
        return timestamp
        
    def update_search(self, url):
        logger.info("Loading next page")
        timestamp = self.get_last_displayed_elements_timestamp()
        
        self.navigate(self.build_search_url(url, timestamp))
        
    def build_search_url(self, original_url, timestamp=None):
        params = {}
        
        if timestamp is None:
            params["to_time_utc"] = config["DEFAULT"].get("to_time_utc", "now")
        else:
            to_time = datetime.strptime(timestamp, "%b %d, %Y @ %H:%M:%S.%f")
            params["to_time_utc"] = "'" + to_time.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z'"
        
        params["from_time_utc"] = config["DEFAULT"].get("from_time_utc", "'2016-12-29T09:57:28.503Z'")
        
        return original_url.format(**params)
        
    def navigate(self, url):
        logger.info("Opening URL: %s", url)
        self.driver.get("about:blank")
        self.driver.get(url)

    def screenshot(self, robot):
        screenshots_path = os.path.abspath(config["DEFAULT"].get("screenshots.path", "."))

        try:
            os.makedirs(screenshots_path)
        except FileExistsError:
            pass

        screenshot_file_name = datetime.now().strftime("screenshot_%Y%m%d_%H%M%S_%f.png")
        screenshot_path = os.path.join(screenshots_path, screenshot_file_name)

        self.driver.save_screenshot(screenshot_path)

    def go(self, target):
        """Process the site at: target.config.url"""
        url = target.config.get("url", None)
        if url is None:
            raise ValueError("URL is not set for section: " + target.section)
        
        self.navigate(self.build_search_url(url))
        
        if self.login_required():
            logger.info("Login required")
            self.attempt_login()
            if self.login_required():
                logger.info("Cannot Continue")
                return
                
        while True:
            if self.get_doc_table() is not None:
                # Table is available on the page. Should I log this?
                pass
            elif self.get_no_results_warnig() is not None:
                logger.info("No more elements to parse")
                return
            elif self.get_page_failed_to_load_warning() is not None:
                logger.info("Page failed to load. Trying again.")
                self.driver.refresh()
                continue
            else:
                raise TimeoutException("No table or warning message appeared")

            self.await_table_to_be_populated()
            
            self.process_table(target)
            
            if signals.stop:
                return
                
            if self.query_has_more_elements():
                self.update_search(url)
            else:
                return
            
    def login_required(self):
        url = urlparse(self.driver.current_url)
        print(url.path)
        
        return url.path == "/login"
        
    def credentials_available(self):
        if self.username is None or self.username == "":
            return False
        elif self.password is None or self.password == "":
            return False
        else:
            return True
    
    def attempt_login(self):
        if not self.credentials_available():
            logger.warn("Missing credentials.")
            return
            
        self.get_username_field().send_keys(self.username)
        self.get_password_field().send_keys(self.password)
        self.click(self.get_login_button())
        sleep(1)
        login_error_message = self.get_login_error_message()
        
        if login_error_message is not None:
            logger.warn(login_error_message.text)
            