
# Kibana Gui App

Kibana scraper is made to automate the exporting of JSON data from the web-based Kibana application.

## Requirements
Kibana Scraper was built and tested on Python3.8, and depends on the following libraries, and all of their dependencies:
  * heartpy==1.2.6
  * selenium==3.141.0
  * statsmodels==0.11.1

It's tested on Windows 10 but should work just as well on Linux too.

## Installation

Extract or download the source code into an arbitrary folder (e.g. c:\kibana_scraper) and open a console in this folder!

Create virtual environment for the application, then activate it
```
c:\kibana_scraper> python -m venv venv
c:\kibana_scraper> venv\Scripts\activate.bat
(venv) c:\kibana_scraper>
```

Install dependencies
```
(venv) c:\kibana_scraper> pip install -r requirements.txt
```
## Run
Kibana Scraper can be executed with a GUI which could be used to control the scraper and extract the downloaded data. It can also be started as a command-line application, in which case act as a simple scraper.

You can start the GUI from within an activated virtual environment
```
(venv) c:\kibana_scraper> python -m kibana_scraper.gui
```
or calling the venv's python executable directly
```
c:\kibana_scraper> venv\Scripts\python.exe -m kibana_scraper.gui
```
Similarly, for the command line scraper
```
(venv) c:\kibana_scraper> python -m kibana_scraper
```
or
```
c:\kibana_scraper> venv\Scripts\python.exe -m kibana_scraper
```

Credentials can be supplied to the command line interface with the following options:

```
Options:
  -h, --help            show this help message and exit
  -u USERNAME, --username=USERNAME
                        Username to be used if login is required
  -p PASSWORD, --password=PASSWORD
                        Password to be used if login is required
```

## Configuration
The script reads its configuration from the _kibana_scraper.ini_ file, which should be available in the current working directory. 
It should contain one 'DEFAULT' section and one section for each target.
The 'DEFAULT' section contains options for the entire application, while the target sections define one query to be scraped each.

For a detailed description, see the template _kibana_scraper.ini_ file, included in the package.

If you would like to reuse an existing login session from the specified Firefox profile.
You can find the correct value for the _firefox_profile_ setting under the **Firefox menu -> Help ->Troubleshooting information -> Profile Directory**

## Script behavior
### Scraping
The scraper procedure iterates over the configured and enabled targets, and executes the following steps:
1. Load all cached CSV files from previous executions and initialize the output file for the current execution
2. Construct url using the _url_, _from_time_utc_ and _to_time_utc_
3. Open constructed URL
4. If login the page appears, attempt to log in. If the login is successful, continue at step 5., otherwise, go to step 10.
5. The web page should display either a table of results. If the table appears, continue at step 6.

6. The web page uses infinite scrolling, which means it dynamically loads new data when the user scrolls to the bottom of the page. But no more than 500 elements can be displayed a time. So the robot first attempts to make the page load as many records as it can:
  6.1. Enumerate displayed records
  6.2. Scroll to the bottom of page
  6.3. Wait. If no new items appear, continue at step 7. Otherwise, repeat from step 6.1
7. For each row
  7.1 Check if **_id** is available in the cache. If yes. continue on next row
  7.2 Click the down-arrow on the current row to open the document details
  7.3 Click on the JSON label to switch to JSON view
  7.4 If the [calculate_measures] option is enabled, compute heart rate measures. Write the record into the output file. 
  7.5 Click the up-arrow on the current row to close the document details
8. Check if the footer node is present (which indicates that there are more 500 results in the query). If not, continue at step 10.
9. The footer is present, so we need to repeat the step with narrower search criteria: using the timestamp of the last displayed element, construct a new URL with updated _to_time_utc_, and continue with step 3.
10. Finish: close the output file, and move to the next target

When all the enabled targets are processed, the scrapers running is finished.

### Exporting the data
The script creates new CSV output files for each target at each runs. The export procedure loads all these files from the cache folder and merges them, and for each row, it adds the target name. Then, the rows are sorted by timestamp and saved into a CSV file at the path supplied by the user.

## Appendix A, parsing the JSON data
Currently, the script supports three JSON layouts. They have common fields, and some are different for each of them. Additionally, the ppg measures computed with HeartPy are added to the final record.

### Common fields

| Field | Origin | Source node | Transformation|
|---|---|---|---| 
| User ID | json | _id | | 
| Age | json | _source.profile.age | | 
| Height | json | _source.profile.height | | 
| Weight | json | _source.profile.weight | | 
| Waist | json | _source.profile.waist | | 
| Status | json | _source.status | | 
| Sex | json | _source.profile.sex | “M” if “Male”, “F” if “female”, “” otherwise |
| Diabetes Type | json | _source.profile.diabeticType | | 
| Ethnicity | json | _source.profile.enhnicity | | 
| HbAc1 | json | _source.profile.hbA1C | | 
| bpm | Computed by hearpy | bpm | | 
| ibi | Computed by hearpy | ibi | | 
| sdnn | Computed by hearpy | sdnn | | 
| sdsd | Computed by hearpy | sdsd | | 
| rmssd | Computed by hearpy | rmssd | | 
| pnn20 | Computed by hearpy | pnn20 | | 
| pnn50 | Computed by hearpy | pnn50 | | 
| hr_mad | Computed by hearpy | hr_mad | | 
| sd1 | Computed by hearpy | sd1 | | 
| sd2 | Computed by hearpy | sd2 | | 
| s | Computed by hearpy | s | | 
| sd1/sd2 | Computed by hearpy | sd1/sd2 | | 
| breathingrate | Computed by hearpy | breathingrate | | 
| lf | Computed by hearpy | lf | | 
| hf | Computed by hearpy | hf | | 
| lf/hf | Computed by hearpy | lf/hf | | 
| _index(Search type) | Computed at export time |  | | 

### research-v2 layout
| Field | Origin | Source node | Transformation|
|---|---|---|---|
| User Key | json | _source.userkey | uppercase |
| Trial Name | json |  | “”, Not available in this layout |
| Diabetic | json | _source.profile.diabetesDiagnosis | 1 if True, 0 if False, “” otherwise |
| IsSmoker | json | _source.profile.smokingStatus | 0 if “NonSmoker” of False, 1 if “Smoker” or True, “” otherwise  |
| DeviceModel | json | _source.device.model |  |
| DeviceMake | json | _source.device.make |  |
| Timestamp | json | fields.timestamp.0 |  |

### rnd-historical layout
| Field | Origin | Source node | Transformation|
|---|---|---|---|
| User Key | json | _source.userkey | uppercase |
| Trial Name | json | _source.tags.0 |  |
| Diabetic | json | _source.profile.diabetic | 1 if True, 0 if False, “” otherwise |
| IsSmoker | json | _source.profile.smoker | 0 if “NonSmoker” of False, 1 if “Smoker” or True, “” otherwise  |
| DeviceModel | json | _source.device.model |  |
| DeviceMake | json | _source.device.make |  |
| Timestamp | json | fields.timestamp.0 |  |

### signals layout
| Field | Origin | Source node | Transformation|
|---|---|---|---|
| User Key | json | _source.accountId | uppercase |
| Trial Name | json |  | “”, Not available in this layout |
| Diabetic | json | _source.profile.diabetesDiagnosis | 1 if True, 0 if False, “” otherwise |
| IsSmoker | json | _source.profile.smokingStatus | 0 if “NonSmoker” of False, 1 if “Smoker” or True, “” otherwise  |
| DeviceModel | json | _source.source.model |  |
| DeviceMake | json | _source.source.make |  |
| Timestamp | json | fields.createdOn.0 |  |

# kibana_gui_app
