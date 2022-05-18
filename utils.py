from os.path import abspath
from types   import LambdaType
from plugin  import plugin_call

class SourceInfo:
  def __init__(self, filename):
    self.filename = abspath(filename)
    self.filecontent = open(self.filename).read()

class SourcePosition:
  def __init__(self, src_info, row, col, len, spacing, is_on_new_line):
    self.src_info = src_info
    self.row = row
    self.col = col
    self.len = len
    self.spacing = spacing
    self.is_on_new_line = is_on_new_line
  
  def __repr__(self):
    return f'{self.__class__.__name__} {vars(self)}'

class CompilerError:
  def __init__(self, msg, pos):
    self.msg = msg
    self.pos = pos

class CompilerComponent:
  def __init__(self, src_info):
    self.src_info = src_info
    self.errors_bag = []
  
  def gen(self):
    raise NotImplementedError()

  def report(self, msg, pos):
    error = CompilerError(msg, pos)

    plugin_call('on_error_report', type(self), CompilerComponent.report, error=error)
    self.errors_bag.append(error)

class CompilerResult:
  def __init__(self, errors_bag, result):
    self.errors_bag = errors_bag
    self.result = result
  
  @property
  def is_ok(self):
    return len(self.errors_bag) == 0
  
  def print_error(self, error, src_lines):
    pos = error.pos
      
    print("{}:{}:{} -> {}\n{} | {}".format(pos.src_info.filename, pos.row, pos.col, error.msg, pos.row, src_lines[pos.row - 1]))
    
    for _ in range(0, len(str(pos.row)) + 2 + pos.col):
      print(end=' ')

    for _ in range(0, pos.len):
      print(end='~')

    print()
  
  def print_errors_or_else(self, or_else):
    if self.is_ok:
      return or_else(self.result)
    
    src_lines = self.errors_bag[0].pos.src_info.filecontent.splitlines()
    
    for error in self.errors_bag:
      self.print_error(error, src_lines)
  
  def print_errors(self):
    self.print_errors_or_else(lambda _: None)
  
  def print_errors_and(self):
    self.print_errors()
    return self
  
  def print_errors_and_then(self, and_then):
    self.print_errors()
    and_then(self.result)

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