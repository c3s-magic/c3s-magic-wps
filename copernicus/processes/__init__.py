from .wps_sleep import Sleep
from .wps_preproc_example import PreprocessExample
from .wps_consecdrydays import ConsecDryDays
from .wps_cvdp import CVDP
from .wps_ensclus import EnsClus
from .wps_shapeselect import ShapeSelect
from .wps_perfmetrics import Perfmetrics
from .wps_rainfarm import RainFarm
from .wps_rmse import RMSE
from .wps_blocking import Blocking
from .wps_stratosphere_troposphere import StratosphereTroposphere
from .wps_annularmodes import AnnularModes
from .wps_teleconnections import Teleconnections
from .wps_weather_regimes import WeatherRegimes


#Disabled for now
# MyDiag(),
# RainFarm(),
# RMSE(),
# ConsecDryDays(),
# ShapeSelect(),
# Perfmetrics(),

processes = [
    CVDP(),
    EnsClus(),
    Sleep(),
    Blocking(),
    PreprocessExample(),
    StratosphereTroposphere(),
    AnnularModes(),
    Teleconnections(),
    WeatherRegimes(),
]
