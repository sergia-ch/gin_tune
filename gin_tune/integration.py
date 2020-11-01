from copy import deepcopy
import gin
from ray import tune
from functools import partial

from gin_tune.tune_funcs import OVERRIDE_ATTR, FUNCS
from gin_tune.tune_funcs import choice, grid_search, sample_from

PREFIX = 'gin_tune'
GIN_CONFIG_ATTR = '_gin_config'


@gin.configurable
def gin_tune_config(**kwargs):
    """Get tune config from gin config."""
    config = kwargs

    # loop over config rows
    for (scope, fcn), args in gin.config._CONFIG.items():

        # loop over functions
        for fcn_name, f in FUNCS.items():
            full_fcn_name = f.__module__ + '.' + fcn_name
            if fcn == full_fcn_name:
                f = getattr(tune, fcn_name)
                config[f"{PREFIX}/{scope}/{fcn_name}"] = f(**args)

    config[GIN_CONFIG_ATTR] = gin.config_str()

    return config

def _tune_gin_wrap_inner(config, function, checkpoint_dir=None):
    """Bind gin parameters from tune config and call function on the resulting config."""
    gin.parse_config(config[GIN_CONFIG_ATTR])

    for key, value in config.items():
        if key.startswith(PREFIX):
            _, scope, name = key.split('/')
            gin.bind_parameter(scope + '/' + name + '.' + OVERRIDE_ATTR, value)

    config_new = deepcopy(config)
    del config_new[GIN_CONFIG_ATTR]
    return function(config_new, checkpoint_dir=checkpoint_dir)

def tune_gin_wrap(function):
    """Wrap around a function and process tune-gin parameters."""

    inner = partial(_tune_gin_wrap_inner, function=function)
    inner.__name__ = function.__name__

    return inner


@gin.configurable
def tune_run(*args, **kwargs):
    """Run tune trial, gin-configurable."""
    return tune.run(*args, **kwargs)


def tune_gin(func, config_update=None, **kwargs):
    """Tune with gin capability."""
    func_wrapped = tune_gin_wrap(func)
    config = config_update if config_update else {}
    config.update(gin_tune_config())
    return tune_run(func_wrapped, config=config, **kwargs)