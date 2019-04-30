import os

from pywps import Service
from pywps.tests import assert_response_success

from . common import client_for
from c3s_magic_wps.processes.wps_blocking import Blocking


def test_wps_blocking():
    client = client_for(Service(processes=[Blocking()], cfgfiles=[".custom.cfg"]))
    resp = client.get(
        service='WPS', request='Execute', version='1.0.0', identifier='blocking')
    print(resp.data)
    assert_response_success(resp)
