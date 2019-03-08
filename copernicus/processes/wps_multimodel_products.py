import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS
from pywps.inout.literaltypes import AllowedValue
from pywps.validator.allowed_value import ALLOWEDVALUETYPE

from copernicus.processes.utils import default_outputs, model_experiment_ensemble, year_ranges, outputs_from_plot_names

from .. import runner, util

LOGGER = logging.getLogger("PYWPS")


class MultimodelProducts(Process):
    def __init__(self):
        inputs = [
            LiteralInput(
                'moninf',
                'First month month of the seasonal mean period',
                abstract='The first month of the seasonal mean period to be computed, if none the monthly anomalies will be computed.',
                data_type='string',
                allowed_values=['1', '2', '3', '4','5', '6', '7', '8', '9', '10', '11', '12', 'null'],
                default='6'),
            LiteralInput(
                'monsup',
                'Last month month of the seasonal mean period',
                abstract='the last month of the seasonal mean period to be computed, if none the monthly anomalies will be computed.',
                data_type='string',
                allowed_values=['1', '2', '3', '4','5', '6', '7', '8', '9', '10', '11', '12'],
                default='6'),
            LiteralInput(
                'agreement_threshold',
                'Agreement Threshold',
                abstract='Integer between 0 and 100 indicating the threshold in percent for the minimum agreement between models on the sign of the multi-model mean anomaly for the stipling to be plotted.',
                data_type='integer',
                allowed_values=[i for i in range(0,101)],
                default=80),
            LiteralInput(
                'running_mean',
                'Running Mean',
                abstract='integer indictating the length of the window for the running mean to be computed.',
                data_type='integer',
                allowed_values=AllowedValue(
                    allowed_type=ALLOWEDVALUETYPE.RANGE,
                    minval=1,
                    maxval=365
                ),
                default=5),
        ]
        self.plotlist = [
            'tas',
            'Area'
        ]
        outputs = [
            *outputs_from_plot_names(self.plotlist),
            ComplexOutput('data', 'Data',
                          abstract='Generated output data of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput(
                'archive',
                'Archive',
                abstract=
                'The complete output of the ESMValTool processing as an zip archive.',
                as_reference=True,
                supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(MultimodelProducts, self).__init__(
            self._handler,
            identifier="multimodel_products",
            title="Generic multi-model products",
            version=runner.VERSION,
            abstract="""For the 'generic multi-model diagnostic' the ensemble
                mean anomaly, and the ensemble variance and agreement are
                calculated. The results are shown as maps and time series.""",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata(
                    'Documentation',
                    'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_multimodel_products.html',
                    role=util.WPS_ROLE_DOC),
                Metadata(
                    'Media',
                    util.diagdata_url() + '/multimodel_products/bsc_anomaly_timeseries.png',
                    role=util.WPS_ROLE_MEDIA),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True)

    def _handler(self, request, response):
        response.update_status("starting ...", 0)

        # build esgf search constraints
        constraints = dict()

        options = dict(
            moninf=request.inputs['moninf'][0].data,
            monsup=request.inputs['monsup'][0].data,
            agreement_threshold=int(request.inputs['agreement_threshold'][0].data),
            running_mean=int(request.inputs['running_mean'][0].data),
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='multimodel_products_wp5',
            constraints=constraints,
            options=options,
            start_year=1961,
            end_year=2099,
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

        if not result['success']:
            LOGGER.exception('esmvaltool failed!')
            response.update_status("exception occured: " + result['exception'],
                                   100)
            return response

        try:
            self.get_outputs(result, response)
        except Exception as e:
            response.update_status("exception occured: " + str(e), 85)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(
            os.path.join(self.workdir, 'output'), 'diagnostic_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
        for plot in self.plotlist:
            key = '{}_plot'.format(plot.lower())
            response.outputs[key].output_format = Format('application/png')
            response.outputs[key].file = runner.get_output(
                result['plot_dir'],
                path_filter=os.path.join('anomaly_agreement', 'main'),
                name_filter="{}*".format(plot),
                output_format="png")

        response.outputs['data'].output_format = FORMATS.NETCDF
        response.outputs['data'].file = runner.get_output(
            result['work_dir'],
            path_filter=os.path.join('anomaly_agreement', 'main'),
            name_filter="tas*",
            output_format="nc")