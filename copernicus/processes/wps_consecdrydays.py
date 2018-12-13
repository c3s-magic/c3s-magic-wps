import os

from pywps import Process
from pywps import LiteralInput, LiteralOutput
from pywps import ComplexInput, ComplexOutput
from pywps import Format, FORMATS
from pywps.app.Common import Metadata

from copernicus import runner
from copernicus import util

import logging
LOGGER = logging.getLogger("PYWPS")


class ConsecDryDays(Process):
    def __init__(self):
        inputs = [
            LiteralInput('model', 'Model',
                         abstract='Choose a model like MPI-ESM-LR.',
                         data_type='string',
                         allowed_values=['bcc-csm1-1-m', 'bcc-csm1-1'],
                         default='bcc-csm1-1-m',
			 min_occurs=1,
			 max_occurs=1),
            LiteralInput('experiment', 'Experiment',
                         abstract='Choose an experiment like historical.',
                         data_type='string',
                         allowed_values=['historical'],
                         default='historical'),
            LiteralInput('ensemble', 'Ensemble',
                         abstract='Choose an ensemble like r1i1p1.',
                         data_type='string',
                         allowed_values=['r1i1p1'],
                         default='r1i1p1'),
            LiteralInput('start_year', 'Start year (from 1850)', data_type='integer',
                         abstract='Start year of model data.',
                         default="2001"),
            LiteralInput('end_year', 'End year (till 2012)', data_type='integer',
                         abstract='End year of model data.',
                         default="2002"),
            LiteralInput('frlim', 'frlim',
                         abstract='Frlim',
                         data_type='string',
                         allowed_values=['2.5', '5', '10'],
                         default='5'),
            LiteralInput('plim', 'plim',
                         abstract='Plim',
                         data_type='string',
                         allowed_values=['0.5', '1', '2'],
                         default='1'),
        ]
        outputs = [
            ComplexOutput('recipe', 'recipe',
                          abstract='ESMValTool recipe used for processing.',
                          as_reference=True,
                          supported_formats=[Format('text/plain')]),
            ComplexOutput('log', 'Log File',
                          abstract='Log File of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[Format('text/plain')]),
#            ComplexOutput('plot', 'Output plot',
#                          abstract='Generated output plot of ESMValTool processing.',
#                          as_reference=True,
#                          supported_formats=[Format('image/png')]),
            ComplexOutput('drymax', 'Data Drymax',
                          abstract='Generated output data of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('dryfreq', 'Data DryFreq',
                          abstract='Generated output data of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('archive', 'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
        ]

        super(ConsecDryDays, self).__init__(
            self._handler,
            identifier="consecdrydays",
            title="Calculating number of dry days",
            version=runner.VERSION,
            abstract="Calculating number of dry days",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata('Documentation',
                         'https://copernicus-wps-demo.readthedocs.io/en/latest/processes.html#pydemo',
                         role=util.WPS_ROLE_DOC),
                Metadata('Media',
                         util.diagdata_url() + '/pydemo/pydemo_thumbnail.png',
                         role=util.WPS_ROLE_MEDIA),
                Metadata('ESGF Testdata',
                         'https://esgf1.dkrz.de/thredds/catalog/esgcet/7/cmip5.output1.MPI-M.MPI-ESM-LR.historical.mon.atmos.Amon.r1i1p1.v20120315.html?dataset=cmip5.output1.MPI-M.MPI-ESM-LR.historical.mon.atmos.Amon.r1i1p1.v20120315.ta_Amon_MPI-ESM-LR_historical_r1i1p1_199001-199912.nc'),  # noqa
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
            time_frequency='day',
            cmor_table='day',
            ensemble=request.inputs['ensemble'][0].data,
        )

        #build options
        options = dict(
            frlim=request.inputs['frlim'][0].data,
            plim=request.inputs['plim'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=self.workdir,
            diag='consecdrydays',
            constraints=constraints,
            start_year=request.inputs['start_year'][0].data,
            end_year=request.inputs['end_year'][0].data,
	    options=options,
            output_format='png',
        )

        # run diag
        response.update_status("running diagnostic ...", 20)
        logfile, plot_dir, work_dir, run_dir = runner.run(recipe_file, config_file)

        # recipe output
        response.outputs['recipe'].output_format = FORMATS.TEXT
        response.outputs['recipe'].file = recipe_file

        # log output
        response.outputs['log'].output_format = FORMATS.TEXT
        response.outputs['log'].file = logfile

        # result plot
        response.update_status("collecting output ...", 80)
#        response.outputs['plot'].output_format = Format('application/png')
#        response.outputs['plot'].file = runner.get_output(
#            plot_dir,
#            path_filter=os.path.join('diagnostic1', 'script1'),
#            name_filter="CMIP5*",
#            output_format="png")

        response.outputs['drymax'].output_format = FORMATS.NETCDF
        response.outputs['drymax'].file = runner.get_output(
            work_dir,
            path_filter=os.path.join('diagnostic1', 'script1'),
            name_filter="CMIP5*drymax",
            output_format="nc")

        response.outputs['dryfreq'].output_format = FORMATS.NETCDF
        response.outputs['dryfreq'].file = runner.get_output(
            work_dir,
            path_filter=os.path.join('diagnostic1', 'script1'),
            name_filter="CMIP5*dryfreq",
            output_format="nc")

        response.update_status("creating archive of diagnostic result ...", 90)

        response.outputs['archive'].output_format = Format('application/zip')
        response.outputs['archive'].file = runner.compress_output(os.path.join(self.workdir, 'output'), 'diagnostic_result.zip')

        response.update_status("done.", 100)
        return response
