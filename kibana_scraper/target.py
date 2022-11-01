import os
import csv
import pathlib
import pandas as pd
from datetime import datetime
from .records import RecordFactory

import logging
logger = logging.getLogger(__name__)


class Target:
    def initialize_working_folders(self):
        pathlib.Path(self.json_cache).mkdir(parents=True, exist_ok=True)
        pathlib.Path(self.csv_cache).mkdir(parents=True, exist_ok=True)

    def initialize_record_cache(self):
        logger.info("Loading previous results from cache")
        lists = []
        for filename in os.listdir(self.csv_cache):
            file_path = os.path.join(self.csv_cache, filename)
            if os.path.isfile(file_path):
                try:
                    records = pd.read_csv(file_path)
                    lists.append(records)
                except pd.errors.EmptyDataError:
                    # File is empty
                    pass
                
        if len(lists) == 0:
            return None
        else:
            return pd.concat(lists)

    def __init__(self, section, config, model = None):
        self.section = section
        self.config = config
        self.model = model
        self.json_cache = os.path.join("cache", self.section, "json")
        self.csv_cache = os.path.join("cache", self.section, "csv")

        self.initialize_working_folders()
        self.record_cache = self.initialize_record_cache()
        self.new_records = set()
        self.output_path = os.path.join(self.csv_cache, datetime.now().strftime(self.section + "-%Y%m%d-%H%M%S.csv"))

        self.fieldnames = None

    def __enter__(self):
        self.output = open(self.output_path, "w", newline="")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.output.close()

    def parse(self, json):
        if self.model is None:
            return None
        else:
            record = RecordFactory.loads(self.model, json)
            return record

    def seen(self, record_id):
        return record_id in self.new_records or (
                self.record_cache is not None and
                self.record_cache[self.record_cache["User ID"] == record_id].shape[0] > 0
        )

    def store(self, data):
        writer = csv.writer(self.output)
        if self.fieldnames is None:
            self.fieldnames = data.keys()
            writer.writerow(self.fieldnames)

        row = [data[key] for key in self.fieldnames]
        writer.writerow(row)

        self.new_records.add(data["User ID"])

    def store_json(self, text, user_id):
        file_path = os.path.join(self.json_cache, user_id + ".json")
        with open(file_path, "wt", newline="") as f:
            f.write(text)


        