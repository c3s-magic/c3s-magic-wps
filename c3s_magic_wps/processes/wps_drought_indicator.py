import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .. import runner, util
from .utils import default_outputs, model_experiment_ensemble, outputs_from_plot_names, year_ranges

LOGGER = logging.getLogger("PYWPS")


class DroughtIndicator(Process):
    def __init__(self):
        self.variables = ['pr', 'tas']
        self.frequency = 'mon'

        inputs = [
            *model_experiment_ensemble(model='ACCESS1-0',
                                       experiment='historical',
                                       ensemble='r1i1p1',
                                       max_occurs=1,
                                       required_variables=self.variables,
                                       required_frequency=self.frequency),
            *year_ranges((1990, 1999)),
            LiteralInput('ref_dataset',
                         'Reference Dataset',
                         abstract='Choose a reference dataset like ERA-Interim.',
                         data_type='string',
                         allowed_values=['ERA-Interim'],
                         default='ERA-Interim',
                         min_occurs=1,
                         max_occurs=1),
        ]
        self.plotlist = []
        outputs = [
            ComplexOutput('spi_plot',
                          'SPI Histogram plot',
                          abstract='Generated spi histogram plot.',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('spei_plot',
                          'SPEI Histogram plot',
                          abstract='Generated SPEI Histogram plot.',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('spi_model',
                          'SPI Data for the model',
                          abstract='The complete SPI Data for the model.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('spi_reference',
                          'SPI Data for the reference model',
                          abstract='The complete SPI Data for the reference model.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('spei_model',
                          'SPEI Data for the model',
                          abstract='The complete SPEI Data for the model.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('spei_reference',
                          'SPEI Data for the reference model',
                          abstract='The complete SPEI Data for the reference model.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(DroughtIndicator, self).__init__(
            self._handler,
            identifier="drought_indicator",
            title="Drought indicator",
            version=runner.VERSION,
            abstract="""The drought indicator calculates diagnostics for meteorological drought.""",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata('Documentation',
                         'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_spei.html',
                         role=util.WPS_ROLE_DOC),
                Metadata('Estimated Calculation Time', '45 minutes'),
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
            reference=request.inputs['ref_dataset'][0].data,
        )

        options = dict()

        # generate recipe
        response.update_status("generate recipe ...", 10)
        start_year = request.inputs['start_year'][0].data
        end_year = request.inputs['end_year'][0].data
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='spei',
            constraints=constraints,
            options=options,
            start_year=start_year,
            end_year=end_year,
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
            response.update_status("exception occured: " + result['exception'], 85)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(os.path.join(self.workdir, 'output'),
                                                                  'drought_indicator_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
        response.outputs['spi_plot'].output_format = Format('application/png')
        response.outputs['spi_plot'].file = runner.get_output(result['plot_dir'],
                                                              path_filter=os.path.join('diagnostic', 'spi'),
                                                              name_filter="histplot",
                                                              output_format="png")
        response.outputs['spei_plot'].output_format = Format('application/png')
        response.outputs['spei_plot'].file = runner.get_output(result['plot_dir'],
                                                               path_filter=os.path.join('diagnostic', 'spei'),
                                                               name_filter="histplot",
                                                               output_format="png")

        response.outputs['spi_model'].output_format = FORMATS.NETCDF
        response.outputs['spi_model'].file = runner.get_output(result['work_dir'],
                                                               path_filter=os.path.join('diagnostic', 'spi'),
                                                               name_filter="CMPI5*spi*",
                                                               output_format="nc")

        response.outputs['spi_reference'].output_format = FORMATS.NETCDF
        response.outputs['spi_reference'].file = runner.get_output(result['work_dir'],
                                                                   path_filter=os.path.join('diagnostic', 'spi'),
                                                                   name_filter="OBS*spi*",
                                                                   output_format="nc")

        response.outputs['spei_model'].output_format = FORMATS.NETCDF
        response.outputs['spei_model'].file = runner.get_output(result['work_dir'],
                                                                path_filter=os.path.join('diagnostic', 'spei'),
                                                                name_filter="CMPI5*spei*",
                                                                output_format="nc")

        response.outputs['spei_reference'].output_format = FORMATS.NETCDF
        response.outputs['spei_reference'].file = runner.get_output(result['work_dir'],
                                                                    path_filter=os.path.join('diagnostic', 'spei'),
                                                                    name_filter="OBS*spei*",
                                                                    output_format="nc")
