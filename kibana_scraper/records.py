import json

import logging
logger = logging.getLogger(__name__)


def get(data, key, default=None):
    """Finds given key in the data"""

    try:
        if "." in key:
            # descending in the data structure
            head, rest = key.split(".", 1)
            node = get(data, head)
            if node is None:
                return default
            else:
                return get(node, rest, default)
        else:
            if type(data) is list:
                index = int(key)
                if len(data) > index:
                    return data[index]
                else:
                    return default
            elif type(data) is dict:
                return data.get(key, default)
            else:
                raise TypeError()
    except:
        return default


def parse_sex(sex):
    if sex is None:
        return None

    _sex = str(sex).strip().lower()

    if _sex in ["male"]:
        return "M"
    elif _sex in ["female"]:
        return "F"
    else:
        return sex


def parse_is_smoker(is_smoker):
    if is_smoker is None:
        return None
    elif type(is_smoker) is bool:
        return 1 if is_smoker else 0
    elif is_smoker == "NonSmoker":
        return 0
    elif is_smoker == "UnKnown":
        return None
    else:
        return None


def parse_diabetic(diabetic):
    return 1 if diabetic else 0


class BaseRecord:
    """Abstract class for records"""

    getters = {}
    measures_calculation_failed = False
    measures = None

    def __init__(self, data, model):
        self.data = data
        self.model = model

        self.getters["User ID"] = lambda: get(self.data, "_id")
        self.getters["Age"] = lambda: get(self.data, "_source.profile.age", None)
        self.getters["Height"] = lambda: get(self.data, "_source.profile.height", None)
        self.getters["Weight"] = lambda: get(self.data, "_source.profile.weight", None)
        self.getters["Waist"] = lambda: get(self.data, "_source.profile.waist", None)
        self.getters["Status"] = lambda: get(self.data, "_source.status", None)
        self.getters["Sex"] = lambda: parse_sex(get(self.data, "_source.profile.sex", None))
        self.getters["Diabetes Type"] = lambda: get(self.data, "_source.profile.diabeticType", None)
        self.getters["Ethnicity"] = lambda: get(self.data, "_source.profile.enhnicity", None)
        self.getters["HbAc1"] = lambda: get(self.data, "_source.profile.hbA1C", None)

        self.getters["bpm"] = lambda: get(self.get_measures(), "bpm", None)
        self.getters["ibi"] = lambda: get(self.get_measures(), "ibi", None)
        self.getters["sdnn"] = lambda: get(self.get_measures(), "sdnn", None)
        self.getters["sdsd"] = lambda: get(self.get_measures(), "sdsd", None)
        self.getters["rmssd"] = lambda: get(self.get_measures(), "rmssd", None)
        self.getters["pnn20"] = lambda: get(self.get_measures(), "pnn20", None)
        self.getters["pnn50"] = lambda: get(self.get_measures(), "pnn50", None)
        self.getters["hr_mad"] = lambda: get(self.get_measures(), "hr_mad", None)
        self.getters["sd1"] = lambda: get(self.get_measures(), "sd1", None)
        self.getters["sd2"] = lambda: get(self.get_measures(), "sd2", None)
        self.getters["s"] = lambda: get(self.get_measures(), "s", None)
        self.getters["sd1/sd2"] = lambda: get(self.get_measures(), "sd1/sd2", None)
        self.getters["breathingrate"] = lambda: get(self.get_measures(), "breathingrate", None)
        self.getters["lf"] = lambda: get(self.get_measures(), "lf", None)
        self.getters["hf"] = lambda: get(self.get_measures(), "hf", None)
        self.getters["lf/hf"] = lambda: get(self.get_measures(), "lf/hf", None)

    def __getitem__(self, key):
        if key in self.getters:
            return self.getters[key]()
        else:
            raise RuntimeError(f"No getter defined for key: {key}")

    def __contains__(self, key):
        return key in self.getters

    def keys(self):
        return self.getters.keys()

    def get_measures(self):
        if self.measures is not None:
            return self.measures
        else:
            if self.measures_calculation_failed:
                return None
            else:
                self.calculate_measures()
                return self.measures

    def calculate_measures(self):
        time = self.data["_ppg"]["time"]
        amplitude = self.data["_ppg"]["amplitude"]

        try:
            model = self.model(time, amplitude)
            working_data, self.measures = model.get_measures()
        except Exception as e:
            logger.warn(str(e))
            self.measures_calculation_failed = True


