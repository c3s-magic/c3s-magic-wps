from .wps_sleep import Sleep
from .wps_python_example import PythonExample
from .wps_consecdrydays import ConsecDryDays
from .wps_perfmetrics import Perfmetrics
from .wps_rainfarm import RainFarm
from .wps_rmse import RMSE

#Disabled for now
# MyDiag(),
# Perfmetrics(),

processes = [
    Sleep(),
    PythonExample(),
    ConsecDryDays(),
    RainFarm(),
    RMSE(),
]
