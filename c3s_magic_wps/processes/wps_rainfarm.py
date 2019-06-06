import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .. import runner, util
from .utils import default_outputs, model_experiment_ensemble, outputs_from_plot_names, year_ranges

LOGGER = logging.getLogger("PYWPS")


class RainFARM(Process):
    def __init__(self):
        self.variables = ['pr']
        self.frequency = 'day'

        inputs = [
            *model_experiment_ensemble(model='ACCESS1-0',
                                       experiment='historical',
                                       ensemble='r1i1p1',
                                       max_occurs=1,
                                       required_variables=self.variables,
                                       required_frequency=self.frequency),
            *year_ranges((1997, 1999)),
            LiteralInput(
                'start_longitude',
                'Start longitude',
                abstract='Minimum longitude.',
                data_type='integer',
                default=5,
            ),
            LiteralInput(
                'end_longitude',
                'End longitude',
                abstract='Maximum longitude.',
                data_type='integer',
                default=15,
            ),
            LiteralInput(
                'start_latitude',
                'Start latitude',
                abstract='Minimum latitude.',
                data_type='integer',
                default=40,
            ),
            LiteralInput(
                'end_latitude',
                'End latitude',
                abstract='Maximum latitude.',
                data_type='integer',
                default=50,
            ),
            LiteralInput(
                'target_grid',
                'Target Grid',
                abstract=('Target grid in degrees (e.g. 1x1) can also be the name of one '
                          'of the datasets to use the grid from that dataset.'),
                data_type='string',
                default='1x1',
            ),
            LiteralInput(
                'scheme',
                'Scheme',
                abstract='Regridding scheme to be used.',
                data_type='string',
                allowed_values=['linear', 'nearest', 'area_weighted', 'unstructured_nearest'],
                default='area_weighted',
            ),
            LiteralInput(
                'slope',
                'Slope',
                abstract=('Spatial spectral slope (set to 0 to compute from'
                          'large scales).'),
                data_type='float',
                default=0.,
            ),
            LiteralInput(
                'nens',
                'No. of ensemble members',
                abstract='Number of ensemble members to be calculated.',
                data_type='integer',
                default=2,
            ),
            LiteralInput(
                'nf',
                'No. of subdivisions',
                abstract=('Number of subdivisions for downscaling (e.g. 8 will '
                          'produce output fields with linear resolution '
                          'increased by a factor 8).'),
                data_type='integer',
                default=8,
            ),
            LiteralInput(
                'conserv_glob',
                'Conserve Global',
                abstract='Conserve precipitation over full domain?',
                data_type='string',
                allowed_values=['true', 'false'],
                default='false',
            ),
            LiteralInput(
                'conserv_smooth',
                'Conserve Smooth',
                abstract=('Conserve precipitation using convolution (if '
                          'neither is chosen box conservation is used)?'),
                data_type='string',
                allowed_values=['true', 'false'],
                default='true',
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

        super(RainFARM, self).__init__(
            self._handler,
            identifier="rainfarm",
            title="RainFARM stochastic downscaling",
            version=runner.VERSION,
            abstract="""Precipitation extremes and small-scale variability are essential drivers in many climate change
                        impact studies. However, the spatial resolution currently achieved by global and regional
                        climate models is still insufficient to correctly identify the fine structure of precipitation
                        intensity fields. In the absence of a proper physically based representation, this scale gap
                        can be at least temporarily bridged by adopting a stochastic rainfall downscaling technique
                        (Rebora et al, 2006). With this aim, the Rainfall Filtered Autoregressive Model (RainFARM)was
                        developed to apply the stochastic precipitation downscaling method to climate models. The
                        selected region needs to have equal and even number of longitude (in any case it is cut) and
                        latitude grid points (e.g., 2x2, 4x4, ...). Warning: downcaling can reach very high resolution,
                        so select a limited area.""",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata('Documentation',
                         'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_rainfarm.html',
                         role=util.WPS_ROLE_DOC),
                Metadata('Estimated Calculation Time', '3 Minutes'),
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
            start_longitude=request.inputs['start_longitude'][0].data,
            end_longitude=request.inputs['end_longitude'][0].data,
            start_latitude=request.inputs['start_latitude'][0].data,
            end_latitude=request.inputs['end_latitude'][0].data,
            target_grid=request.inputs['target_grid'][0].data,
            scheme=request.inputs['scheme'][0].data,
            slope=request.inputs['slope'][0].data,
            nens=request.inputs['nens'][0].data,
            nf=request.inputs['nf'][0].data,
            conserv_glob=request.inputs['conserv_glob'][0].data,
            conserv_smooth=request.inputs['conserv_smooth'][0].data,
            weights_climo='false',
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=workdir,
            diag='rainfarm',
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
        # Disable HDF5 library version mismatched error for rainfarm metric
        os.environ["HDF5_DISABLE_VERSION_CHECK"] = "1"
        result = runner.run(recipe_file, config_file)
        del os.environ["HDF5_DISABLE_VERSION_CHECK"]

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
        response.outputs['archive'].file = runner.compress_output(os.path.join(workdir, 'output'),
                                                                  'rainfarm_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
