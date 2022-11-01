import pandas as pd
from statsmodels.tsa.seasonal import STL
import heartpy as hp
from scipy.signal import resample
from .config import config


import logging
logger = logging.getLogger(__name__)

import warnings
warnings.filterwarnings('ignore')

class BaseModel:
    def __init__(self, time, amplitude):
        self.time = pd.to_timedelta(time, unit='seconds')
        self.amplitude = amplitude
        self.df = pd.DataFrame(list(zip(self.time, self.amplitude)))
        self.df.columns = ["time", "amplitude"]
        self.df.set_index("time", inplace=True)

    def get_sample_rate(self):
        """Calculates sample rate"""
        sample_rate = hp.get_samplerate_mstimer(self.time.total_seconds() * 1000)
        return sample_rate


class STLNormalizationModel(BaseModel):
    def _get_period_score(self, period):
        result = STL(self.df.amplitude, period=period).fit()
        try:
            working_data, measures = hp.process((result.resid + result.seasonal + result.weights).to_numpy(),
                                                self.get_sample_rate(), calc_freq=True)
            return len(working_data["binary_peaklist"]), sum(working_data["binary_peaklist"])
        except:
            return None, None

    def _get_best_period(self):
        """Finds the period with the best accepted/rejected peak ratio"""
        results = []
        for i in range(20, 60):
            l, s = self._get_period_score(i)
            if l is not None:
                results.append((i, l, s))

        x = [r[0] for r in results]
        y = [(r[1] / (r[1] - r[2])) for r in results]

        best_score = max(y)
        best_score_index = y.index(best_score)
        best_period = x[best_score_index]

        return best_period

    def get_measures(self):
        """Calculates measures using HeartPy"""
        
        if not config["DEFAULT"].getboolean("calculate_measures", True):
            return None, None
            
        sample_rate = self.get_sample_rate()
        best_period = self._get_best_period()

        result = STL(self.df.amplitude, period=best_period).fit()
        return hp.process((result.resid + result.seasonal + result.weights).to_numpy(), sample_rate,
                          calc_freq=True)


class HPModel(BaseModel):
    def process(self, sample_rate):
        data = self.df.amplitude.to_numpy()

        data = hp.filter_signal(data, [0.6, 3.6], sample_rate, order=3, filtertype='bandpass')

        data = hp.smooth_signal(data, sample_rate, window_length=15)

        sample_ratio = (100/sample_rate)+1
        data = resample(data, len(data) * 1)
        sample_rate = sample_rate * 1
        
        return hp.process(data, sample_rate,
                          calc_freq=True, clean_rr=True)
        
    def get_measures(self):
        """Calculates measures using HeartPy"""
        
        sample_rate = self.get_sample_rate()
        return self.process(sample_rate)
