import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .. import runner, util
from .utils import default_outputs, model_experiment_ensemble, outputs_from_plot_names, year_ranges

LOGGER = logging.getLogger("PYWPS")


class QuantileBias(Process):
    def __init__(self):
        self.variables = ['pr']
        self.frequency = 'mon'

        inputs = [
            *model_experiment_ensemble(model='MPI-ESM-P',
                                       experiment='historical',
                                       ensemble='r1i1p1',
                                       max_occurs=1,
                                       required_variables=self.variables,
                                       required_frequency=self.frequency),
            *year_ranges((1997, 1997)),
            LiteralInput('ref_dataset',
                         'Reference Dataset',
                         abstract='Choose a reference dataset like GPCP-SG.',
                         data_type='string',
                         allowed_values=['GPCP-SG'],
                         default='GPCP-SG',
                         min_occurs=1,
                         max_occurs=1),
            LiteralInput('perc_lev',
                         'Quantile',
                         abstract='Quantile in percentage (%).',
                         data_type='integer',
                         default=75),
        ]

        outputs = [
            ComplexOutput('model',
                          'Model Quantile Data',
                          abstract='Generated output data of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as a zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(QuantileBias, self).__init__(
            self._handler,
            identifier="quantile_bias",
            title="Quantile Bias",
            version=runner.VERSION,
            abstract="""Diagnostic showing the quantile bias between models and a reference dataset.""",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata(
                    'Documentation',
                    'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_quantilebias.html',
                    role=util.WPS_ROLE_DOC,
                ),
                Metadata('Estimated Calculation Time', '1 Minute'),
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
            reference=request.inputs['ref_dataset'][0].data,
        )

        options = dict(perc_lev=request.inputs['perc_lev'][0].data)

        # generate recipe
        response.update_status("generate recipe ...", 10)
        start_year = request.inputs['start_year'][0].data
        end_year = request.inputs['end_year'][0].data
        recipe_file, config_file = runner.generate_recipe(
            workdir=workdir,
            diag='quantilebias',
            constraints=constraints,
            options=options,
            start_year=start_year,
            end_year=end_year,
            output_format='svg',
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
                self.get_outputs(constraints['model'], result, response)
            except Exception as e:
                response.update_status("exception occured: " + str(e), 85)
        else:
            LOGGER.exception('esmvaltool failed!')
            response.update_status("exception occured: " + result['exception'], 85)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(os.path.join(workdir, 'output'),
                                                                  'quantilebias_result.zip')
        response.update_status("done.", 100)
        return response

    def get_outputs(self, model, result, response):
        # result plot
        response.update_status("collecting output ...", 80)

        response.outputs['model'].output_format = FORMATS.NETCDF
        response.outputs['model'].file = runner.get_output(result['work_dir'],
                                                           path_filter=os.path.join('quantilebias', 'main'),
                                                           name_filter="{}*".format(model),
                                                           output_format="nc")
