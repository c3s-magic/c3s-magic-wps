from pywps import Service
from pywps.tests import assert_response_success

from .common import client_for
from c3s_magic_wps.processes import processes


def test_wps_caps():
    client = client_for(Service(processes=processes))
    resp = client.get(service='wps', request='getcapabilities', version='1.0.0')
    names = resp.xpath_text('/wps:Capabilities' '/wps:ProcessOfferings' '/wps:Process' '/ows:Identifier')
    # 'consecdrydays',
    # 'shape_select',
    # 'perfmetrics',
    expected_caps = sorted([
        'blocking',
        'capacity_factor',
        'combined_indices',
        'consecdrydays',
        'cvdp',
        'diurnal_temperature_index',
        'drought_indicator',
        'ensclus',
        'extreme_index',
        'heatwaves_coldwaves',
        'modes_of_variability',
        'multimodel_products',
        'preproc',
        'shapefile_selection',
        'sleep',
        'teleconnections',
        'weather_regimes',
        'zmnam',
        'toymodel',
        'rainfarm',
        'quantile_bias',
        'hyint',
        'smpi',
        'perfmetrics',
        'extreme_events',
        'meta',
    ])
    print(sorted(names.split()))
    print(expected_caps)
    assert sorted(names.split()) == expected_caps
