from pywps import Process, LiteralInput, LiteralOutput, ComplexOutput, Format
from pywps.app.Common import Metadata


class Meta(Process):
    def __init__(self):
        inputs = [LiteralInput('process', 'Process for which to return the available data', data_type='string', max_occurs=1)]
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
        import time

        print('Getting process input', request.inputs['process'][0].data)
        # print('Getting process input', request.inputs['process'][1].data)
        # print('Getting process input', request.inputs['process'][2].data)

        if 'delay' in request.inputs:
            sleep_delay = request.inputs['delay'][0].data
        else:
            sleep_delay = 1

        time.sleep(sleep_delay)
        response.update_status('PyWPS Process started. Waiting...', 20)
        time.sleep(sleep_delay)
        response.update_status('PyWPS Process started. Waiting...', 40)
        time.sleep(sleep_delay)
        response.update_status('PyWPS Process started. Waiting...', 60)
        time.sleep(sleep_delay)
        response.update_status('PyWPS Process started. Waiting...', 80)
        time.sleep(sleep_delay)
        #response.outputs['sleep_output'].data = 'done sleeping (delay={})'.format(sleep_delay)

        return response
