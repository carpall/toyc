from os.path import abspath
from utils   import *
from plugin  import StopExecution, plugin_call

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

    if plugin_call('on_error_report', self.report, error=error) == StopExecution: return
    
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

def extend_pos(pos_left, pos_right):
  return SourcePosition(pos_left.src_info, pos_left.row, pos_left.col, (pos_right.col - pos_left.col) + pos_right.len, None, None)

def range_to_len(start, stop):
  return stop - start