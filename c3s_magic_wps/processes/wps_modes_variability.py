import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from .utils import default_outputs, model_experiment_ensemble, year_ranges, outputs_from_plot_names

from .. import runner, util

LOGGER = logging.getLogger("PYWPS")


class ModesVariability(Process):
    def __init__(self):
        self.variables = ['psl']
        self.frequency = 'mon'

        inputs = [
            *model_experiment_ensemble(model='bcc-csm1-1',
                                       experiment='rcp85',
                                       ensemble='r1i1p1',
                                       max_occurs=1,
                                       required_variables=self.variables,
                                       required_frequency=self.frequency),
            *year_ranges((1971, 2000), start_name='start_historical', end_name='end_historical'),
            *year_ranges((2020, 2050), start_name='start_projection', end_name='end_projection'),
            LiteralInput('plot_type',
                         'Plot Type',
                         abstract='Plot type.',
                         data_type='string',
                         allowed_values=['polar', 'rectangular'],
                         default='polar'),
            LiteralInput('ncenters',
                         'Cluster Centers',
                         abstract='Choose a number of cluster centers.',
                         data_type='string',
                         allowed_values=['3', '4', '5'],
                         default='4'),
            LiteralInput('detrend_order',
                         'Detrend Order',
                         abstract='Choose a order of detrend.',
                         data_type='string',
                         allowed_values=['2', '1'],
                         default='2'),
            LiteralInput('cluster_method',
                         'Cluster Method',
                         abstract='Choose a clustering method.',
                         data_type='string',
                         allowed_values=['kmeans', 'hclust'],
                         default='kmeans'),
            LiteralInput('eofs',
                         'EOFs',
                         abstract='Calculate EOFs?',
                         data_type='string',
                         allowed_values=['True', 'False'],
                         default=True),
            LiteralInput(
                'frequency',
                'Frequency',
                abstract='Choose a frequency like JAN.',
                data_type='string',
                allowed_values=[
                    'JAN',
                    'FEB',
                    'MAR',
                    'APR',
                    'MAY',
                    'JUN',
                    'JUL',
                    'AUG',
                    'SEP',
                    'OCT',
                    'NOV',
                    'DEC',
                    'JJA',
                    'SON',
                    'DJF'  # 'MAM' <- does not work yet
                ],
                default='JJA'),
        ]
        self.plotlist = [
            ('Table_psl', [Format('image/png')]),
            ('psl_predicted_regimes', [Format('image/png')]),
            ('psl_observed_regimes', [Format('image/png')]),
        ]
        outputs = [
            *outputs_from_plot_names(self.plotlist),
            ComplexOutput('rmse',
                          'RMSE Data',
                          abstract='Generated output data of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('exp',
                          'EXP Data',
                          abstract='Generated output data of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('obs',
                          'OBS Data',
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

        super(ModesVariability, self).__init__(
            self._handler,
            identifier="modes_of_variability",
            title="Modes of variability",
            version=runner.VERSION,
            abstract="""Diagnostics showing the RMSE between the observed and
            modelled patterns of variability obtained through classification
            and their relative relative bias (percentage) in the frequency of
            occurrence and the persistence of each mode.""",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata(
                    'Documentation',
                    'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_modes_of_variability.html',  # noqa
                    role=util.WPS_ROLE_DOC),
                Metadata('Estimated Calculation Time', '30 seconds'),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True,
        )

    def _handler(self, request, response):
        response.update_status("starting ...", 0)

        # build esgf search constraints
        constraints = dict(model=request.inputs['model'][0].data,
                           experiment=request.inputs['experiment'][0].data,
                           ensemble=request.inputs['ensemble'][0].data,
                           start_year_historical=request.inputs['start_historical'][0].data,
                           end_year_historical=request.inputs['end_historical'][0].data,
                           start_year_projection=request.inputs['start_projection'][0].data,
                           end_year_projection=request.inputs['end_projection'][0].data)

        options = dict(
            plot_type=request.inputs['plot_type'][0].data,
            start_historical='{}-01-01'.format(request.inputs['start_historical'][0].data),
            end_historical='{}-12-31'.format(request.inputs['end_historical'][0].data),
            start_projection='{}-01-01'.format(request.inputs['start_projection'][0].data),
            end_projection='{}-12-31'.format(request.inputs['end_projection'][0].data),
            ncenters=int(request.inputs['ncenters'][0].data),
            detrend_order=int(request.inputs['detrend_order'][0].data),
            cluster_method=request.inputs['cluster_method'][0].data,
            eofs=request.inputs['eofs'][0].data,
            frequency=request.inputs['frequency'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='modes_of_variability',
            constraints=constraints,
            options=options,
            start_year=constraints['start_year_historical'],
            end_year=constraints['end_year_projection'],
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
            response.update_status("exception occured: " + result['exception'], 85)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(os.path.join(self.workdir, 'output'),
                                                                  'modes_of_variability_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
        for plot, _ in self.plotlist:
            key = '{}_plot'.format(plot.lower())
            response.outputs[key].output_format = Format('application/png')
            response.outputs[key].file = runner.get_output(result['plot_dir'],
                                                           path_filter=os.path.join('weather_regime', 'main'),
                                                           name_filter="*{}*".format(plot),
                                                           output_format="png")

        response.outputs['rmse'].output_format = FORMATS.NETCDF
        response.outputs['rmse'].file = runner.get_output(result['work_dir'],
                                                          path_filter=os.path.join('weather_regime', 'main'),
                                                          name_filter="*rmse*",
                                                          output_format="nc")

        response.outputs['exp'].output_format = FORMATS.NETCDF
        response.outputs['exp'].file = runner.get_output(result['work_dir'],
                                                         path_filter=os.path.join('weather_regime', 'main'),
                                                         name_filter="*exp*",
                                                         output_format="nc")

        response.outputs['obs'].output_format = FORMATS.NETCDF
        response.outputs['obs'].file = runner.get_output(result['work_dir'],
                                                         path_filter=os.path.join('weather_regime', 'main'),
                                                         name_filter="*obs*",
                                                         output_format="nc")
