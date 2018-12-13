from .wps_sleep import Sleep
from .wps_python_example import PythonExample
from .wps_consecdrydays import ConsecDryDays
from .wps_cvdp import CVDP
from .wps_ensclus import EnsClus
from .wps_shapeselect import ShapeSelect
from .wps_zmnam import ZonalMeanNAM
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
    CVDP(),
    EnsClus(),
    ShapeSelect(),
    ZonalMeanNAM(),
]
