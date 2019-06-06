import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .utils import default_outputs, model_experiment_ensemble, outputs_from_plot_names, year_ranges

from .. import runner, util

LOGGER = logging.getLogger("PYWPS")


class HyInt(Process):
    def __init__(self):
        self.variables = ['pr']
        self.frequency = 'day'

        inputs = [
            *model_experiment_ensemble(model='ACCESS1-0',
                                       experiment='rcp85',
                                       ensemble='r1i1p1',
                                       min_occurs=2,
                                       max_occurs=100,
                                       required_variables=self.variables,
                                       required_frequency=self.frequency),
            *year_ranges((2005, 2020)),
            LiteralInput(
                'ref_model',
                'Reference Model',
                abstract='Choose a reference model like ACCESS1-0.',
                data_type='string',
                allowed_values=['ACCESS1-0'],
                default='ACCESS1-0',
                min_occurs=1,
                max_occurs=1,
            ),
            LiteralInput(
                'indices',
                'Indices',
                abstract='Indices to be analysed and plotted.',
                data_type='string',
                allowed_values=[
                    "pa_norm", "hyint", "int_norm", "r95_norm", "wsl_norm", "dsl_norm", "int", "dsl", "wsl"
                ],
                default="hyint",
                min_occurs=1,
                max_occurs=9,
            ),
            LiteralInput(
                'regions',
                'Regions',
                abstract='Regions for timeseries and maps.',
                data_type='string',
                allowed_values=["GL", "GL60", "TR", "SA", "AF", "IN", "EU", "EA", "AU"],
                default="GL",
                min_occurs=1,
                max_occurs=5,
            ),
            LiteralInput(
                'norm_year_start',
                'Norm year start',
                abstract='First year of reference normalization period to be used for normalized indices.',
                data_type='integer',
                default=1980,
            ),
            LiteralInput(
                'norm_year_end',
                'Norm year end',
                abstract='Last year of reference normalization period to be used for normalized indices.',
                data_type='integer',
                default=1999,
            ),
        ]

        outputs = [
            ComplexOutput('plot1',
                          'Plot1',
                          abstract='Single panel lon/lat map per individual index, multi-year mean',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('plot2',
                          'Plot2',
                          abstract='3-panel lon/lat maps per individual index with comparison to reference dataset, \
                multi-year mean',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('plot3',
                          'Plot3',
                          abstract='multipanel of indices of lon/lat maps with comparison to reference dataset, \
                multi-year mean',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('plot12',
                          'Plot12',
                          abstract='multipanel of indices with timeseries over multiple regions',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('plot13',
                          'Plot13',
                          abstract='multipanel of indices with timeseries for multiple models',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('plot14',
                          'Plot14',
                          abstract='multipanel of indices with summary of trend coefficients over multiple regions',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('plot15',
                          'Plot15',
                          abstract='multipanel of indices with summary of trend coefficients for multiple models',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as a zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(HyInt, self).__init__(
            self._handler,
            identifier="hyint",
            title="HyInt - Hydroclimatic intensity and extremes",
            version=runner.VERSION,
            abstract='HyInt hydroclimatic indices calculation and plotting.',
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata('Documentation',
                         'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_hyint.html',
                         role=util.WPS_ROLE_DOC),
                Metadata('Note: Selected models should be experiment (eg. "rcp85") and not historical. The historical \
                data will be added automatically.'),
                Metadata('Estimated Calculation Time', '30 minutes'),
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
            reference=request.inputs['ref_model'][0].data,
        )

        options = dict(
            indices=request.inputs['indices'][0].data,
            regions=request.inputs['regions'][0].data,
            norm_year_start=request.inputs['norm_year_start'][0].data,
            norm_year_end=request.inputs['norm_year_end'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=workdir,
            diag='hyint',
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
                self.get_outputs(constraints['models'], result, response)
            except Exception as e:
                response.update_status("exception occured: " + str(e), 85)
        else:
            LOGGER.exception('esmvaltool failed!')
            response.update_status("exception occured: " + result['exception'], 85)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(os.path.join(workdir, 'output'), 'hyint_result.zip')
        response.update_status("done.", 100)
        return response

    def get_outputs(self, models, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
        response.outputs['plot1'].output_format = Format('image/png')
        response.outputs['plot1'].file = runner.get_output(result['plot_dir'],
                                                           path_filter=os.path.join('hyint', 'main'),
                                                           name_filter="*_??_map",
                                                           output_format="png")
        response.outputs['plot2'].output_format = Format('image/png')
        response.outputs['plot2'].file = runner.get_output(result['plot_dir'],
                                                           path_filter=os.path.join('hyint', 'main'),
                                                           name_filter="*comp_map",
                                                           output_format="png")
        response.outputs['plot3'].output_format = Format('image/png')
        response.outputs['plot3'].file = runner.get_output(result['plot_dir'],
                                                           path_filter=os.path.join('hyint', 'main'),
                                                           name_filter="multiindex*_map",
                                                           output_format="png")
        response.outputs['plot12'].output_format = Format('image/png')
        response.outputs['plot12'].file = runner.get_output(result['plot_dir'],
                                                            path_filter=os.path.join('hyint', 'main'),
                                                            name_filter="*multiregion_timeseries*",
                                                            output_format="png")
        response.outputs['plot13'].output_format = Format('image/png')
        response.outputs['plot13'].file = runner.get_output(result['plot_dir'],
                                                            path_filter=os.path.join('hyint', 'main'),
                                                            name_filter="*_multimodel*_timeseries*",
                                                            output_format="png")
        response.outputs['plot14'].output_format = Format('image/png')
        response.outputs['plot14'].file = runner.get_output(result['plot_dir'],
                                                            path_filter=os.path.join('hyint', 'main'),
                                                            name_filter="*multiregion_trend_summary*",
                                                            output_format="png")
        response.outputs['plot15'].output_format = Format('image/png')
        response.outputs['plot15'].file = runner.get_output(result['plot_dir'],
                                                            path_filter=os.path.join('hyint', 'main'),
                                                            name_filter="*_multimodel*_trend_summary*",
                                                            output_format="png")
        response.outputs['model'].output_format = FORMATS.NETCDF
        response.outputs['model'].file = runner.get_output(result['work_dir'],
                                                           path_filter=os.path.join('hyint', 'main'),
                                                           name_filter="hyint_{}*_ALL".format(models[0]),
                                                           output_format="nc")
