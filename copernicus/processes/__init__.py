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
from .wps_zmnam import ZMNAM
from .wps_teleconnections import Teleconnections
from .wps_weather_regimes import WeatherRegimes
from .wps_modes_variability import ModesVariability


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
    ZMNAM(),
    Teleconnections(),
    WeatherRegimes(),
    ModesVariability()
]
