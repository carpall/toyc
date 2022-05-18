from os    import listdir
from types import ModuleType

PLUGINS_CLASSES   = []
PLUGINS_INSTANCES = []

def load_plugins(path):
  for file in listdir(path):
    if file.endswith('.plugin.py'):
      module = ModuleType(file.removesuffix('.plugin.py'))
      exec(open(f'{path}/{file}').read(), module.__dict__)

def init_plugins(**kwargs):
  for plugin_class in PLUGINS_CLASSES:
    PLUGINS_INSTANCES.append(plugin_class(**kwargs))

def plugin_call(impl_name, component, method, **args):
  for plugin in PLUGINS_INSTANCES:
    getattr(plugin, impl_name)(component, method, **args)

class Plugin:
  def __init__(self, **kwargs):
    self.__dict__ = kwargs

  def __init_subclass__(cls):
    PLUGINS_CLASSES.append(cls)
  
  # component: the compiler component which reported the error
  # method: the method which made the plugin call
  # error: the error instance
  def on_error_report(self, component, method, error):
    pass