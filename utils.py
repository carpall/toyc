from types import LambdaType

class Option:
  def __init__(self, value):
    self.value = value
  
  @property
  def is_some(self):
    return self.value != None
  
  @property
  def is_none(self):
    return not self.is_some
  
  def unwrap(self):
    if self.is_none:
      raise ValueError('unwrapped none')
    
    return self.value
  
  def unwrap_or_default(self, default):
    return self.value if self.is_some else default

  def unwrap_or_else(self, or_else):
    return self.value if self.is_some else or_else()
  
  def is_some_with(self, value):
    if isinstance(value, LambdaType):
      return self.is_some and value(self.value)

    return self.is_some and self.value == value
  
  def is_some_with_any(self, values):
    return self.is_some and self.value in values
  
  def is_some_and(self):
    return Out(self.is_some, value=self.value)
  
  def is_some_and_then(self, and_then):
    return and_then(self.value) if self.is_some else self

debug_indent = ''

class Debug:
  def __init__(self, fields_to_ignore=[]):
    self.to_ignore = fields_to_ignore + ['to_ignore']

  def __repr__(self):
    global debug_indent

    result = f'{self.__class__.__name__} {{'
    debug_indent += '  '

    for key, value in self.__dict__.items():
      if key in self.to_ignore:
        continue

      result += f'\n{debug_indent}{key}: {repr(value)},'

    debug_indent = debug_indent[:-2]
    result += f'\n{debug_indent}}}'

    return result

class Out(Debug):
  def __init__(self, ret, **params):
    if 'ret' in params:
      raise NameError('ret is a reserved field')

    self.__dict__ = params
    self.ret = ret
  
  def unwrap(self):
    return self.ret

def todo():
  raise NotImplementedError('todo')

def dbg(**kwargs):
  print('DBG ->', kwargs)

def inline_function(*args, ret=None):
  return ret