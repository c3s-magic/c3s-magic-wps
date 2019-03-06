import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from copernicus.processes.utils import default_outputs, model_experiment_ensemble, year_ranges

from .. import runner, util

LOGGER = logging.getLogger("PYWPS")


class ModesVariability(Process):
    def __init__(self):
        inputs = [
            *model_experiment_ensemble(
                models=['bcc-csm1-1'],
                model_name='Model_historical',
                experiments=['historical'],
                experiment_name='Experiment_historical',
                ensembles=['r1i1p1'],
                ensemble_name='Ensemble_historical'),
            *year_ranges((1850, 2005), (1971, 2000),
                         start_name='start_historical',
                         end_name='end_historical'),
            *model_experiment_ensemble(
                models=['bcc-csm1-1'],
                model_name='Model_projection',
                experiments=['historical'],
                experiment_name='Experiment_projection',
                ensembles=['r1i1p1'],
                ensemble_name='Ensemble_projection'),
            *year_ranges((2006, 2050), (2020, 2050),
                         start_name='start_projection',
                         end_name='end_projection'),
            LiteralInput(
                'region',
                'Region',
                abstract='Choose a region like Polar',
                data_type='string',
                allowed_values=['Polar', 'North-Atlantic'],
                default='North-Atlantic'),
            LiteralInput(
                'ncenters',
                'Cluster Centers',
                abstract='Choose a number of cluster centers.',
                data_type='string',
                allowed_values=['3', '4', '5'],
                default='4'),
            LiteralInput(
                'detrend_order',
                'Detrend Order',
                abstract='Choose a order of detrend.',
                data_type='string',
                allowed_values=['2', '1'],
                default='2'),
            LiteralInput(
                'cluster_method',
                'Cluster Method',
                abstract='Choose a clustering method.',
                data_type='string',
                allowed_values=['kmeans', 'complete'],
                default='kmeans'),
            LiteralInput(
                'eofs',
                'EOFs',
                abstract='Calculate EOFs?',
                data_type='boolean',
                default=True),
            LiteralInput(
                'frequency',
                'Frequency',
                abstract='Choose a frequency like JAN.',
                data_type='string',
                allowed_values=[
                    'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG',
                    'SEP', 'OCT', 'NOV', 'DEC', 'JJA', 'SON', 'MAM', 'DJF'
                ],
                default='JJA'),
        ]
        outputs = [
            ComplexOutput(
                'archive',
                'Archive',
                abstract=
                'The complete output of the ESMValTool processing as an zip archive.',
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
                    'https://copernicus-wps-demo.readthedocs.io/en/latest/processes.html#pydemo',
                    role=util.WPS_ROLE_DOC),
                Metadata(
                    'Media',
                    util.diagdata_url() + '/pydemo/pydemo_thumbnail.png',
                    role=util.WPS_ROLE_MEDIA),
            ],
            inputs=inputs,
            outputs=outputs,
            status_supported=True,
            store_supported=True)

    def _handler(self, request, response):
        response.update_status("starting ...", 0)

        # build esgf search constraints
        constraints = dict(
            model_historical=request.inputs['model_historical'][0].data,
            experiment_historical=request.inputs['experiment_historical'][0].data,
            ensemble_historical=request.inputs['ensemble_historical'][0].data,
            start_year_historical = request.inputs['start_year_historical'][0].data,
            end_year_historical = request.inputs['end_year_historical'][0].data,
            model_projection=request.inputs['model_projection'][0].data,
            experiment_projection=request.inputs['experiment_projection'][0].data,
            ensemble_projection=request.inputs['ensemble_projection'][0].data,
            start_year_projection = request.inputs['start_year_projection'][0].data,
            end_year_projection = request.inputs['end_year_projection'][0].data
        )

        options = dict(
            region=request.inputs['region'][0].data,
            start_historical='{}-01-01'.format(request.inputs['start_historical'][0].data),
            end_historical='{}-12-31'.format(request.inputs['end_historical'][0].data),
            start_projection='{}-01-01'.format(request.inputs['start_projection'][0].data),
            end_projection='{}-12-31'.format(request.inputs['end_projection'][0].data),
            ncenters=int(request.inputs['ncenters'][0].data),
            detrend_order=int(request.inputs['detrend_order'][0].data),
            cluster_method=request.inputs['cluster_method'][0].data,
            EOFS=request.inputs['eofs'][0].data,
            frequency=request.inputs['frequency'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='miles_blocking',
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

        if not result['success']:
            LOGGER.exception('esmvaltool failed!')
            response.update_status("exception occured: " + result['exception'],
                                   100)
            return response

        # subdir = os.path.join(constraints['model'], constraints['experiment'],
        #                       constraints['ensemble'], "{}_{}".format(
        #                           start_year,
        #                           end_year), options['season'], 'Block')
        subdir = ""
        try:
            self.get_outputs(result, subdir, response)
        except Exception as e:
            response.update_status("exception occured: " + str(e), 85)

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(
            os.path.join(self.workdir, 'output'), 'diagnostic_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, subdir, response):
        # result plot
        pass