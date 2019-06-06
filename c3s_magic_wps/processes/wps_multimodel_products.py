import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS
from pywps.inout.literaltypes import AllowedValue
from pywps.validator.allowed_value import ALLOWEDVALUETYPE

from .utils import default_outputs, model_experiment_ensemble, year_ranges, outputs_from_plot_names

from .. import runner, util

LOGGER = logging.getLogger("PYWPS")


class MultimodelProducts(Process):
    def __init__(self):
        self.variables = ['tas']
        self.frequency = 'mon'

        inputs = [
            *model_experiment_ensemble(model='MPI-ESM-MR',
                                       experiment='rcp85',
                                       ensemble='r1i1p1',
                                       min_occurs=2,
                                       required_variables=self.variables,
                                       required_frequency=self.frequency),
            *year_ranges((1961, 1990), start_name='start_historical', end_name='end_historical'),
            *year_ranges((2006, 2099), start_name='start_projection', end_name='end_projection'),
            LiteralInput(
                'moninf',
                'First month month of the seasonal mean period',
                abstract="""First month of the seasonal mean period to be computed, if none the monthly anomalies
                            will be computed.""",
                data_type='string',
                allowed_values=['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 'null'],
                default='6'),
            LiteralInput(
                'monsup',
                'Last month month of the seasonal mean period',
                abstract="""Last month of the seasonal mean period to be computed, if none the monthly anomalies
                            will be computed.""",
                data_type='string',
                allowed_values=['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'],
                default='6'),
            LiteralInput(
                'agreement_threshold',
                'Agreement Threshold',
                abstract="""Threshold in percent for the minimum agreement
                            between models on the sign of the multi-model mean anomaly for the stipling to be
                            plotted.""",
                data_type='integer',
                allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=0, maxval=100),
                default=80),
            LiteralInput('running_mean',
                         'Running Mean',
                         abstract='Length of the window for which the running mean is computed.',
                         data_type='integer',
                         allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=1, maxval=365),
                         default=5),
            LiteralInput('time_series_plot',
                         'Time series plot',
                         abstract="""Either single or maxmin (plot the individual or the mean with shading between the
                                     max and min).""",
                         data_type='string',
                         allowed_values=['single', 'maxmin'],
                         default='single'),
        ]
        self.plotlist = [
            ('tas', [Format('image/png')]),
            ('Area', [Format('image/png')]),
        ]
        outputs = [
            *outputs_from_plot_names(self.plotlist),
            ComplexOutput('data',
                          'Data',
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
                Metadata('Media',
                         util.diagdata_url() + '/multimodel_products/bsc_anomaly_timeseries.png',
                         role=util.WPS_ROLE_MEDIA),
                Metadata(
                    'Model Selection',
                    """The Multimodel Products metric requires at least one model to be chosen, but multiple models
                    is supported. For each model choose a projection scenario (e.g. rcp26) and the relevant historical
                    experiment will be added by the WPS process. Also make sure to set the climatology and anomaly
                    start and end years correctly."""),
                Metadata('Estimated Calculation Time', '1 minute'),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True)

    def _handler(self, request, response):
        response.update_status("starting ...", 0)

        # build esgf search constraints
        constraints = dict(
            models=request.inputs['model'],
            ensembles=request.inputs['ensemble'],
            experiments=request.inputs['experiment'],
            start_historical=request.inputs['start_historical'][0].data,
            end_historical=request.inputs['end_historical'][0].data,
            start_projection=request.inputs['start_projection'][0].data,
            end_projection=request.inputs['end_projection'][0].data,
        )

        options = dict(
            moninf=request.inputs['moninf'][0].data,
            monsup=request.inputs['monsup'][0].data,
            agreement_threshold=int(request.inputs['agreement_threshold'][0].data),
            running_mean=int(request.inputs['running_mean'][0].data),
            time_series_plot=request.inputs['time_series_plot'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='multimodel_products',
            constraints=constraints,
            options=options,
            start_year=constraints['start_historical'],
            end_year=constraints['end_projection'],
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
            response.update_status("exception occured: " + result['exception'], 100)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(os.path.join(self.workdir, 'output'),
                                                                  'multimodel_products_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
        for plot, _ in self.plotlist:
            key = '{}_plot'.format(plot.lower())
            response.outputs[key].output_format = Format('application/png')
            response.outputs[key].file = runner.get_output(result['plot_dir'],
                                                           path_filter=os.path.join('anomaly_agreement', 'main'),
                                                           name_filter="{}*".format(plot),
                                                           output_format="png")

        response.outputs['data'].output_format = FORMATS.NETCDF
        response.outputs['data'].file = runner.get_output(result['work_dir'],
                                                          path_filter=os.path.join('anomaly_agreement', 'main'),
                                                          name_filter="tas*",
                                                          output_format="nc")
