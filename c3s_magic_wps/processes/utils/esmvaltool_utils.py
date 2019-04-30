from pywps import Process
from pywps import LiteralInput, LiteralOutput
from pywps import ComplexInput, ComplexOutput
from pywps import Format, FORMATS
from pywps.app.Common import Metadata

import logging
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
        LiteralInput(
            start_name,
            "{} ({})".format(start_long_name, start_year),
            data_type='integer',
            abstract='{} of model data.'.format(start_long_name),
            default=default_start_year),
        LiteralInput(
            end_name,
            "{} (till {})".format(end_long_name, end_year),
            data_type='integer',
            abstract='{} of model data.'.format(end_long_name),
            default=default_end_year)
    ]


def default_outputs():
    return (
        LiteralOutput(
            'success',
            'Success',
            abstract=
            'True if the metric has been successfully calculated. If false please check the log files',
            data_type='string'),
        ComplexOutput(
            'recipe',
            'recipe',
            abstract='ESMValTool recipe used for processing.',
            as_reference=True,
            supported_formats=[Format('text/plain')]),
        ComplexOutput(
            'log',
            'Log File',
            abstract='Log File of ESMValTool processing.',
            as_reference=True,
            supported_formats=[Format('text/plain')]),
        ComplexOutput(
            'debug_log',
            'ESMValTool Debug File',
            abstract='Debug Log File of ESMValTool processing.',
            as_reference=True,
            supported_formats=[Format('text/plain')]),
    )


def model_experiment_ensemble(models=['MPI-ESM-LR'],
                              model_name='Model',
                              experiments=['historical'],
                              experiment_name='Experiment',
                              ensembles=['r1i1p1'],
                              ensemble_name='Ensemble',
                              start_end_year=None,
                              start_end_defaults=None):
    model_long_name = model_name.replace('_', ' ').capitalize()
    experiment_long_name = model_name.replace('_', ' ').capitalize()
    ensemble_long_name = model_name.replace('_', ' ').capitalize()
    inputs = [
        LiteralInput(
            model_name.lower(),
            model_long_name,
            abstract='Choose a model like {}.'.format(models[0]),
            data_type='string',
            allowed_values=models,
            default=models[0],
            min_occurs=1,
            max_occurs=1),
        LiteralInput(
            experiment_name.lower(),
            experiment_long_name,
            abstract='Choose an experiment like {}.'.format(experiments[0]),
            data_type='string',
            allowed_values=experiments,
            default=experiments[0]),
        LiteralInput(
            ensemble_name.lower(),
            ensemble_long_name,
            abstract='Choose an ensemble like {}.'.format(ensembles[0]),
            data_type='string',
            allowed_values=ensembles,
            default=ensembles[0]),
    ]
    if start_end_year is not None:
        inputs.extend(year_ranges(start_end_year, start_end_defaults))

    return inputs


def outputs_from_plot_names(plotlist):
    plots = []
    for plot in plotlist:
        plots.append(
            ComplexOutput(
                '{}_plot'.format(plot.lower()),
                '{} plot'.format(plot),
                abstract='Generated {} plot of ESMValTool processing.'.format(
                    plot),
                as_reference=True,
                supported_formats=[Format('image/png')]))
    return plots