class ResearchV2Record(BaseRecord):
    def __init__(self, data, model):
        super().__init__(data, model)
        self.getters["User Key"] = lambda: get(self.data, "_source.userkey", "").upper()
        self.getters["Trial Name"] = lambda: None
        self.getters["Diabetic"] = lambda: parse_diabetic(get(self.data, "_source.profile.diabetesDiagnosis", None))
        self.getters["IsSmoker"] = lambda: parse_is_smoker(get(self.data, "_source.profile.smokingStatus", None))
        self.getters["DeviceModel"] = lambda: get(self.data, "_source.device.model", None)
        self.getters["DeviceMake"] = lambda: get(self.data, "_source.device.make", None)
        self.getters["Timestamp"] = lambda: get(self.data, "fields.timestamp.0", None)

        self.data["_ppg"] = {}
        self.data["_ppg"]["time"] = get(self.data, "_source.data.ppg.x", [])
        self.data["_ppg"]["amplitude"] = get(self.data, "_source.data.ppg.y", [])


class RndHistoricalRecord(BaseRecord):
    def __init__(self, data, model):
        super().__init__(data, model)
        self.getters["User Key"] = lambda: get(self.data, "_source.userkey", "").upper()
        self.getters["Trial Name"] = lambda: get(self.data, "_source.tags.0", None)
        self.getters["Diabetic"] = lambda: parse_diabetic(get(self.data, "_source.profile.diabetic", None))
        self.getters["IsSmoker"] = lambda: parse_is_smoker(get(self.data, "_source.profile.smoker", None))
        self.getters["DeviceModel"] = lambda: get(self.data, "_source.device.model", None)
        self.getters["DeviceMake"] = lambda: get(self.data, "_source.device.make", None)
        self.getters["Timestamp"] = lambda: get(self.data, "fields.timestamp.0", None)

        self.data["_ppg"] = {}
        self.data["_ppg"]["time"] = get(self.data, "_source.data.ppg.x", [])
        self.data["_ppg"]["amplitude"] = get(self.data, "_source.data.ppg.y", [])


class SignalsRecord(BaseRecord):
    def __init__(self, data, model):
        super().__init__(data, model)
        self.getters["User Key"] = lambda: get(self.data, "_source.accountId", "").upper()
        self.getters["Trial Name"] = lambda: None
        self.getters["Diabetic"] = lambda: parse_diabetic(get(self.data, "_source.profile.diabetesDiagnosis", None))
        self.getters["IsSmoker"] = lambda: parse_is_smoker(get(self.data, "_source.profile.smokingStatus", None))
        self.getters["DeviceModel"] = lambda: get(self.data, "_source.source.model", None)
        self.getters["DeviceMake"] = lambda: get(self.data, "_source.source.make", None)
        self.getters["Timestamp"] = lambda: get(self.data, "fields.createdOn.0", None)

        self.data["_ppg"] = {}
        self.data["_ppg"]["time"] = get(self.data, "_source.channels.0.time", [])
        self.data["_ppg"]["amplitude"] = get(self.data, "_source.channels.0.amplitude", [])


class RecordFactory:
    @staticmethod
    def get_class(data):
        index = data.get("_index", None)
        if index == "signals":
            return SignalsRecord
        elif index == "research-v2":
            return ResearchV2Record
        elif index == "rnd-historical":
            return RndHistoricalRecord
        else:
            raise ValueError("_index value not supported: " + str(index))

    @staticmethod
    def load(model, *args, **kwargs):
        """Loads the data from a file pointer and returns a Record instance. All parameters passed to json.load"""
        data = json.load(*args, **kwargs)
        cls = RecordFactory.get_class(data)

        return cls(data, model)

    @staticmethod
    def loads(model, *args, **kwargs):
        """Loads the data from a string and returns a Record instance. All parameters passed to json.loads"""
        data = json.loads(*args, **kwargs)
        cls = RecordFactory.get_class(data)

        return cls(data, model)
