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

class Out:
  def __init__(self, ret, **params):
    if 'ret' in params:
      raise NameError('ret is a reserved field')

    self.__dict__ = params
    self.ret = ret
  
  def unwrap(self):
    return self.ret
  
  def __repr__(self):
    return f'Out {vars(self)}'

def range_to_len(start, stop):
  return stop - start

def dbg(**kwargs):
  print('DBG ->', kwargs)