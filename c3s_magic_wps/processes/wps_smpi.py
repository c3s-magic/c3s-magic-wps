import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .. import runner, util
from .utils import default_outputs, model_experiment_ensemble, outputs_from_plot_names, year_ranges

LOGGER = logging.getLogger("PYWPS")


class SMPI(Process):
    def __init__(self):
        # this list contains variables from multiple reals, which our data finder cannot handle yet.
        # self.variables = ['ta', 'va', 'ua', 'hus', 'tas', 'psl', 'pr', 'tos', 'sic', 'tauu', 'tauv']
        self.variables = ['ta', 'va', 'ua', 'hus', 'tas', 'psl', 'pr']
        self.frequency = 'mon'

        inputs = [
            *model_experiment_ensemble(model='MPI-ESM-MR',
                                       experiment='historical',
                                       ensemble='r1i1p1',
                                       min_occurs=2,
                                       required_variables=self.variables,
                                       required_frequency=self.frequency),
            *year_ranges((1980, 1985)),
            LiteralInput(
                'region',
                'Region',
                abstract="""Region over which to calculate the metric.""",
                data_type='string',
                allowed_values=[
                    'global', 'trop', 'nhext', 'shext', 'nhtrop', 'shtrop', 'nh', 'sh', 'nhmidlat', 'shmidlat',
                    'nhpolar', 'shpolar', 'eq'
                ],
                default='global',
            ),
            LiteralInput(
                'smpi_n_bootstrap',
                'Number of bootstrapping members',
                abstract="""
                    Number of bootstrapping members used to determine uncertainties on model-reference differences
                    (typical number of bootstrapping members: 100).
                """,
                data_type='integer',
                default=100,
            ),
        ]
        outputs = [
            ComplexOutput('smpi',
                          'SMPI plot',
                          abstract='Generated output plot of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(SMPI, self).__init__(
            self._handler,
            identifier="smpi",
            title="Single Model Performance index",
            version=runner.VERSION,
            abstract="""
                This diagnostic calculates the Single Model Performance Index (SMPI) following Reichler and Kim (2008).
                The SMPI (called "I2") is based on the comparison of several different climate variables (atmospheric,
                surface and oceanic) between climate model simulations and observations or reanalyses, and it focuses
                on the validation of the time-mean state of climate.
            """,
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata(
                    'Documentation',
                    'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_smpi.html',
                    role=util.WPS_ROLE_DOC,
                ),
                Metadata('Estimated Calculation Time', '10 minutes'),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True)

    def _handler(self, request, response):
        response.update_status("starting ...", 0)
        workdir = self.workdir

        # build esgf search constraints
        constraints = dict(
            models=request.inputs['model'],
            experiments=request.inputs['experiment'],
            ensembles=request.inputs['ensemble'],
        )

        options = dict(
            region=request.inputs['region'][0].data,
            smpi_n_bootstrap=request.inputs['smpi_n_bootstrap'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=workdir,
            diag='smpi',
            options=options,
            constraints=constraints,
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
        else:
            LOGGER.exception('esmvaltool failed!')
            response.update_status("exception occured: " + result['exception'], 85)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(os.path.join(workdir, 'output'), 'smpi_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
        response.outputs['smpi'].output_format = Format('application/png')
        response.outputs['smpi'].file = runner.get_output(
            result['plot_dir'],
            path_filter=os.path.join('collect', 'SMPI'),
            name_filter="SMPI",
            output_format="png",
        )
