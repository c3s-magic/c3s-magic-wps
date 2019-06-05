import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.inout.literaltypes import make_allowedvalues
from pywps.response.status import WPS_STATUS

from .. import runner, util
from .utils import (default_outputs, model_experiment_ensemble, outputs_from_data_names, outputs_from_plot_names,
                    year_ranges)

LOGGER = logging.getLogger("PYWPS")


class Perfmetrics(Process):
    def __init__(self):
        self.variables = ['ta', 'ua', 'va', 'zg', 'hus', 'tas', 'ts', 'pr', 'clt', 'rlut', 'rsut']
        self.frequency = 'mon'

        inputs = []
        outputs = [
            ComplexOutput('rmsd',
                          'RMSD metric',
                          abstract='RMSD metric.',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(Perfmetrics, self).__init__(
            self._handler,
            identifier="perfmetrics",
            title="Performance metrics for essential climate parameters",
            version=runner.VERSION,
            abstract="""The goal is to create a standard recipe for the calculation of performance metrics to quantify
                        the ability of the models to reproduce the climatological mean annual cycle for selected
                        Essential Climate Variables (ECVs) plus some additional corresponding diagnostics and plots
                        to better understand and interpret the results.""",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata('Documentation',
                         'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_perfmetrics.html',
                         role=util.WPS_ROLE_DOC),
                Metadata('Estimated Calculation Time', '20 Minutes'),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True,
        )

    def _handler(self, request, response):
        response.update_status("starting ...", 0)
        workdir = self.workdir

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(workdir=workdir,
                                                          diag='perfmetrics_CMIP5',
                                                          output_format='png')

        # recipe output
        response.outputs['recipe'].output_format = FORMATS.TEXT
        response.outputs['recipe'].file = recipe_file

        # run diag
        response.update_status("running diagnostic ...", 20)
        result = runner.run(recipe_file, config_file, skip_nonexistent=True)

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
        response.outputs['archive'].file = runner.compress_output(os.path.join(workdir, 'output'),
                                                                  'perfmetrics_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        response.update_status("collecting output ...", 80)

        response.outputs['rmsd'].output_format = Format('application/png')
        response.outputs['rmsd'].file = runner.get_output(result['plot_dir'],
                                                          path_filter=os.path.join('collect', 'RMSD'),
                                                          name_filter="*",
                                                          output_format="png")
