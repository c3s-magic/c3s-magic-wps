import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .. import runner, util
from .utils import default_outputs, model_experiment_ensemble, outputs_from_plot_names, year_ranges

LOGGER = logging.getLogger("PYWPS")


class ZMNAM(Process):
    def __init__(self):
        self.variables = ['zg']
        self.frequency = 'day'
        inputs = [
            *model_experiment_ensemble(model='MPI-ESM-MR',
                                       experiment='historical',
                                       ensemble='r1i1p1',
                                       max_occurs=1,
                                       required_variables=self.variables,
                                       required_frequency=self.frequency),
            *year_ranges((1979, 2005)),
        ]
        self.pressure_levels = [5000, 25000, 50000, 100000]
        self.plotlist = [("{}Pa_mo_reg".format(i), [Format('image/png')]) for i in self.pressure_levels]
        self.plotlist.extend([("{}Pa_da_pdf".format(i), [Format('image/png')]) for i in self.pressure_levels])
        self.plotlist.extend([("{}Pa_mo_ts".format(i), [Format('image/png')]) for i in self.pressure_levels])
        outputs = [
            *outputs_from_plot_names(self.plotlist),
            ComplexOutput('regr_map',
                          'Regr Map Data',
                          abstract='Generated output data of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('eofs',
                          'EOF Data',
                          abstract='Generated output data of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('pc_mo',
                          'PC Mo Data',
                          abstract='Generated output data of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('pc_da',
                          'PC Da Data',
                          abstract='Generated output data of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(ZMNAM, self).__init__(
            self._handler,
            identifier="zmnam",
            title="Stratosphere-troposphere coupling and annular modes indices (ZMNAM)",
            version=runner.VERSION,
            abstract="Stratosphere-troposphere coupling and annular modes indices (ZMNAM)",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata(
                    'Documentation',
                    'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_zmnam.html',
                    role=util.WPS_ROLE_DOC,
                ),
                Metadata('Estimated Calculation Time', '3 minutes'),
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

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=workdir,
            diag='zmnam',
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
        for plot, _ in self.plotlist:
            key = '{}_plot'.format(plot.lower())
            response.outputs[key].output_format = Format('application/png')
            response.outputs[key].file = runner.get_output(result['plot_dir'],
                                                           path_filter=os.path.join('zmnam', 'main'),
                                                           name_filter="*_{}".format(plot),
                                                           output_format="png")

        response.outputs['regr_map'].output_format = FORMATS.NETCDF
        response.outputs['regr_map'].file = runner.get_output(result['work_dir'],
                                                              path_filter=os.path.join('zmnam', 'main'),
                                                              name_filter="*regr_map*",
                                                              output_format="nc")

        response.outputs['eofs'].output_format = FORMATS.NETCDF
        response.outputs['eofs'].file = runner.get_output(result['work_dir'],
                                                          path_filter=os.path.join('zmnam', 'main'),
                                                          name_filter="*eofs*",
                                                          output_format="nc")

        response.outputs['pc_mo'].output_format = FORMATS.NETCDF
        response.outputs['pc_mo'].file = runner.get_output(result['work_dir'],
                                                           path_filter=os.path.join('zmnam', 'main'),
                                                           name_filter="*pc_mo*",
                                                           output_format="nc")

        response.outputs['pc_da'].output_format = FORMATS.NETCDF
        response.outputs['pc_da'].file = runner.get_output(result['work_dir'],
                                                           path_filter=os.path.join('zmnam', 'main'),
                                                           name_filter="*pc_da*",
                                                           output_format="nc")
