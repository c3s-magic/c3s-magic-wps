import os
import tempfile
import glob
import json
import sys
import copy

import logging

LOGGER = logging.getLogger("PYWPS")


# Builds up a tree of folders with their contentaining folders
# Not unlike the output of the "tree -J" command in linux
def _dir_entry(path, name):
        result = dict()
        result['name'] = name
      
        contents = []
        for dir in os.listdir(path):
            subdir = os.path.join(path, dir)
            if (os.path.isdir(subdir)):
                contents.append(_dir_entry(subdir, dir))

        if len(contents) > 0:
            result['contents'] = contents

        return result


# Obtain a list of all valid models, experiments, and esemble members for the wps.
def _get_model_experiment_ensemble(data_tree, required_variables=[], required_frequency='mon'):
    models = set()
    experiments = set()
    ensembles = set()

    for organization in data_tree['contents']:
        for model in organization['contents']:
            for experiment in model['contents']:
                for frequency in experiment['contents']:
                    if frequency['name'] == required_frequency:
                        for mip in frequency['contents']:
                            for realm in mip['contents']:
                                for ensemble in realm['contents']:
                                    for version in ensemble['contents']:
                                        available_variables = []
                                        for variable in version['contents']:
                                            available_variables.append(variable['name'])

                                        print ('matching')
                                        #print (model, experiment, ensemble)
                                        print ('required_variables', required_variables)
                                        print ('available variables', available_variables)

                                        if all(required_variable in available_variables for required_variable in required_variables):
                                            models.add(model['name'])
                                            experiments.add(experiment['name'])
                                            ensembles.add(ensemble['name'])
    
    return (list(models), list(experiments), list(ensembles))


# Obtain a pruned tree with models/experiments/ensembles containing the required variables and frequency only
def _get_pruned_tree(data_tree, required_variables=[], required_frequency='mon'):
    result = copy.deepcopy(data_tree)

    for organization in result['contents'].copy():
        for model in organization['contents'].copy():
            for experiment in model['contents'].copy():
                for frequency in experiment['contents'].copy():
                    if frequency['name'] == required_frequency:
                        for mip in frequency['contents'].copy():
                            for realm in mip['contents'].copy():
                                for ensemble in realm['contents'].copy():
                                    
                                    available_variables = []
                                    for variable in ensemble['contents']:
                                        available_variables.append(variable['name'])

                                    # print ('matching')
                                    # print ('ensemble', ensemble)

                                    # print ('required_variables', required_variables)
                                    # print ('available variables', available_variables)

                                    if not all(required_variable in available_variables for required_variable in required_variables):
                                        print('removing', ensemble, 'from', model)
                                        realm['contents'].remove(ensemble)
                                if not realm['contents']:
                                    mip['contents'].remove(realm)
                            if not mip['contents']:
                                frequency['contents'].remove(mip)
                        if not frequency['contents']:
                            experiment['contents'].remove(frequency)
                    else:
                        experiment['contents'].remove(frequency)
                if not experiment['contents']:
                    model['contents'].remove(experiment)
            if not model['contents']:
                organization['contents'].remove(model)
        if not organization['contents']:
            result['contents'].remove(organization)
    return result

# Obtain a list of all valid models, experiments, and esemble members for the wps.
def _get_model_experiment_ensemble(data_tree, required_variables=[], required_frequency='mon'):
    models = set()
    experiments = set()
    ensembles = set()

    for organization in data_tree['contents']:
        for model in organization['contents']:
            for experiment in model['contents']:
                for frequency in experiment['contents']:
                    if frequency['name'] is required_frequency:
                        for mip in frequency['contents']:
                            for realm in mip['contents']:
                                for ensemble in realm['contents']:
                                    available_variables = []
                                    for variable in ensemble['contents']:
                                        available_variables.append(variable['name'])

                                    print ('matching')
                                    #print (model, experiment, ensemble)
                                    print ('required_variables', required_variables)
                                    print ('available variables', available_variables)

                                    if all(required_variable in available_variables for required_variable in required_variables):
                                        models.add(model['name'])
                                        experiments.add(experiment['name'])
                                        ensembles.add(ensemble['name'])
    
    return (list(models), list(experiments), list(ensembles))
                                                                

class DataFinder():
    def __init__(self, archive_base):
        self.archive_base = archive_base or '/data'
 
        #use root instead of the actual filename to
        #not needlessly reveal the location of the files on disk
        self.data = _dir_entry(archive_base, 'root')

        #print(self.data)

        #print(json.dumps(self.data, indent=2), file=sys.stderr)

        models, experiments, ensembles = _get_model_experiment_ensemble(self.data, required_variables=['zg'], required_frequency='day')

        print (models)
        print (experiments)
        print (ensembles)

        pruned = _get_pruned_tree(self.data, required_variables=['zg'], required_frequency='day')

        #print ("tree!", self.data)
        print ("pruned tree!", pruned)


if __name__ == "__main__":
    DataFinder(sys.argv[1])
    