import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .utils import default_outputs, model_experiment_ensemble, year_ranges, outputs_from_plot_names

from .. import runner, util

LOGGER = logging.getLogger("PYWPS")


class CapacityFactor(Process):
    def __init__(self):
        inputs = [
            *model_experiment_ensemble(start_end_year=(1850, 2005), start_end_defaults=(1980, 2005)),
            LiteralInput(
                'start_longitude',
                'Start longitude',
                abstract='minimum longitude',
                data_type='integer',
                default=200,
            ),
            LiteralInput(
                'end_longitude',
                'End longitude',
                abstract='maximum longitude',
                data_type='integer',
                default=300,
            ),
            LiteralInput(
                'start_latitude',
                'Start latitude',
                abstract='minimum latitude',
                data_type='integer',
                default=27,
            ),
            LiteralInput(
                'end_latitude',
                'End latitude',
                abstract='maximum latitude',
                data_type='integer',
                default=70,
            ),
            LiteralInput(
                'scheme',
                'Scheme',
                abstract='regridding scheme',
                data_type='string',
                allowed_values=['linear', 'nearest', 'area_weighted',
                                'unstructured_nearest'],
                default='linear',
            ),
            LiteralInput(
                'threshold_fraction',
                'Threshold Fraction',
                abstract='Threshold Fraction (between 0 and 1.0) for fillvalues mask',
                data_type='float',
                default='linear',
            ),
            LiteralInput(
                'season',
                'Season',
                abstract='Season',
                data_type='string',
                allowed_values=['djf', 'mam', 'jja',
                                'son'],
                default='djf',
            ),
        ]
        self.plotlist = []
        outputs = [
            ComplexOutput('plot',
                          'Capacity Factor of Wind Power plot',
                          abstract='Ratio of average estimated power to theoretical maximum power.',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('data',
                          'Capacity Factor of Wind Power data',
                          abstract='Ratio of average estimated power to theoretical maximum power.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(CapacityFactor, self).__init__(
            self._handler,
            identifier="capacity_factor",
            title="Capacity factor of wind power",
            version=runner.VERSION,
            abstract=("The goal of this diagnostic is to compute the wind capacity factor, taking as input the daily "
                       "instantaneous surface wind speed, which is then extrapolated to obtain the wind speed at a "
                       "height of 100 m as described in Lledó (2017)."),
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata(
                    'Documentation',
                    'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_capacity_factor.html',
                    role=util.WPS_ROLE_DOC),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True)

    def _handler(self, request, response):
        response.update_status("starting ...", 0)

        # build esgf search constraints
        constraints = dict(
            model=request.inputs['model'][0].data,
            experiment=request.inputs['experiment'][0].data,
            ensemble=request.inputs['ensemble'][0].data,
        )

        options = dict(
            start_longitude=request.inputs['start_longitude'][0].data,
            end_longitude=request.inputs['end_longitude'][0].data,
            start_latitude=request.inputs['start_latitude'][0].data,
            end_latitude=request.inputs['end_latitude'][0].data,
            scheme=request.inputs['scheme'][0].data,
            threshold_fraction=request.inputs['threshold_fraction'][0].data,
            season=request.inputs['season'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='capacity_factor_wp7',
            constraints=constraints,
            options=options,
            start_year=request.inputs['start_year'][0].data,
            end_year=request.inputs['end_year'][0].data,
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
                                                                  'capacity_factor_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
        response.outputs['plot'].output_format = Format('application/png')
        response.outputs['plot'].file = runner.get_output(result['plot_dir'],
                                                          path_filter=os.path.join('capacity_factor', 'main'),
                                                          name_filter="capacity_factor*",
                                                          output_format="png")

        response.outputs['data'].output_format = FORMATS.NETCDF
        response.outputs['data'].file = runner.get_output(result['work_dir'],
                                                          path_filter=os.path.join('capacity_factor', 'main'),
                                                          name_filter="capacity_factor*",
                                                          output_format="nc")
