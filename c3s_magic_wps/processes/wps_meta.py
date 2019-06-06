import logging
import json

from pywps import Process, LiteralInput, LiteralOutput, ComplexOutput, Format
from pywps.app.Common import Metadata

from .utils import DataFinder

from .. import processes

LOGGER = logging.getLogger("PYWPS")


class Meta(Process):
    def __init__(self):
        inputs = [
            LiteralInput('process',
                         'Process for which to return the available data',
                         abstract='Process for which to return the available data.',
                         default='',
                         data_type='string',
                         min_occurs=0,
                         max_occurs=1)
        ]
        outputs = [
            ComplexOutput('drs',
                          'CMIP DRS Tree for available data',
                          supported_formats=[Format('application/json')],
                          as_reference=False)
        ]

        super(Meta, self).__init__(
            self._handler,
            identifier='meta',
            version='1.0',
            title='Meta process',
            abstract="""This is not a Metric. This process returns the available model data for the metric processes
                        in this WPS service.""",
            profile='',
            metadata=[
                Metadata('MAGIC WPS Metadata process', 'https://c3s-magic-wps.readthedocs.io/en/latest/'),
            ],
            inputs=inputs,
            outputs=outputs,
            store_supported=False,
            status_supported=False)

    @staticmethod
    def _handler(request, response):
        finder = DataFinder.get_instance()

        process_identifier = request.inputs['process'][0].data

        if not process_identifier:
            LOGGER.info("Process identifier not specified, returning entire tree")
            response.outputs['drs'].data = json.dumps(finder.data)

            return response

        LOGGER.info('Getting process inputs for: %s' % process_identifier)

        process = next((process for process in processes.processes if process.identifier == process_identifier), None)

        if not process:
            raise Exception("Cannot find process with identifier %s" % process_identifier)

        LOGGER.debug('Process object: %s' % process)

        # default to any model with monthly values for some variable
        required_variables = process.variables or []
        required_frequency = process.frequency or 'mon'

        response.outputs['drs'].data = json.dumps(
            finder.get_pruned_tree(required_variables=required_variables, required_frequency=required_frequency))

        return response
