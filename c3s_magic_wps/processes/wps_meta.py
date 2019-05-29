import json

from pywps import Process, LiteralInput, LiteralOutput, ComplexOutput, Format
from pywps.app.Common import Metadata

from .utils import DataFinder


class Meta(Process):
    def __init__(self):
        inputs = [LiteralInput('process', 'Process for which to return the available data', default='', data_type='string', min_occurs=0, max_occurs=1)]
        outputs = [ComplexOutput('drs',
                                 'CMIP DRS Tree for available data',
                                 supported_formats=[Format('application/json')],
                                 as_reference=False)
        ]

        super(Meta, self).__init__(self._handler,
                                    identifier='meta',
                                    version='1.0',
                                    title='Meta process',
                                    abstract='This process returns the available model data for the metric processes in this WPS service.',
                                    profile='',
                                    metadata=[
                                        Metadata('MAGIC WPS Metadata process', 'https://c3s-magic-wps.readthedocs.io/en/latest/'),
                                    ],
                                    inputs=inputs,
                                    outputs=outputs,
                                    store_supported=False,
                                    status_supported=True)

    @staticmethod
    def _handler(request, response):

        print('Getting process inputs', request.inputs['process'][0].data)
        
        finder = DataFinder()

        response.outputs['drs'].data = json.dumps(finder.get_pruned_tree(required_variables=['pr'], required_frequency='mon'))

        return response
