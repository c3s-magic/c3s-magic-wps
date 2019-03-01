from pywps import Process
from pywps import LiteralInput, LiteralOutput
from pywps import ComplexInput, ComplexOutput
from pywps import Format, FORMATS
from pywps.app.Common import Metadata

import logging
LOGGER = logging.getLogger("PYWPS")


def year_ranges(start_end_year, start_end_defaults):
    start_year, end_year = start_end_year
    default_start_year, default_end_year = start_end_defaults
    return (LiteralInput(
        'start_year',
        "Start year ({})".format(start_year),
        data_type='integer',
        abstract='Start year of model data.',
        default=default_start_year),
            LiteralInput(
                'end_year',
                'End year (till {})'.format(end_year),
                data_type='integer',
                abstract='End year of model data.',
                default=default_end_year))


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
                              start_end_year=(1850, 2005),
                              start_end_defaults=(1950, 2005)):
    return (LiteralInput(
        model_name.lower(),
        model_name,
        abstract='Choose a model like {}.'.format(models[0]),
        data_type='string',
        allowed_values=models,
        default=models[0],
        min_occurs=1,
        max_occurs=1),
            LiteralInput(
                experiment_name.lower(),
                experiment_name,
                abstract='Choose an experiment like {}.'.format(
                    experiments[0]),
                data_type='string',
                allowed_values=experiments,
                default=experiments[0]),
            LiteralInput(
                ensemble_name.lower(),
                ensemble_name,
                abstract='Choose an ensemble like {}.'.format(ensembles[0]),
                data_type='string',
                allowed_values=ensembles,
                default=ensembles[0]),
            *year_ranges(start_end_year, start_end_defaults))
