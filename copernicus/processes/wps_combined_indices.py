import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from copernicus.processes.utils import default_outputs, model_experiment_ensemble, year_ranges, outputs_from_plot_names

from .. import runner, util

LOGGER = logging.getLogger("PYWPS")


class CombinedIndices(Process):
    def __init__(self):
        inputs = [
            LiteralInput(
                'weights',
                'Weights',
                abstract='Either `equal`, for equal weights, `null` for no weights.',
                data_type='string',
                allowed_values=['equal', 'null'],
                default='equal'),
            LiteralInput(
                'moninf',
                'First month month of the seasonal mean period',
                abstract='The first month of the seasonal mean period to be computed, if none the monthly anomalies will be computed.',
                data_type='string',
                allowed_values=['1', '2', '3', '4','5', '6', '7', '8', '9', '10', '11', '12', 'null'],
                default='1'),
            LiteralInput(
                'monsup',
                'Last month month of the seasonal mean period',
                abstract='the last month of the seasonal mean period to be computed, if none the monthly anomalies will be computed.',
                data_type='string',
                allowed_values=['1', '2', '3', '4','5', '6', '7', '8', '9', '10', '11', '12'],
                default='3'),
        ]
        outputs = [
            ComplexOutput(
                'data',
                'Data',
                abstract='Generated combined indices data.',
                as_reference=True,
                supported_formats=[FORMATS.NETCDF]),
            ComplexOutput(
                'archive',
                'Archive',
                abstract=
                'The complete output of the ESMValTool processing as an zip archive.',
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
                    'https://copernicus-wps-demo.readthedocs.io/en/latest/processes.html#pydemo',
                    role=util.WPS_ROLE_DOC),
                Metadata(
                    'Media',
                    util.diagdata_url() + '/pydemo/pydemo_thumbnail.png',
                    role=util.WPS_ROLE_MEDIA),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True)

    def _handler(self, request, response):
        response.update_status("starting ...", 0)

        # build esgf search constraints
        constraints = dict(
        )

        options = dict(
            weights=request.inputs['weights'][0].data,
            moninf=request.inputs['moninf'][0].data,
            monsup=request.inputs['monsup'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='combined_indices_wp6',
            constraints=constraints,
            options=options,
            start_year=1950,
            end_year=2005,
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
            response.update_status("exception occured: " + result['exception'],
                                   100)
            return response

        try:
            self.get_outputs(result, response)
        except Exception as e:
            response.update_status("exception occured: " + str(e), 85)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(
            os.path.join(self.workdir, 'output'), 'diagnostic_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
        response.outputs['data'].output_format = FORMATS.NETCDF
        response.outputs['data'].file = runner.get_output(
            result['work_dir'],
            path_filter=os.path.join('combine_indices', 'main'),
            name_filter="*",
            output_format="nc")