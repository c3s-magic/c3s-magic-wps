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

from copernicus.processes.utils import default_outputs, model_experiment_ensemble, year_ranges, outputs_from_plot_names


class ConsecDryDays(Process):
    def __init__(self):
        inputs = [
            *model_experiment_ensemble(
                models=['bcc-csm1-1-m', 'bcc-csm1-1'],
                experiments=['historical'],
                ensembles=['r1i1p1'],
                start_end_year=(1850, 2012),
                start_end_defaults=(2001, 2002)),
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
        self.plotlist = [
            'dryfreq',
            'drymax'
        ]
        outputs = [
            *outputs_from_plot_names(self.plotlist),
            ComplexOutput('data_drymax', 'Data Drymax',
                          abstract='Generated output data of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('data_dryfreq', 'Data DryFreq',
                          abstract='Generated output data of ESMValTool processing.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('archive', 'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
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
                         'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_consecdrydays.html',
                         role=util.WPS_ROLE_DOC),
                Metadata('Media',
                         util.diagdata_url() + '/consecdrydays/drydays.png',
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
            workdir=workdir,
            diag='consecdrydays',
            constraints=constraints,
            start_year=request.inputs['start_year'][0].data,
            end_year=request.inputs['end_year'][0].data,
	    options=options,
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
        response.outputs['archive'].file = runner.compress_output(os.path.join(self.workdir, 'output'), 'diagnostic_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        for plot in self.plotlist:
            key = '{}_plot'.format(plot.lower())
            response.outputs[key].output_format = Format('application/png')
            response.outputs[key].file = runner.get_output(
                result['plot_dir'],
                path_filter=os.path.join('dry_days', 'consecutive_dry_days'),
                name_filter="*{}".format(plot),
                output_format="png")

        response.outputs['data_drymax'].output_format = FORMATS.NETCDF
        response.outputs['data_drymax'].file = runner.get_output(
            result['work_dir'],
            path_filter=os.path.join('dry_days', 'consecutive_dry_days'),
            name_filter="*drymax",
            output_format="nc")

        response.outputs['data_dryfreq'].output_format = FORMATS.NETCDF
        response.outputs['data_dryfreq'].file = runner.get_output(
            result['work_dir'],
            path_filter=os.path.join('dry_days', 'consecutive_dry_days'),
            name_filter="*dryfreq",
            output_format="nc")