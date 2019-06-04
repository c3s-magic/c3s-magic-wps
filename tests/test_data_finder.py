from c3s_magic_wps.processes.utils import DataFinder


def test_data_finder():
    finder = DataFinder.get_instance()

    print(finder.data)

    # print(json.dumps(self.data, indent=2), file=sys.stderr)

    models, experiments, ensembles = finder.get_model_experiment_ensemble(required_variables=['pr', 'tas'],
                                                                          required_frequency='mon')

    # print(models)
    # print(experiments)
    # print(ensembles)

    pruned = finder.get_pruned_tree(required_variables=['pr'], required_frequency='mon')

    # print ("tree!", self.data)
    print("pruned tree!", pruned)
