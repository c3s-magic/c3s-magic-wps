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
        inputs = [
            *model_experiment_ensemble(
                model='MPI-ESM-MR',
                experiment='historical',
                ensemble='r1i1p1',
                max_occurs=1,
            ),
            *year_ranges((1980, 2005)),
            LiteralInput(
                'plot_type',
                'Plot type',
                abstract="""
                    Plot type: cycle (time), zonal (plev, lat), latlon (lat, lon),
                    cycle_latlon (time, lat, lon), cycle_zonal (time, plev, lat)
                """,
                data_type='string',
                allowed_values=['cycle', 'zonal', 'latlon', 'cycle_latlon', 'cycle_zonal'],
                default='cycle_zonal',
            ),
            LiteralInput(
                'time_avg',
                'Type of time average',
                abstract="""Type of time average""",
                data_type='string',
                allowed_values=['yearly', 'monthly', 'seasonal'],
                default='yearly',
            ),
            LiteralInput(
                'region',
                'Region',
                abstract="""Selected region""",
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
                    number of bootstrapping members used to determine uncertainties on model-reference differences
                    (typical number of bootstrapping members: 100)
                """,
                data_type='integer',
                default=100,
            ),
        ]
        outputs = [
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
                    'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_zmnam.html',
                    role=util.WPS_ROLE_DOC,
                ),
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
            model=request.inputs['model'][0].data,
            experiment=request.inputs['experiment'][0].data,
            ensemble=request.inputs['ensemble'][0].data,
        )

        options = dict(
            plot_type=request.inputs['plot_type'][0].data,
            time_avg=request.inputs['time_avg'][0].data,
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
        response.outputs['archive'].file = runner.compress_output(os.path.join(workdir, 'output'), 'zmnam_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)