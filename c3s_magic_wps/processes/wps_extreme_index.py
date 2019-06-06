import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS
from pywps.inout.literaltypes import AllowedValue
from pywps.validator.allowed_value import ALLOWEDVALUETYPE

from .utils import default_outputs, model_experiment_ensemble, year_ranges
from .utils import outputs_from_plot_names, outputs_from_data_names

from .. import runner, util

LOGGER = logging.getLogger("PYWPS")


class ExtremeIndex(Process):
    def __init__(self):
        self.variables = ['tasmax', 'tasmin', 'sfcWind', 'pr']
        self.frequency = 'day'

        inputs = [
            *model_experiment_ensemble(model='MPI-ESM-MR',
                                       experiment='rcp85',
                                       ensemble='r1i1p1',
                                       max_occurs=1,
                                       required_variables=self.variables,
                                       required_frequency=self.frequency),
            *year_ranges((1971, 2000), start_name='start_historical', end_name='end_historical'),
            *year_ranges((2020, 2040), start_name='start_projection', end_name='end_projection'),
            LiteralInput('running_mean',
                         'Running Mean',
                         abstract='Length of the window for which the running mean is computed.',
                         data_type='integer',
                         allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=1, maxval=365),
                         default=5),
            LiteralInput(
                'start_longitude',
                'Start longitude',
                abstract='Minimum longitude.',
                data_type='integer',
                default=-60,
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
                default=70,
            ),
        ]
        self.plotlist = [
            ('t10p', [Format('image/png')]),
            ('t90p', [Format('image/png')]),
            ('Wx', [Format('image/png')]),
            ('rx5day', [Format('image/png')]),
            ('cdd', [Format('image/png')]),
            ('combined', [Format('image/png')]),
        ]
        self.datalist = [
            ('t10p', [FORMATS.NETCDF]),
            ('t90p', [FORMATS.NETCDF]),
            ('Wx', [FORMATS.NETCDF]),
            ('rx5day', [FORMATS.NETCDF]),
            ('cdd', [FORMATS.NETCDF]),
            ('combined', [FORMATS.NETCDF]),
        ]
        outputs = [
            *outputs_from_plot_names(self.plotlist),
            *outputs_from_data_names(self.datalist),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(ExtremeIndex, self).__init__(
            self._handler,
            identifier="extreme_index",
            title="Combined Climate Extreme Index",
            version=runner.VERSION,
            abstract="""Metric showing extreme indices relevant to the insurance industry (heat, cold, wind, flood and
                        drought indices).""",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata(
                    'Documentation',
                    'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_combined_climate_extreme_index.html',  # noqa
                    role=util.WPS_ROLE_DOC),
                # Metadata('Media',
                #          util.diagdata_url() + '/risk_index/insurance_risk_indices.png',
                #          role=util.WPS_ROLE_MEDIA),
                Metadata('Estimated Calculation Time', '2 minutes'),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True)

    def _handler(self, request, response):
        response.update_status("starting ...", 0)

        # build esgf search constraints
        constraints = dict(model=request.inputs['model'][0].data,
                           ensemble=request.inputs['ensemble'][0].data,
                           experiment=request.inputs['experiment'][0].data,
                           start_year_historical=request.inputs['start_historical'][0].data,
                           end_year_historical=request.inputs['end_historical'][0].data,
                           start_year_projection=request.inputs['start_projection'][0].data,
                           end_year_projection=request.inputs['end_projection'][0].data)

        options = dict(
            running_mean=int(request.inputs['running_mean'][0].data),
            start_historical='{}-01-01'.format(request.inputs['start_historical'][0].data),
            end_historical='{}-12-31'.format(request.inputs['end_historical'][0].data),
            start_projection='{}-01-01'.format(request.inputs['start_projection'][0].data),
            end_projection='{}-12-31'.format(request.inputs['end_projection'][0].data),
            start_longitude=request.inputs['start_longitude'][0].data,
            end_longitude=request.inputs['end_longitude'][0].data,
            start_latitude=request.inputs['start_latitude'][0].data,
            end_latitude=request.inputs['end_latitude'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='extreme_index',
            constraints=constraints,
            options=options,
            start_year=request.inputs['start_historical'][0].data,
            end_year=request.inputs['end_projection'][0].data,
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
                self.get_outputs(result, constraints, response)
            except Exception as e:
                response.update_status("exception occured: " + str(e), 85)
                LOGGER.exception('Getting output failed: ' + str(e))
        else:
            LOGGER.exception('esmvaltool failed!')
            response.update_status("exception occured: " + result['exception'], 85)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(os.path.join(self.workdir, 'output'),
                                                                  'extreme_index_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, constraints, response):
        # result plot
        response.update_status("collecting output ...", 80)
        # output of individual indices
        for idx in ['t10p', 't90p', 'Wx', 'rx5day', 'cdd']:
            plotkey = '{}_plot'.format(idx.lower())
            datakey = '{}_data'.format(idx.lower())
            response.outputs[plotkey].output_format = Format('application/png')
            response.outputs[plotkey].file = runner.get_output(result['plot_dir'],
                                                               path_filter=os.path.join('extreme_index', 'metric'),
                                                               name_filter="*{}_*".format(idx),
                                                               output_format="png")
            response.outputs[datakey].output_format = FORMATS.NETCDF
            response.outputs[datakey].file = runner.get_output(result['work_dir'],
                                                               path_filter=os.path.join('extreme_index', 'metric'),
                                                               name_filter="*{}_risk_insurance_index*".format(idx),
                                                               output_format="nc")
        # output of combined indices
        response.outputs['combined_plot'].output_format = Format('application/png')
        response.outputs['combined_plot'].file = runner.get_output(result['plot_dir'],
                                                                   path_filter=os.path.join('extreme_index', 'metric'),
                                                                   name_filter="CombinedIndices*",
                                                                   output_format="png")
        response.outputs['combined_data'].output_format = FORMATS.NETCDF
        response.outputs['combined_data'].file = runner.get_output(result['work_dir'],
                                                                   path_filter=os.path.join('extreme_index', 'metric'),
                                                                   name_filter="_*",
                                                                   output_format="nc")
