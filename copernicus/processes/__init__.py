from .wps_sleep import Sleep
from .wps_mydiag import MyDiag
from .wps_pydemo import PyDemo
from .wps_perfmetrics import Perfmetrics
from .wps_rainfarm import RainFarm
from .wps_rmse import RMSE

processes = [
    Sleep(),
    MyDiag(),
    PyDemo(),
    Perfmetrics(),
    RainFarm(),
    RMSE(),
]
