import json
import logging
import os
import re

from pywps import (FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process)
from pywps.app.Common import Metadata
from pywps.inout.literaltypes import AllowedValue
from pywps.app.exceptions import ProcessError
from pywps.validator.allowed_value import ALLOWEDVALUETYPE

from ...util import static_directory

from .data_finder import DataFinder

LOGGER = logging.getLogger("PYWPS")


def year_ranges(start_end_defaults, start_name='start_year', end_name='end_year', start_year=1850, end_year=2100):
    default_start_year, default_end_year = start_end_defaults

    start_long_name = start_name.replace('_', ' ').capitalize()
    end_long_name = end_name.replace('_', ' ').capitalize()
    return [
        LiteralInput(start_name,
                     "{}".format(start_long_name),
                     data_type='integer',
                     abstract=('{} of model data. Valid minimum value is {} in case of historical,'
                               ' and 2005 in case of rcp experiments.'.format(start_long_name, start_year)),
                     default=default_start_year,
                     allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=start_year,
                                                 maxval=end_year)),
        LiteralInput(end_name,
                     "{}".format(end_long_name),
                     data_type='integer',
                     abstract=('{} of model data. Valid maximum value is 2005 in case of historical,'
                               ' and {} in case of rcp experiments.'.format(end_long_name, end_year)),
                     default=default_end_year,
                     allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=start_year,
                                                 maxval=end_year))
    ]


# for now uses valid ranges from ERA-Interim only
def reference_year_ranges(default_start_reference, default_end_reference, end_year=2018):
    return [
        LiteralInput("start_reference",
                     "Start reference",
                     data_type='integer',
                     abstract='Start year of reference period. Valid minimum value is 1979.',
                     default=default_start_reference,
                     allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=1979, maxval=end_year)),
        LiteralInput("end_reference",
                     "End Reference",
                     data_type='integer',
                     abstract='End year of reference period. Valid maximum value is {}.'.format(end_year),
                     default=default_end_reference,
                     allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=1979, maxval=end_year))
    ]


def historic_projection_year_ranges(default_start_historical, default_end_historical,
                                    default_start_projection, default_end_projection):

    return [
        LiteralInput("start_historical",
                     "Start historical year",
                     data_type='integer',
                     abstract='Start historical year of model data. Valid minimum value is 1850.',
                     default=default_start_historical,
                     allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=1850, maxval=2005)),
        LiteralInput("end_historical",
                     "End historical year",
                     data_type='integer',
                     abstract='End historical year of model data. Valid maximum value is 2005.',
                     default=default_end_historical,
                     allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=1850, maxval=2005)),
        LiteralInput("start_projection",
                     "Start projection year",
                     data_type='integer',
                     abstract='Start projection year of model data. Valid minimum value is 2005.',
                     default=default_start_projection,
                     allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=2005, maxval=2100)),
        LiteralInput("end_projection",
                     "End projection year",
                     data_type='integer',
                     abstract='End projection year of model data. Valid maximum value is 2100.',
                     default=default_end_projection,
                     allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=2005, maxval=2100))

    ]


def region(default_start_longitude=0, default_end_longitude=360, default_start_latitude=-90, default_end_latitude=90):
    return [
        LiteralInput(
            'start_longitude',
            'Start longitude',
            abstract='Minimum longitude. Range usually from -180 to 180.',
            data_type='integer',
            default=default_start_longitude,
            allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=-360, maxval=360)),
        LiteralInput(
            'end_longitude',
            'End longitude',
            abstract='Maximum longitude. Range usually from -180 to 180.',
            data_type='integer',
            default=default_end_longitude,
            allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=-360, maxval=360)),
        LiteralInput(
            'start_latitude',
            'Start latitude',
            abstract='Minimum latitude. Valid range from -90 to 90.',
            data_type='integer',
            default=default_start_latitude,
            allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=-90, maxval=90)),
        LiteralInput(
            'end_latitude',
            'End latitude',
            abstract='Maximum latitude. Valid range from -90 to 90.',
            data_type='integer',
            default=default_end_latitude,
            allowed_values=AllowedValue(allowed_type=ALLOWEDVALUETYPE.RANGE, minval=-90, maxval=90)),
    ]


def default_outputs():
    return (
        LiteralOutput('success',
                      'Success',
                      abstract="""True if the metric has been successfully calculated.
                        If false please check the log files""",
                      data_type='string'),
        ComplexOutput('recipe',
                      'recipe',
                      abstract='ESMValTool recipe used for processing.',
                      as_reference=True,
                      supported_formats=[Format('text/plain')]),
        ComplexOutput('log',
                      'Log File',
                      abstract='Log File of ESMValTool processing.',
                      as_reference=True,
                      supported_formats=[Format('text/plain')]),
        ComplexOutput('debug_log',
                      'ESMValTool Debug File',
                      abstract='Debug Log File of ESMValTool processing.',
                      as_reference=True,
                      supported_formats=[Format('text/plain')]),
    )


