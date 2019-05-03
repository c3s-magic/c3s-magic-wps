import json
import logging
import os
import re

from pywps import (FORMATS, ComplexInput, ComplexOutput, Format, LiteralInput, LiteralOutput, Process)
from pywps.app.Common import Metadata

from ...util import static_directory

LOGGER = logging.getLogger("PYWPS")


def year_ranges(start_end_year, start_end_defaults, start_name='start_year', end_name='end_year'):
    start_year, end_year = start_end_year
    if start_end_defaults is not None:
        default_start_year, default_end_year = start_end_defaults
    else:
        default_start_year = start_year
        default_end_year = end_year

    start_long_name = start_name.replace('_', ' ').capitalize()
    end_long_name = end_name.replace('_', ' ').capitalize()
    return [
        LiteralInput(start_name,
                     "{} ({})".format(start_long_name, start_year),
                     data_type='integer',
                     abstract='{} of model data.'.format(start_long_name),
                     default=default_start_year),
        LiteralInput(end_name,
                     "{} (till {})".format(end_long_name, end_year),
                     data_type='integer',
                     abstract='{} of model data.'.format(end_long_name),
                     default=default_end_year)
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


def parse_model_lists():
    json_file = os.path.join(static_directory(), 'available_models.json')
    with open(json_file, 'r') as f:
        json_dict = json.load(f)

    key = lambda key: [int(i) for i in re.findall('([0-9]+)', key)]  # Sort by the numbers in the ensemble
    model_experiment_ensemble.available_models = sorted(list(json_dict['facets']['model'].keys()))
    model_experiment_ensemble.available_experiments = sorted(list(json_dict['facets']['experiment'].keys()))
    model_experiment_ensemble.available_ensembles = sorted(list(json_dict['facets']['ensemble'].keys()), key=key)


def model_experiment_ensemble(model_name='Model',
                              experiment_name='Experiment',
                              ensemble_name='Ensemble',
                              start_end_year=None,
                              start_end_defaults=None):

    if not hasattr(model_experiment_ensemble, 'available_models'):
        parse_model_lists()

    model_long_name = model_name.replace('_', ' ').capitalize()
    experiment_long_name = experiment_name.replace('_', ' ').capitalize()
    ensemble_long_name = ensemble_name.replace('_', ' ').capitalize()
    inputs = [
        LiteralInput(model_name.lower(),
                     model_long_name,
                     abstract='Choose a model like {}.'.format(model_experiment_ensemble.available_models[0]),
                     data_type='string',
                     allowed_values=model_experiment_ensemble.available_models,
                     default=model_experiment_ensemble.available_models[0],
                     min_occurs=1,
                     max_occurs=1),
        LiteralInput(experiment_name.lower(),
                     experiment_long_name,
                     abstract='Choose an experiment like {}.'.format(
                         model_experiment_ensemble.available_experiments[0]),
                     data_type='string',
                     allowed_values=model_experiment_ensemble.available_experiments,
                     default=model_experiment_ensemble.available_experiments[0]),
        LiteralInput(ensemble_name.lower(),
                     ensemble_long_name,
                     abstract='Choose an ensemble like {}.'.format(model_experiment_ensemble.available_ensembles[0]),
                     data_type='string',
                     allowed_values=model_experiment_ensemble.available_ensembles,
                     default=model_experiment_ensemble.available_ensembles[0]),
    ]
    if start_end_year is not None:
        inputs.extend(year_ranges(start_end_year, start_end_defaults))

    return inputs


def outputs_from_plot_names(plotlist):
    plots = []
    for plot in plotlist:
        plots.append(
            ComplexOutput('{}_plot'.format(plot.lower()),
                          '{} plot'.format(plot),
                          abstract='Generated {} plot of ESMValTool processing.'.format(plot),
                          as_reference=True,
                          supported_formats=[Format('image/png')]))
    return plots
