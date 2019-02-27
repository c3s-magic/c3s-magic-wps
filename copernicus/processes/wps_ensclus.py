import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata
from pywps.response.status import WPS_STATUS

from copernicus import runner, util

from .utils import default_outputs, model_experiment_ensemble

LOGGER = logging.getLogger("PYWPS")


class EnsClus(Process):
    def __init__(self):
        inputs = [
            *model_experiment_ensemble(
                models=['Defaults'],
                experiments=['historical'],
                ensembles=['r1i1p1'],
                start_end_year=(1850, 2005),
                start_end_defaults=(1850, 2005)),
            LiteralInput(
                'area',
                'Area',
                abstract='Area',
                data_type='string',
                allowed_values=['Eu', 'EAT', 'PNA'],
                default='Eu'),
            LiteralInput(
                'extreme',
                'Extreme',
                abstract='Extreme',
                data_type='string',
                allowed_values=[
                    '60th_percentile', '75th_percentile', '90th_percentile',
                    'mean', 'maximum', 'std'
                ],
                default='75th_percentile'),
            LiteralInput(
                'numclus',
                'Number of Clusters',
                abstract='Numclus',
                data_type='string',
                allowed_values=['2', '3', '4'],
                default='3'),
            LiteralInput(
                'perc',
                'Percentage',
                abstract='Percentage of total Variance',
                data_type='string',
                allowed_values=['70', '80', '90'],
                default='80'),
        ]
        outputs = [
            *default_outputs(),
            ComplexOutput(
                'plot',
                'Output plot',
                abstract='Generated output plot of ESMValTool processing.',
                as_reference=True,
                supported_formats=[Format('image/eps')]),
            ComplexOutput(
                'data',
                'Data',
                abstract='Generated output data of ESMValTool processing.',
                as_reference=True,
                supported_formats=[FORMATS.NETCDF]),
            ComplexOutput(
                'statistics',
                'Statistics',
                abstract='Clustering Statictics',
                as_reference=True,
                supported_formats=[Format('text/plain')]),
            ComplexOutput(
                'archive',
                'Archive',
                abstract=
                'The complete output of the ESMValTool processing as an zip archive.',
                as_reference=True,
                supported_formats=[Format('application/zip')]),
        ]

        super(EnsClus, self).__init__(
            self._handler,
            identifier="ensclus",
            title="Recipe for sub-ensemble selection",
            version=runner.VERSION,
            abstract="Generates a plot for temperature using ESMValTool."
            " The default run uses the following CMIP5 data:"
            " project=CMIP5, experiment=historical, ensemble=r1i1p1, variable=ta, model=MPI-ESM-LR, time_frequency=mon",  # noqa
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
                Metadata(
                    'ESGF Testdata',
                    'https://esgf1.dkrz.de/thredds/catalog/esgcet/7/cmip5.output1.MPI-M.MPI-ESM-LR.historical.mon.atmos.Amon.r1i1p1.v20120315.html?dataset=cmip5.output1.MPI-M.MPI-ESM-LR.historical.mon.atmos.Amon.r1i1p1.v20120315.ta_Amon_MPI-ESM-LR_historical_r1i1p1_199001-199912.nc'
                ),  # noqa
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

        options = dict(
            area=request.inputs['area'][0].data,
            extreme=request.inputs['extreme'][0].data,
            numclus=request.inputs['numclus'][0].data,
            perc=request.inputs['perc'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='ensclus',
            constraints=constraints,
            start_year=request.inputs['start_year'][0].data,
            end_year=request.inputs['end_year'][0].data,
            output_format='png',
            options=options,
        )

        # recipe output
        response.outputs['recipe'].output_format = FORMATS.TEXT
        response.outputs['recipe'].file = recipe_file

        # run diag
        response.update_status("running diagnostic ...", 20)
        result = runner.run(recipe_file, config_file)

        logfile = result['logfile']
        work_dir = result['work_dir']
        plot_dir = result['plot_dir']

        # log output
        response.outputs['log'].output_format = FORMATS.TEXT
        response.outputs['log'].file = logfile

        response.outputs['success'].data = result['success']

        if not result['success']:
            LOGGER.exception('esmvaltool failed!')
            response.update_status("exception occured: " + result['exception'],
                                   100)
            response.status = WPS_STATUS.FAILED
            return response

        # result plot
        response.update_status("collecting output ...", 80)
        response.outputs['plot'].output_format = Format('application/eps')
        response.outputs['plot'].file = runner.get_output(
            plot_dir,
            path_filter=os.path.join('EnsClus', 'main'),
            name_filter="*",
            output_format="eps")

        response.outputs['data'].output_format = FORMATS.NETCDF
        response.outputs['data'].file = runner.get_output(
            work_dir,
            path_filter=os.path.join('EnsClus', 'main'),
            name_filter="ens*",
            output_format="nc")

        response.outputs['statistics'].output_format = FORMATS.TEXT
        response.outputs['statistics'].file = runner.get_output(
            work_dir,
            path_filter=os.path.join('EnsClus', 'main'),
            name_filter="statistics*",
            output_format="txt")

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(
            os.path.join(self.workdir, 'output'), 'diagnostic_result.zip')

        response.update_status("done.", 100)
        return response
