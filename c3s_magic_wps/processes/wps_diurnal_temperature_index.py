import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .. import runner, util
from .utils import default_outputs, model_experiment_ensemble, outputs_from_plot_names, year_ranges

LOGGER = logging.getLogger("PYWPS")


class DiurnalTemperatureIndex(Process):
    def __init__(self):
        self.variables = ['tasmax', 'tasmin']
        self.frequency = 'day'

        inputs = [
            *model_experiment_ensemble(model='MPI-ESM-MR',
                                       experiment='rcp85',
                                       ensemble='r1i1p1',
                                       max_occurs=1,
                                       required_variables=self.variables,
                                       required_frequency=self.frequency),
            *year_ranges((1990, 2000), start_name='start_historical', end_name='end_historical'),
            *year_ranges((2070, 2080), start_name='start_projection', end_name='end_projection'),
            LiteralInput(
                'start_longitude',
                'Start longitude',
                abstract='Minimum longitude.',
                data_type='integer',
                default=-10,
            ),
            LiteralInput(
                'end_longitude',
                'End longitude',
                abstract='Maximum longitude.',
                data_type='integer',
                default=40,
            ),
            LiteralInput(
                'start_latitude',
                'Start latitude',
                abstract='Minimum latitude.',
                data_type='integer',
                default=27,
            ),
            LiteralInput(
                'end_latitude',
                'End latitude',
                abstract='Maximum latitude.',
                data_type='integer',
                default=70,
            ),
        ]
        self.plotlist = []
        outputs = [
            ComplexOutput('plot',
                          'Diurnal Temperature Variation (DTR) Indicator plot',
                          abstract='The diurnal temperature indicator to estimate energy demand.',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('data',
                          'Diurnal Temperature Variation (DTR) Indicator data',
                          abstract='The diurnal temperature indicator data.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(DiurnalTemperatureIndex, self).__init__(
            self._handler,
            identifier="diurnal_temperature_index",
            title="Diurnal Temperature Variation (DTR) Indicator",
            version=runner.VERSION,
            abstract="""
                Metric showing the diurnal temperature indicator to estimate energy demand.
            """,
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata(
                    'Documentation',
                    'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_diurnal_temperature_index.html',  # noqa
                    role=util.WPS_ROLE_DOC),
                Metadata('Media',
                         util.diagdata_url() + '/dtr/diurnal_temperature_variation.png',
                         role=util.WPS_ROLE_MEDIA),
                Metadata('Estimated Calculation Time', '6 minutes'),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True)

    def _handler(self, request, response):
        response.update_status("starting ...", 0)

        # build esgf search constraints
        constraints = dict(model=request.inputs['model'][0].data,
                           experiment=request.inputs['experiment'][0].data,
                           ensemble=request.inputs['ensemble'][0].data,
                           start_year_historical=request.inputs['start_historical'][0].data,
                           end_year_historical=request.inputs['end_historical'][0].data,
                           start_year_projection=request.inputs['start_projection'][0].data,
                           end_year_projection=request.inputs['end_projection'][0].data)

        options = dict(
            start_longitude=request.inputs['start_longitude'][0].data,
            end_longitude=request.inputs['end_longitude'][0].data,
            start_latitude=request.inputs['start_latitude'][0].data,
            end_latitude=request.inputs['end_latitude'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='diurnal_temperature_index',
            constraints=constraints,
            options=options,
            start_year=request.inputs['start_historical'][0].data,
            end_year=request.inputs['end_projection'][0].data,
            output_format='png',
        )

        # recipe output
        response.outputs['recipe'].output_format = FORMATS.TEXT
        response.outputs['recipe'].file = recipe_file

        # run diag
        response.update_status("running diagnostic ...", 20)
        result = runner.run(recipe_file, config_file)

        response.outputs['success'].data = result['success']

        # log output
        response.outputs['log'].output_format = FORMATS.TEXT
        response.outputs['log'].file = result['logfile']

        # debug log output
        response.outputs['debug_log'].output_format = FORMATS.TEXT
        response.outputs['debug_log'].file = result['debug_logfile']

        if result['success']:
            try:
                self.get_outputs(result, response)
            except Exception as e:
                response.update_status("exception occured: " + str(e), 85)
                LOGGER.exception('Getting output failed: ' + str(e))
        else:
            LOGGER.exception('esmvaltool failed!')
            response.update_status("exception occured: " + result['exception'], 85)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(os.path.join(self.workdir, 'output'),
                                                                  'diurnal_temperature_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
        response.outputs['plot'].output_format = Format('application/png')
        response.outputs['plot'].file = runner.get_output(result['plot_dir'],
                                                          path_filter=os.path.join('diurnal_temperature_indicator',
                                                                                   'main'),
                                                          name_filter="*",
                                                          output_format="png")

        response.outputs['data'].output_format = FORMATS.NETCDF
        response.outputs['data'].file = runner.get_output(result['work_dir'],
                                                          path_filter=os.path.join('diurnal_temperature_indicator',
                                                                                   'main'),
                                                          name_filter="Seasonal_DTRindicator*",
                                                          output_format="nc")