def ensemble_comp(key):
    return [int(i) for i in re.findall('([0-9]+)', key)]  # Sort by the numbers in the ensemble


def parse_model_lists():
    json_file = os.path.join(static_directory(), 'available_models.json')
    with open(json_file, 'r') as f:
        json_dict = json.load(f)

    model_experiment_ensemble.available_models = sorted(
        [s.replace('.', '-') for s in json_dict['facets']['model'].keys()], key=str.lower)
    model_experiment_ensemble.available_experiments = sorted(list(json_dict['facets']['experiment'].keys()))
    model_experiment_ensemble.available_ensembles = sorted(list(json_dict['facets']['ensemble'].keys()),
                                                           key=ensemble_comp)


def model_experiment_ensemble(model: str,
                              experiment: str,
                              ensemble: str,
                              model_name: str = 'Model',
                              experiment_name: str = 'Experiment',
                              ensemble_name: str = 'Ensemble',
                              min_occurs=1,
                              max_occurs=150,
                              required_variables=[],
                              required_frequency='mon'):
    # if not hasattr(model_experiment_ensemble, 'available_models'):
    #     parse_model_lists()

    finder = DataFinder.get_instance()
    available_models, available_experiments, available_ensembles = finder.get_model_experiment_ensemble(
        required_variables=required_variables, required_frequency=required_frequency)

    available_models = sorted(available_models, key=str.lower)
    available_experiments = sorted(available_experiments)
    available_ensembles = sorted(available_ensembles, key=ensemble_comp)

    if not available_models:
        available_models = ['None']

    if not available_ensembles:
        available_ensembles = ['None']

    if not available_experiments:
        available_experiments = ['None']

    model_long_name = model_name.replace('_', ' ').capitalize()
    experiment_long_name = experiment_name.replace('_', ' ').capitalize()
    ensemble_long_name = ensemble_name.replace('_', ' ').capitalize()

    default_model = model
    if default_model not in available_models:
        default_model = available_models[0]

    default_ensemble = ensemble
    if default_ensemble not in available_ensembles:
        default_ensemble = available_ensembles[0]

    default_experiment = experiment
    if default_experiment not in available_experiments:
        default_experiment = available_experiments[0]

    inputs = [
        LiteralInput(model_name.lower(),
                     model_long_name,
                     abstract='Choose a model',
                     data_type='string',
                     allowed_values=available_models,
                     default=default_model,
                     min_occurs=min_occurs,
                     max_occurs=max_occurs),
        LiteralInput(experiment_name.lower(),
                     experiment_long_name,
                     abstract='Choose an experiment',
                     data_type='string',
                     allowed_values=available_experiments,
                     default=default_experiment,
                     min_occurs=min_occurs,
                     max_occurs=max_occurs),
        LiteralInput(ensemble_name.lower(),
                     ensemble_long_name,
                     abstract='Choose an ensemble',
                     data_type='string',
                     allowed_values=available_ensembles,
                     default=default_ensemble,
                     min_occurs=min_occurs,
                     max_occurs=max_occurs),
    ]

    return inputs


def outputs_from_plot_names(plotlist):
    plots = []
    for plot, plot_formats in plotlist:
        plots.append(
            ComplexOutput('{}_plot'.format(plot.lower()),
                          '{} plot'.format(plot),
                          abstract='Generated {} plot of ESMValTool processing.'.format(plot),
                          as_reference=True,
                          supported_formats=plot_formats))
    return plots


def outputs_from_data_names(datalist):
    data_outputs = []
    for data_output, file_formats in datalist:
        data_outputs.append(
            ComplexOutput('{}_data'.format(data_output.lower()),
                          '{} data'.format(data_output),
                          abstract='Generated output {} data of ESMValTool processing..'.format(data_output),
                          as_reference=True,
                          supported_formats=file_formats))
    return data_outputs

# check for illegal combinations of contraints such as duplicate entries an uneven length values


def check_constraints(constraints):
    LOGGER.debug('Checking contraints: %s', constraints)
    if not 'models' in constraints:
        raise ProcessError("No models found in input")

    if not 'experiments' in constraints:
        raise ProcessError("No experiment found in input")

    if not 'ensembles' in constraints:
        raise ProcessError("No ensembles found in input")

    length = len(constraints['models'])

    LOGGER.debug('Number of models: %d', length)

    if len(constraints['experiments']) != length:
        raise ProcessError("Not the same number of experiments selected as models")

    if len(constraints['ensembles']) != length:
        raise ProcessError("Not the same number of ensembles selected as models")

    for i in range(length):
        for j in range(i + 1, length):
            if (constraints['models'][i].data == constraints['models'][j].data
                and constraints['experiments'][i].data == constraints['experiments'][j].data
                    and constraints['ensembles'][i].data == constraints['ensembles'][j].data):
                raise ProcessError("Duplicate entry for %s %s %s. Please use unique entries for datasets" %
                                   (constraints['models'][i].data,
                                    constraints['experiments'][i].data,
                                    constraints['ensembles'][i].data))
