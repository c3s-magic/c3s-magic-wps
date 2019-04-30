import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .utils import default_outputs, model_experiment_ensemble, year_ranges, outputs_from_plot_names

from .. import runner, util

LOGGER = logging.getLogger("PYWPS")


class ExtremeIndex(Process):
    def __init__(self):
        inputs = [
            LiteralInput(
                'metric',
                'Metric',
                abstract='Choose a metric to calculate.',
                data_type='string',
                allowed_values=['t10p', 't90p', 'rx5day', 'Wx'], # 'cdd' <- these do not work
                default='Wx'),
        ]
        self.plotlist = []
        outputs = [
            ComplexOutput(
                'plot',
                'Combined Climate Extreme Index plot',
                abstract='Combined Climate Extreme Index plot.',
                as_reference=True,
                supported_formats=[Format('image/png')]),
            ComplexOutput(
                'data',
                'Combined Climate Extreme Index data',
                abstract=
                'Combined Climate Extreme Index data.',
                as_reference=True,
                supported_formats=[Format('application/zip')]),
            ComplexOutput(
                'archive',
                'Archive',
                abstract=
                'The complete output of the ESMValTool processing as an zip archive.',
                as_reference=True,
                supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(ExtremeIndex, self).__init__(
            self._handler,
            identifier="extreme_index",
            title="Combined Climate Extreme Index",
            version=runner.VERSION,
            abstract="""Metric showing extreme indices relevant to the insurance industry (heat, cold, wind, flood and drought indices).""",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata(
                    'Documentation',
                    'https://copernicus-wps-demo.readthedocs.io/en/latest/processes.html#pydemo',
                    role=util.WPS_ROLE_DOC),
                Metadata(
                    'Media',
                    util.diagdata_url() + '/risk_index/insurance_risk_indices.png',
                    role=util.WPS_ROLE_MEDIA),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True)

    def _handler(self, request, response):
        response.update_status("starting ...", 0)

        # build esgf search constraints
        constraints = dict()

        options = dict(
            metric=request.inputs['metric'][0].data
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='extreme_index_wp7',
            constraints=constraints,
            options=options,
            start_year=1971,
            end_year=2040,
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
            self.get_outputs(result, constraints, options, response)
        except Exception as e:
            response.update_status("exception occured: " + str(e), 85)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(
            os.path.join(self.workdir, 'output'), 'diagnostic_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, constraints, options, response):
        # result plot
        response.update_status("collecting output ...", 80)
        response.outputs['plot'].output_format = Format('application/png')
        response.outputs['plot'].file = runner.get_output(
            result['plot_dir'],
            path_filter=os.path.join('extreme_index', 'main'),
            name_filter="{}*".format(options['metric']),
            output_format="png")

        response.outputs['data'].output_format = FORMATS.NETCDF
        response.outputs['data'].file = runner.get_output(
            result['work_dir'],
            path_filter=os.path.join('extreme_index', 'main'),
            name_filter="*risk_insurance_index*",
            output_format="nc")