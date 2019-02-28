from pywps import Service
from pywps.tests import assert_response_success

from .common import client_for
from copernicus.processes import processes


def test_wps_caps():
    client = client_for(Service(processes=processes))
    resp = client.get(service='wps', request='getcapabilities', version='1.0.0')
    names = resp.xpath_text('/wps:Capabilities'
                            '/wps:ProcessOfferings'
                            '/wps:Process'
                            '/ows:Identifier')
    # 'consecdrydays',
    expected_caps = sorted([
        'cvdp',
        'ensclus',
        'preproc',
        'shape_select',
        'sleep',
        'perfmetrics',
        'blocking',
        'stratosphere-troposphere',
        'annularmodes',
        'teleconnections',
        'weather_regimes',
    ])
    print(sorted(names.split()))
    print(expected_caps)
    assert sorted(names.split()) == expected_caps
