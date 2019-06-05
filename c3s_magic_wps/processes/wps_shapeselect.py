import logging
import os

from pywps import FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process
from pywps.app.Common import Metadata

from .. import runner, util
from .utils import default_outputs, model_experiment_ensemble, outputs_from_plot_names, year_ranges

LOGGER = logging.getLogger("PYWPS")


class ShapeSelect(Process):
    def __init__(self):
        self.variables = ['tas', 'pr']
        self.frequency = 'mon'
        inputs = [
            *model_experiment_ensemble(model='EC-EARTH',
                                       experiment='historical',
                                       ensemble='r1i1p1',
                                       max_occurs=1,
                                       required_variables=self.variables,
                                       required_frequency=self.frequency),
            *year_ranges((1990, 1999)),
            LiteralInput('shape',
                         'Shape',
                         abstract='Shape of the area',
                         data_type='string',
                         allowed_values=['MotalaStrom', 'Elbe', 'multicatchment', 'testfile', 'Thames'],
                         default='MotalaStrom'),
            LiteralInput(
                'weighting_method',
                'Weighting method',
                abstract="""The preferred weighting method: mean_inside - mean of all
                        grid points inside polygon or representative - one point inside or close
                        to the polygon is used to represent the complete area.""",
                data_type='string',
                allowed_values=['mean_inside', 'representative'],
                default='mean_inside'),
        ]
        outputs = [
            ComplexOutput('data',
                          'Data',
                          abstract='Generated NetCDF file with precipitation for the selected area.',
                          as_reference=True,
                          supported_formats=[FORMATS.NETCDF]),
            ComplexOutput('xlsx_data',
                          'XLSX Data',
                          abstract='Generated excel file with precipitation for the selected area',
                          as_reference=True,
                          supported_formats=[Format('application/vnd.ms-excel')]),
            ComplexOutput('archive',
                          'Archive',
                          abstract='The complete output of the ESMValTool processing as an zip archive.',
                          as_reference=True,
                          supported_formats=[Format('application/zip')]),
            *default_outputs(),
        ]

        super(ShapeSelect, self).__init__(
            self._handler,
            identifier="shapefile_selection",
            title="Shapefile selection",
            version=runner.VERSION,
            abstract="""Metric showing selected gridded data within a user
                        defined polygon shapefile and outputting as NetCDF
                        or csv file.""",
            metadata=[
                Metadata('ESMValTool', 'http://www.esmvaltool.org/'),
                Metadata('Documentation',
                         'https://esmvaltool.readthedocs.io/en/version2_development/recipes/recipe_shapeselect.html',
                         role=util.WPS_ROLE_DOC),
                # Metadata('Media',
                #          util.diagdata_url() + '/shapefile_selection/OBS_CRU_reanaly_1_T2Ms_tas_1990-1994.png',
                #          role=util.WPS_ROLE_MEDIA),
                Metadata('Estimated Calculation Time', '10 seconds'),
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
            cmor_table='Amon',
            experiment=request.inputs['experiment'][0].data,
            ensemble=request.inputs['ensemble'][0].data,
        )

        options = dict(
            shape=request.inputs['shape'][0].data,
            weighting_method=request.inputs['weighting_method'][0].data,
        )

        # generate recipe
        response.update_status("generate recipe ...", 10)
        recipe_file, config_file = runner.generate_recipe(
            workdir=workdir,
            diag='shapeselect',
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
        response.outputs['archive'].file = runner.compress_output(os.path.join(self.workdir, 'output'),
                                                                  'shapeselect_result.zip')

        response.update_status("done.", 100)
        return response

    def get_outputs(self, result, response):
        # result plot
        response.update_status("collecting output ...", 80)
        response.outputs['data'].output_format = Format('application/png')
        response.outputs['data'].file = runner.get_output(result['work_dir'],
                                                          path_filter=os.path.join('diagnostic1', 'script1'),
                                                          name_filter="CMIP5*",
                                                          output_format="nc")

        response.outputs['xlsx_data'].output_format = Format('application/vnd.ms-excel')
        response.outputs['xlsx_data'].file = runner.get_output(result['work_dir'],
                                                               path_filter=os.path.join('diagnostic1', 'script1'),
                                                               name_filter="CMIP5*",
                                                               output_format="xlsx")
