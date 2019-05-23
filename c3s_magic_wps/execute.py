import argparse
import requests


def execute(scheme, wps_service, port, process, models, experiments, ensembles, start_year=None, end_year=None):
    inputs = f'DataInputs='
    if models and experiments and ensembles:
        for model, experiment, ensemble in zip(models, experiments, ensembles):
            inputs += f'model={model};experiment={experiment};ensemble={ensemble};'

    if start_year:
        inputs += f'start_year={start_year};'
    if end_year:
        inputs += f'end_year={end_year}'

    query = f'{scheme}://{wps_service}:{port}/wps?service=wps&request=Execute&version=1.0.0&identifier={process}'
    query += f'&storeExecuteResponse=true&status=true&{inputs}'

    print(f'Executing query: {query}')
    response = requests.get(query)

    if response.status_code == requests.codes.ok:  # noqa
        print(f'The request was successfully submitted: {response.text}')
    else:
        print(f'The request failed!')
        response.raise_for_status()


def canary():
    parser = argparse.ArgumentParser(description="""Command line to interact with a WPS service.

                        Do not use this service in a production environment.
                        It's intended to be running in a test environment only!
                        """)

    subparsers = parser.add_subparsers(help='sub-command', dest='command')
    subparsers.required = True

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--wps-service', type=str, default='localhost', help='hostname of the wps service.')
    common.add_argument('--port', type=int, default=5000, help='port of the wps service.')
    common.add_argument('--scheme', type=str, default='http', help='scheme of the wps service.')

    execute_parser = subparsers.add_parser('execute', description='Execute a wps process', parents=[common])
    execute_parser.add_argument('process', type=str, help='The process to execute')
    execute_parser.add_argument('--model', type=str, nargs='*', help='The models to run the process on')
    execute_parser.add_argument('--experiment', type=str, nargs='*', help='The experiments to run the process on')
    execute_parser.add_argument('--ensemble', type=str, nargs='*', help='The ensembles to run the process on')
    execute_parser.add_argument('--start-year', type=int, required=False, help='The start year')
    execute_parser.add_argument('--end-year', type=int, required=False, help='The end year')

    args = parser.parse_args()

    print(args)
    execute(
        args.scheme,
        args.wps_service,
        args.port,
        args.process,
        args.model,
        args.experiment,
        args.ensemble,
        start_year=args.start_year,
        end_year=args.end_year,
    )
