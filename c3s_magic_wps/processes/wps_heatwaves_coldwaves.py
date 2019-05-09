import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .utils import default_outputs, model_experiment_ensemble, year_ranges, outputs_from_plot_names

from .. import runner, util

LOGGER = logging.getLogger("PYWPS")


class HeatwavesColdwaves(Process):
    def __init__(self):
        inputs = [
            *model_experiment_ensemble(model_name='Model_historical',
                                       experiment_name='Experiment_historical',
                                       ensemble_name='Ensemble_historical'),
            *year_ranges((1850, 2005), (1971, 2000), start_name='start_historical', end_name='end_historical'),
            *model_experiment_ensemble(model_name='Model_projection',
                                       experiment_name='Experiment_projection',
                                       ensemble_name='Ensemble_projection'),
            *year_ranges((2006, 2050), (2020, 2050), start_name='start_projection', end_name='end_projection'),
            LiteralInput('quantile',
                         'Quantile',
                         abstract='quantile defining the exceedance/non-exceedance threshold',
                         data_type='float',
                         allowed_values=[0.5, 0.6, 0.7, 0.8, 0.9],
                         default=0.8),
            LiteralInput('min_duration',
                         'Minimum duration',
                         abstract='Min duration in days of a heatwave/coldwave event',
                         data_type='integer',
                         default=5),
            LiteralInput('operator',
                         'Operator',
                         abstract='either `>` for exceedances or `<` for non-exceedances',
                         data_type='string',
                         allowed_values=['exceedances', 'non-exceedances'],
                         default='non-exceedances'),
            LiteralInput('season',
                         'Season',
                         abstract='Choose a season.',
                         data_type='string',
                         allowed_values=['summer', 'winter'],
                         default='winter'),
        ]
        outputs = [
            ComplexOutput('plot',
                          'Extreme spell duration tasmin plot',
                          abstract='Generated extreme spell duration tasmin plot.',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('data',
                          'Extreme spell duration tasmin data',
                          abstract='Extreme spell duration tasmin data.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(HeatwavesColdwaves, self).__init__(
            self._handler,
            identifier="heatwaves_coldwaves",
            title="Heatwave and coldwave duration",
            version=runner.VERSION,
            abstract="""Metric showing the duration of heatwaves and coldwaves, to help understand potential changes in
                        energy demand.""",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata(
                    'Documentation',
                    'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_heatwaves_coldwaves.html',
                    role=util.WPS_ROLE_DOC),
                Metadata('Media',
                         util.diagdata_url() + '/heatwaves_coldwaves/extreme_spells_energy.png',
                         role=util.WPS_ROLE_MEDIA),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True)

    def _handler(self, request, response):
        response.update_status("starting ...", 0)

        # build esgf search constraints
        constraints = dict(model_historical=request.inputs['model_historical'][0].data,
                           experiment_historical=request.inputs['experiment_historical'][0].data,
                           ensemble_historical=request.inputs['ensemble_historical'][0].data,
                           start_year_historical=request.inputs['start_historical'][0].data,
                           end_year_historical=request.inputs['end_historical'][0].data,
                           model_projection=request.inputs['model_projection'][0].data,
                           experiment_projection=request.inputs['experiment_projection'][0].data,
                           ensemble_projection=request.inputs['ensemble_projection'][0].data,
                           start_year_projection=request.inputs['start_projection'][0].data,
                           end_year_projection=request.inputs['end_projection'][0].data)

        op = request.inputs['operator'][0].data
        if op == 'exceedances':
            operator = '>'
        elif op == 'non-exceedances':
            operator = '<'
        else:
            raise Exception('Unknown operator for task: ' + op)

        options = dict(
            quantile=request.inputs['quantile'][0].data,
            min_duration=request.inputs['min_duration'][0].data,
            operator=operator,
            season=request.inputs['season'][0].data,
            start_historical='{}-01-01'.format(request.inputs['start_historical'][0].data),
            end_historical='{}-12-31'.format(request.inputs['end_historical'][0].data),
            start_projection='{}-01-01'.format(request.inputs['start_projection'][0].data),
            end_projection='{}-12-31'.format(request.inputs['end_projection'][0].data),
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='heatwaves_coldwaves_wp7',
            constraints=constraints,
            options=options,
            start_year=1971,
            end_year=2080,
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

        if not result['success']:
            LOGGER.exception('esmvaltool failed!')
            response.update_status("exception occured: " + result['exception'], 100)
            return response

        try:
            self.get_outputs(result, response)
        except Exception as e:
            response.update_status("exception occured: " + str(e), 85)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(os.path.join(self.workdir, 'output'),
                                                                  'diagnostic_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
        response.outputs['plot'].output_format = Format('application/png')
        response.outputs['plot'].file = runner.get_output(result['plot_dir'],
                                                          path_filter=os.path.join('heatwaves_coldwaves', 'main'),
                                                          name_filter="*extreme_spell*",
                                                          output_format="png")

        response.outputs['data'].output_format = FORMATS.NETCDF
        response.outputs['data'].file = runner.get_output(result['work_dir'],
                                                          path_filter=os.path.join('heatwaves_coldwaves', 'main'),
                                                          name_filter="*extreme_spell*",
                                                          output_format="nc")
