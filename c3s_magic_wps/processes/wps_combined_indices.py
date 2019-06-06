import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS
from pywps.inout.literaltypes import AllowedValue
from pywps.validator.allowed_value import ALLOWEDVALUETYPE

from .utils import default_outputs, model_experiment_ensemble, year_ranges, outputs_from_plot_names

from .. import runner, util

LOGGER = logging.getLogger("PYWPS")


class CombinedIndices(Process):
    def __init__(self):
        self.variables = ['pr']
        self.frequency = 'mon'
        inputs = [
            *model_experiment_ensemble(model='MPI-ESM-MR',
                                       experiment='historical',
                                       ensemble='r1i1p1',
                                       max_occurs=1,
                                       required_variables=self.variables,
                                       required_frequency=self.frequency),
            *year_ranges((1950, 2005)),
            LiteralInput('running_mean',
                         'Running Mean',
                         abstract='Length of the window for which the running mean is computed.',
                         data_type='integer',
                         allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=1, maxval=365),
                         default=5),
            LiteralInput(
                'moninf',
                'First month month of the seasonal mean period',
                abstract="""First month of the seasonal mean period to be computed, if null the monthly anomalies
                            will be computed.""",
                data_type='string',
                allowed_values=['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 'null'],
                default='1'),
            LiteralInput(
                'monsup',
                'Last month month of the seasonal mean period',
                abstract="""Last month of the seasonal mean period to be computed, if null the monthly anomalies
                            will be computed.""",
                data_type='string',
                allowed_values=['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 'null'],
                default='3'),
            LiteralInput('region',
                         'Region',
                         abstract='Region over which to calculate the metric.',
                         data_type='string',
                         allowed_values=['NAO', 'Nino3', 'Nino3.4', 'Nino4', 'SOI'],
                         default='NAO'),
            LiteralInput('standardized',
                         'Standardized',
                         abstract='Boolean indictating if standardization should be computed.',
                         data_type='boolean',
                         default=True),
        ]
        outputs = [
            ComplexOutput('plot',
                          'Combined Indices plot',
                          abstract='Combined Indices plot.',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('data',
                          'Data',
                          abstract='Generated combined indices data.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(CombinedIndices, self).__init__(
            self._handler,
            identifier="combined_indices",
            title="Single and multi-model indices based on area averages",
            version=runner.VERSION,
            abstract="""Metric showning single and multi model indices based on area averages.""",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata(
                    'Documentation',
                    'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_combined_climate_extreme_index.html',  # noqa
                    role=util.WPS_ROLE_DOC),
                Metadata('Estimated Calculation Time', '1 minute'),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True,
        )

    def _handler(self, request, response):
        response.update_status("starting ...", 0)

        # build esgf search constraints
        constraints = dict(
            model=request.inputs['model'][0].data,
            experiment=request.inputs['experiment'][0].data,
            ensemble=request.inputs['ensemble'][0].data,
        )

        options = dict(
            standardized=request.inputs['standardized'][0].data,
            region=request.inputs['region'][0].data,
            moninf=request.inputs['moninf'][0].data,
            monsup=request.inputs['monsup'][0].data,
            running_mean=request.inputs['running_mean'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='combined_indices',
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

        if result['success']:
            try:
                self.get_outputs(result, response)
            except Exception as e:
                response.update_status("exception occured: " + str(e), 85)
                LOGGER.exception('Getting output failed: ' + str(e))
        else:
            LOGGER.exception('esmvaltool failed!')
            response.update_status("exception occured: " + result['exception'], 100)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(os.path.join(self.workdir, 'output'),
                                                                  'combined_indices_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
        response.outputs['plot'].output_format = Format('image/png')
        response.outputs['plot'].file = runner.get_output(result['plot_dir'],
                                                          path_filter=os.path.join('combine_indices', 'main'),
                                                          name_filter="*",
                                                          output_format="png")
        response.outputs['data'].output_format = FORMATS.NETCDF
        response.outputs['data'].file = runner.get_output(result['work_dir'],
                                                          path_filter=os.path.join('combine_indices', 'main'),
                                                          name_filter="*",
                                                          output_format="nc")
