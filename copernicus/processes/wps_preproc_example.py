import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.inout.literaltypes import make_allowedvalues
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from copernicus import runner, util
from copernicus.processes.utils import default_outputs, model_experiment_ensemble

LOGGER = logging.getLogger("PYWPS")


class PreprocessExample(Process):
    def __init__(self):
        inputs = [
            *model_experiment_ensemble(
                models=['EC-EARTH'],
                model_name='model1',
                experiments=['historical'],
                ensembles=['r2i1p1'],
                ensemble_name='ensemble1',
                start_end_year=(1850, 2005),
                start_end_defaults=(2000, 2005)
            ),
            *model_experiment_ensemble(
                models=['bcc-csm1-1'],
                model_name='model2',
                experiments=['historical'],
                ensembles=['r1i1p1'],
                ensemble_name='ensemble2',
                start_end_year=(1850, 2005),
                start_end_defaults=(2000, 2005)
            ),
            *model_experiment_ensemble(
                models=['MPI-ESM-LR'],
                model_name='model3',
                experiments=['historical'],
                ensembles=['r1i1p1'],
                ensemble_name='ensemble3',
                start_end_year=(1850, 2005),
                start_end_defaults=(2000, 2005)
            ),
            LiteralInput('extract_levels', 'Extraction levels',
                         abstract='Choose an extraction level for the preprocessor.',
                         data_type='float',
                         #allowed_values=make_allowedvalues([0.0, 110000.0]),
                         default=85000.0),
        ]
        outputs = [
            ComplexOutput('plot', 'Output plot',
                          abstract='Generated output plot of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[Format('image/png')]),
            ComplexOutput('data', 'Data',
                          abstract='Generated output data of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('archive', 'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(PreprocessExample, self).__init__(
            self._handler,
            identifier="preproc",
            title="Preprocessing Demo",
            version=runner.VERSION,
            abstract="Generates a plot for temperature using ESMValTool."
             " The default run uses the following CMIP5 data:"
             " project=CMIP5, experiment=historical, ensemble=r1i1p1, variable=ta, model=MPI-ESM-LR, time_frequency=mon",  # noqa
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata('Documentation',
                         'https://copernicus-wps-demo.readthedocs.io/en/latest/processes.html#pydemo',
                         role=util.WPS_ROLE_DOC),
                Metadata('Media',
                         util.diagdata_url() + '/pydemo/pydemo_thumbnail.png',
                         role=util.WPS_ROLE_MEDIA)
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True)

    def _handler(self, request, response):
        response.update_status("starting ...", 0)

        # build esgf search constraints
        constraints = dict(
            model1=request.inputs['model1'][0].data,
            ensemble1=request.inputs['ensemble1'][0].data,
            model2=request.inputs['model2'][0].data,
            ensemble2=request.inputs['ensemble2'][0].data,
            model3=request.inputs['model3'][0].data,
            ensemble3=request.inputs['ensemble3'][0].data,
            experiment=request.inputs['experiment'][0].data,
        )

        options = dict(
            extract_levels=request.inputs['extract_levels'][0].data
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='preproc',
            constraints=constraints,
            start_year=request.inputs['start_year'][0].data,
            end_year=request.inputs['end_year'][0].data,
            output_format='png',
            options=options
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

        if not result['success']:
            LOGGER.exception('esmvaltool failed!')
            response.update_status("exception occured: " + result['exception'], 100)
            return response
        
        try:
            self.get_outputs(result, response)
        except Exception as e:
            response.update_status("exception occured: " + str(e), 85)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(os.path.join(self.workdir, 'output'), 'diagnostic_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
        response.outputs['plot'].output_format = Format('application/png')
        response.outputs['plot'].file = runner.get_output(
            result['plot_dir'],
            path_filter=os.path.join('diagnostic1', 'script1'),
            name_filter="CMIP5*",
            output_format="png")

        response.outputs['data'].output_format = FORMATS.NETCDF
        response.outputs['data'].file = runner.get_output(
            result['plot_dir'],
            path_filter=os.path.join('diagnostic1', 'script1'),
            name_filter="CMIP5*",
            output_format="nc")