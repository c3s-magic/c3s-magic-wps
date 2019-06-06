import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .utils import default_outputs, year_ranges, model_experiment_ensemble, outputs_from_plot_names

from .. import runner, util

LOGGER = logging.getLogger("PYWPS")


class Toymodel(Process):
    def __init__(self):
        # more correctly the variable depends on the settings
        self.variables = ['psl', 'tas']
        self.frequency = 'mon'
        inputs = [
            *model_experiment_ensemble(model='ACCESS1-0',
                                       experiment='historical',
                                       ensemble='r1i1p1',
                                       max_occurs=1,
                                       required_variables=self.variables,
                                       required_frequency=self.frequency),
            *year_ranges((1999, 2001)),
            LiteralInput('variable',
                         'Variable',
                         abstract='Select the variable to simulate.',
                         data_type='string',
                         default='psl',
                         allowed_values=['psl', 'tas']),
            LiteralInput(
                'start_longitude',
                'Start longitude',
                abstract='Minimum longitude.',
                data_type='integer',
                default=-40,
            ),
            LiteralInput(
                'end_longitude',
                'End longitude',
                abstract='Maximum longitude.',
                data_type='integer',
                default=40,
            ),
            LiteralInput(
                'start_latitude',
                'Start latitude',
                abstract='Minimum latitude.',
                data_type='integer',
                default=30,
            ),
            LiteralInput(
                'end_latitude',
                'End latitude',
                abstract='Maximum latitude.',
                data_type='integer',
                default=50,
            ),
            LiteralInput(
                'beta',
                'Beta',
                abstract='User defined underdispersion (beta >= 0).',
                data_type='float',
                default=0.7,
            ),
            LiteralInput(
                'number_of_members',
                'Number of members',
                abstract='Number of members to be generated.',
                data_type='integer',
                default=2,
            ),
        ]
        # self.plotlist = [
        #     'TM90', 'NumberEvents', 'DurationEvents', 'LongBlockEvents', 'BlockEvents', 'ACN', 'CN', 'BI', 'MGI',
        #     'Z500', 'ExtraBlock', 'InstBlock'
        # ]
        outputs = [
            # *outputs_from_plot_names(self.plotlist),
            ComplexOutput('plot',
                          'Toy Model plot',
                          abstract='Generated synthetic model plt.',
                          as_reference=True,
                          supported_formats=[Format('image/jpeg')]),
            ComplexOutput('model',
                          'Toy Model',
                          abstract='Generated synthetic model.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(Toymodel, self).__init__(
            self._handler,
            identifier="toymodel",
            title="Toymodel",
            version=runner.VERSION,
            abstract="""The goal of this diagnostic is to simulate single-model ensembles from an observational dataset
                        to investigate the effect of observational uncertainty.""",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata(
                    'Documentation',
                    'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_toymodel.html',
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
            start_longitude=request.inputs['start_longitude'][0].data,
            end_longitude=request.inputs['end_longitude'][0].data,
            start_latitude=request.inputs['start_latitude'][0].data,
            end_latitude=request.inputs['end_latitude'][0].data,
            beta=request.inputs['beta'][0].data,
            number_of_members=request.inputs['number_of_members'][0].data,
            variable=request.inputs['variable'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        start_year = request.inputs['start_year'][0].data
        end_year = request.inputs['end_year'][0].data
        recipe_file, config_file = runner.generate_recipe(
            workdir=workdir,
            diag='toymodel',
            constraints=constraints,
            options=options,
            start_year=start_year,
            end_year=end_year,
            output_format='jpg',
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
        response.outputs['archive'].file = runner.compress_output(os.path.join(workdir, 'output'),
                                                                  'toymodel_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)

        response.outputs['plot'].output_format = Format('image/jpeg')
        response.outputs['plot'].file = runner.get_output(result['plot_dir'],
                                                          path_filter=os.path.join('toymodel', 'main'),
                                                          name_filter="synthetic*",
                                                          output_format="jpg")

        response.outputs['model'].output_format = FORMATS.NETCDF
        response.outputs['model'].file = runner.get_output(result['work_dir'],
                                                           path_filter=os.path.join('toymodel', 'main'),
                                                           name_filter="synthetic*",
                                                           output_format="nc")
