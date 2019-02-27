import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .utils import default_outputs, model_experiment_ensemble

from .. import runner
from .. import util

import logging
LOGGER = logging.getLogger("PYWPS")


class Perfmetrics(Process):
    def __init__(self):
        inputs = [
            *model_experiment_ensemble(
                models=['MPI-ESM-LR', 'MPI-ESM-MR'],
                experiments=['historical', 'rcp26', 'rcp45', 'rcp85'],
                ensembles=['r1i1p1', 'r2i1p1', 'r3i1p1'],
                start_end_year=(1850, 2005),
                start_end_defaults=(2000, 2001)
            ),
        ]
        outputs = [
            *default_outputs(),
            ComplexOutput('output', 'Output plot',
                          abstract='Generated output plot of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[Format('application/pdf')]),
        ]

        super(Perfmetrics, self).__init__(
            self._handler,
            identifier="perfmetrics",
            title="Performance metrics",
            version=runner.VERSION,
            abstract="Creates a performance metrics report comparing models using ESMValTool. "
            " The goal is to create a standard namelist for the calculation of performance metrics to quantify "
            " the ability of the models to reproduce the climatological mean annual cycle for selected "
            " Essential Climate Variables (ECVs) plus some additional corresponding diagnostics "
            " and plots to better understand and interpret the results. "
            " The namelist can be used to calculate performance metrics at different vertical "
            " levels (e.g., 5, 30, 200, 850 hPa as in Gleckler et al., 2008) and in four "
            " regions (global, tropics 20N-20S, northern extratropics 20-90N, southern extratropics 20-90S). "
            " As an additional reference, we consider the Righi et al. (2015) paper.",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata('Documentation',
                         'https://copernicus-wps-demo.readthedocs.io/en/latest/processes.html#perfmetrics',
                         role=util.WPS_ROLE_DOC),
                Metadata('Media',
                         util.diagdata_url() + '/perfmetrics/Portait.png',
                         role=util.WPS_ROLE_MEDIA),
                Metadata('Diagnostic Description',
                         util.diagdata_url() + '/perfmetrics/description.md',
                         role=util.MAGIC_ROLE_DOC),
                Metadata('Diagnostic Metadata',
                         util.diagdata_url() + '/perfmetrics/perfmetrics.yml',
                         role=util.MAGIC_ROLE_METADATA),
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
            time_frequency='mon',
            cmor_table='Amon',
            ensemble=request.inputs['ensemble'][0].data,
        )

        # generate recipy
        response.update_status("generate recipy ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='perfmetrics',
            constraints=constraints,
            start_year=request.inputs['start_year'][0].data,
            end_year=request.inputs['end_year'][0].data,
            output_format='pdf'
        )

        # recipe output
        response.outputs['recipe'].output_format = FORMATS.TEXT
        response.outputs['recipe'].file = recipe_file

        # run diag
        response.update_status("running diagnostic ...", 20)
        result = runner.run(recipe_file, config_file)
        logfile = result['logfile']
        work_dir = result['work_dir']

        # log output
        response.outputs['log'].output_format = FORMATS.TEXT
        response.outputs['log'].file = logfile

        response.outputs['success'].data = result['success']

        if not result['success']:
            LOGGER.exception('esmvaltool failed!')
            response.update_status("exception occured: " + result['exception'], 100)
            response.status = WPS_STATUS.FAILED
            return response

        # result plot
        response.update_status("collect output plot ...", 90)
        response.outputs['output'].output_format = Format('application/pdf')
        response.outputs['output'].file = runner.get_output(
            work_dir,
            path_filter=os.path.join('ta850', 'cycle'),
            name_filter="ta_cycle_monthlyclim__Glob",
            output_format="pdf")
        response.update_status("done.", 100)
        return response
