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

                                                     
class DataFinder():
    def __init__(self, archive_base):
        self.archive_base = archive_base or '/data'
 
        #use root instead of the actual filename to
        #not needlessly reveal the location of the files on disk
        self.data = _dir_entry(archive_base, 'root')
      

    # Obtain a pruned tree with models/experiments/ensembles containing the required variables and frequency only
    def get_pruned_tree(self, required_variables=[], required_frequency='mon'):
        result = copy.deepcopy(self.data)

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

                                        LOGGER.debug('required_variables ' + str(required_variables))
                                        LOGGER.debug('available variables ' + str(available_variables))

                                        if not all(required_variable in available_variables for required_variable in required_variables):
                                            LOGGER.debug('removing %s from %s' %(ensemble, model))
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
    def get_model_experiment_ensemble(self, required_variables=[], required_frequency='mon'):
        models = set()
        experiments = set()
        ensembles = set()

        for organization in self.data['contents']:
            for model in organization['contents']:
                for experiment in model['contents']:
                    for frequency in experiment['contents']:
                        if frequency['name'] == required_frequency:
                            for mip in frequency['contents']:
                                for realm in mip['contents']:
                                    for ensemble in realm['contents']:
                                        available_variables = []
                                        for variable in ensemble['contents']:
                                            available_variables.append(variable['name'])

                                        LOGGER.debug('required_variables ' + str(required_variables))
                                        LOGGER.debug('available variables ' + str(available_variables))

                                        if all(required_variable in available_variables for required_variable in required_variables):
                                            models.add(model['name'])
                                            experiments.add(experiment['name'])
                                            ensembles.add(ensemble['name'])
        
        return (list(models), list(experiments), list(ensembles))
         


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    finder = DataFinder(sys.argv[1])

    print(finder.data)

    #print(json.dumps(self.data, indent=2), file=sys.stderr)

    models, experiments, ensembles = finder.get_model_experiment_ensemble(required_variables=['pr', 'tas'], required_frequency='mon')

    print (models)
    print (experiments)
    print (ensembles)

    pruned = finder.get_pruned_tree(required_variables=['pr'], required_frequency='mon')

    #print ("tree!", self.data)
    print ("pruned tree!", pruned)

    
