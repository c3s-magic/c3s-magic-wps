import os
import tempfile
import glob
import json
import sys
import copy

import logging

LOGGER = logging.getLogger("PYWPS")

from pywps import configuration


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

def _get_children_of(a_dict):
    if 'contents' in a_dict:
        return a_dict['contents'].copy()
    else:
        return []

def _has_chilren(a_dict):
    if 'contents' in a_dict:
        #make sure we return a boolean
        return len(a_dict['contents']) != 0
    return False
                                                     
class DataFinder():
    def __init__(self, archive_base = None):
        if not archive_base:
            self.archive_base = configuration.get_config_value("data", "archive_root")
        else:
            self.archive_base = archive_base
 
        LOGGER.debug("searching for model data in the following folder: `%s`", self.archive_base)

        if not os.path.isdir(self.archive_base):
            raise Exception('cmip5 folder not found at %s' % self.archive_base)

        #use root instead of the actual filename to
        #not needlessly reveal the location of the files on disk
        self.data = _dir_entry(self.archive_base, 'root')

    # Obtain a pruned tree with models/experiments/ensembles containing the required variables and frequency only
    def get_pruned_tree(self, required_variables=[], required_frequency='mon'):
        result = copy.deepcopy(self.data)

        for organization in _get_children_of(result):
            for model in _get_children_of(organization):
                for experiment in _get_children_of(model):
                    for frequency in _get_children_of(experiment):
                        if frequency['name'] == required_frequency:
                            for mip in _get_children_of(frequency):
                                for realm in _get_children_of(mip):
                                    for ensemble in _get_children_of(realm):
                                        
                                        available_variables = []
                                        for variable in _get_children_of(ensemble):
                                            available_variables.append(variable['name'])

                                        LOGGER.debug('required_variables ' + str(required_variables))
                                        LOGGER.debug('available variables ' + str(available_variables))

                                        if not all(required_variable in available_variables for required_variable in required_variables):
                                            #LOGGER.debug('removing %s from %s' %(ensemble, model))
                                            realm['contents'].remove(ensemble)
                                        else:
                                            #remove unneeded information for the tree to reduce size
                                            del ensemble['contents']
                                            
                                    if not _has_chilren(realm):
                                        mip['contents'].remove(realm)
                                if not _has_chilren(mip):
                                    frequency['contents'].remove(mip)
                            if not _has_chilren(frequency):
                                experiment['contents'].remove(frequency)
                        else:
                            experiment['contents'].remove(frequency)
                    if not _has_chilren(experiment):
                        model['contents'].remove(experiment)
                if not _has_chilren(model):
                    organization['contents'].remove(model)
            if not _has_chilren(organization):
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

    