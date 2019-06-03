import os
import tempfile
import glob
import json
import sys
import copy

import logging

from pywps import configuration

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


def _get_children_of(a_dict):
    if 'contents' in a_dict:
        return a_dict['contents'].copy()
    else:
        return []


def _has_chilren(a_dict):
    if 'contents' in a_dict:
        # make sure we return a boolean
        return len(a_dict['contents']) != 0
    return False


class DataFinder():
    __instance = None

    @staticmethod
    def get_instance():
        if DataFinder.__instance is None:
            DataFinder.__instance = DataFinder()

        return DataFinder.__instance

    def __init__(self):
        self.archive_base = os.environ['CMIP_DATA_ROOT']

        LOGGER.debug("searching for model data in the following folder: `%s`", self.archive_base)

        if not os.path.isdir(self.archive_base):
            raise Exception('cmip5 folder not found at %s' % self.archive_base)

        # use root instead of the actual filename to
        # not needlessly reveal the location of the files on disk
        self.data = _dir_entry(self.archive_base, 'root')

    # Obtain a pruned tree with models/experiments/ensembles containing the required variables and frequency only
    # Note, it cannot handle variables in multiple realms as of yet
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

                                        if not all(required_variable in available_variables
                                                   for required_variable in required_variables):
                                            # LOGGER.debug('removing %s from %s' %(ensemble, model))
                                            realm['contents'].remove(ensemble)
                                        else:
                                            # remove unneeded information for the tree to reduce size
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

        for organization in _get_children_of(self.data):
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

                                        if all(required_variable in available_variables
                                               for required_variable in required_variables):
                                            models.add(model['name'])
                                            experiments.add(experiment['name'])
                                            ensembles.add(ensemble['name'])

        return (list(models), list(experiments), list(ensembles))
