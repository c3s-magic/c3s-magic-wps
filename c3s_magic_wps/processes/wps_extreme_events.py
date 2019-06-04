import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .. import runner, util
from .utils import default_outputs, model_experiment_ensemble, outputs_from_plot_names, year_ranges

LOGGER = logging.getLogger("PYWPS")


class ExtremeEvents(Process):
    def __init__(self):
        inputs = [
            *model_experiment_ensemble(model='MPI-ESM-MR', experiment='historical', ensemble='r1i1p1', min_occurs=2),
            *year_ranges((1981, 2000)),
            LiteralInput('ref_dataset',
                         'Reference Dataset',
                         abstract='Choose a reference dataset like ERA-Interim.',
                         data_type='string',
                         allowed_values=['ERA-Interim'],
                         default='ERA-Interim',
                         min_occurs=1,
                         max_occurs=1),
        ]
        self.plotlist = [
            ('Glecker', [Format('image/png')]),
            ('r95', [Format('image/png')]),
            ('rx5day', [Format('image/png')]),
            ('rx1day', [Format('image/png')]),
            ('cdd', [Format('image/png')]),
            ('fd', [Format('image/png')]),
            ('tr', [Format('image/png')]),
            ('txn', [Format('image/png')]),
            ('txx', [Format('image/png')]),
            ('tnn', [Format('image/png')]),
            ('tnx', [Format('image/png')]),
        ]

        outputs = [
            *outputs_from_plot_names(self.plotlist),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(ExtremeEvents, self).__init__(
            self._handler,
            identifier="extreme_events",
            title="Calculate extreme events",
            version=runner.VERSION,
            abstract="""
                Calculate indices for monitoring changes in extremes based on daily temperature
                and precipitation data. Producing Glecker and timeline plots of this as shown in
                the IPCC_AR5 report
            """,
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata(
                    'Documentation',
                    'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_extreme_events.html',
                    role=util.WPS_ROLE_DOC,
                ),
                Metadata('Estimated Calculation Time', '4 hours'),
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
            reference=request.inputs['ref_dataset'][0].data,
        )

        options = dict()

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=workdir,
            diag='extreme_events',
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
        response.outputs['archive'].file = runner.compress_output(os.path.join(workdir, 'output'),
                                                                  'extreme_events_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        response.update_status("collecting output ...", 80)
        for plot, _ in self.plotlist:
            key = '{}_plot'.format(plot.lower())
            response.outputs[key].output_format = Format('application/png')
            response.outputs[key].file = runner.get_output(result['plot_dir'],
                                                           path_filter=os.path.join('extreme_events', 'main'),
                                                           name_filter="{}*".format(plot),
                                                           output_format="png")
