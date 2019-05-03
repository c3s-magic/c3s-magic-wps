import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .. import runner, util
from .utils import default_outputs, model_experiment_ensemble, year_ranges

LOGGER = logging.getLogger("PYWPS")


class CVDP(Process):
    def __init__(self):
        inputs = [
            *model_experiment_ensemble(
                start_end_year=(1850, 2005),
                start_end_defaults=(2000, 2002),
            ),
        ]
        outputs = [
            # ComplexOutput(
            #     'plot',
            #     'Output plot',
            #     abstract='Generated output plot of ESMValTool processing.',
            #     as_reference=True,
            #     supported_formats=[Format('image/png')]),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(CVDP,
              self).__init__(self._handler,
                             identifier="cvdp",
                             title="NCAR CVDPackage",
                             version=runner.VERSION,
                             abstract="Run the NCAR CVDPackage",
                             metadata=[
                                 Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                                 Metadata('Documentation',
                                          'https://copernicus-wps-demo.readthedocs.io/en/latest/processes.html#pydemo',
                                          role=util.WPS_ROLE_DOC),
                                 Metadata('Media',
                                          util.diagdata_url() + '/pydemo/pydemo_thumbnail.png',
                                          role=util.WPS_ROLE_MEDIA),
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
            time_frequency='mon',
            cmor_table='Amon',
            ensemble=request.inputs['ensemble'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=workdir,
            diag='cvdp',
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
                                                                  'diagnostic_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
        # response.outputs['plot'].output_format = Format('application/png')
        # response.outputs['plot'].file = runner.get_output(
        #     result['work_dir'], # Yes, it's in the work dir
        #     path_filter=os.path.join('diagnostic1', 'cvdp'),
        #     name_filter="pr.mean.ann",
        #     output_format="png")
