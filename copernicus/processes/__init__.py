from .wps_sleep import Sleep
from .wps_python_example import PythonExample
from .wps_consecdrydays import ConsecDryDays
from .wps_cvdp import CVDP
from .wps_ensclus import EnsClus
from .wps_shapeselect import ShapeSelect
from .wps_perfmetrics import Perfmetrics
from .wps_rainfarm import RainFarm
from .wps_rmse import RMSE
from .wps_blocking import Blocking
from .wps_stratosphere_troposphere import StratosphereTroposphere

#Disabled for now
# MyDiag(),
# 
# ConsecDryDays(),

processes = [
    Sleep(),
    PythonExample(),
    CVDP(),
    EnsClus(),
    ShapeSelect(),
    Perfmetrics(),
    Blocking(),
    StratosphereTroposphere(),
]
