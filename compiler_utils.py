from os.path import abspath, isfile
from utils   import *
from plugin  import plugin_call

USAGE = 'toyc <action> [options]'

ACTIONS = {
  'help': 'print this message',
  'build': "generates an executable from a source file '-s'"
}

pad_action_desc = lambda action: ' ' * (max([len(key) for key in ACTIONS.keys()]) - len(action))
stringify_actions = lambda: '\n    '.join(map(lambda action_desc: f'{action_desc[0]}:{pad_action_desc(action_desc[0])} {action_desc[1]}', ACTIONS.items()))

HELP = f'''
  Usage: {USAGE}

  Actions:
    {stringify_actions()}
'''

class SourceInfo:
  def __init__(self, filename, action, args):
    self.filename = filename
    self.filecontent = open(self.filename).read() if filename is not None else None
    self.action = action
    self.args = args

class SourcePosition:
  def __init__(self, src_info, row, col, len, spacing, is_on_new_line):
    self.src_info = src_info
    self.row = row
    self.col = col
    self.len = len
    self.spacing = spacing
    self.is_on_new_line = is_on_new_line
  
  def __repr__(self):
    return '..'

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

    plugin_call('on_error_report', self.report, error=error)
    
    self.errors_bag.append(error)

    plugin_call('on_error_reported', self.report, error=error)

class CompilerResult:
  def __init__(self, errors_bag, result):
    self.errors_bag = errors_bag
    self.result = result
  
  @property
  def is_ok(self):
    return len(self.errors_bag) == 0
  
  @staticmethod
  def print_error(error, src_lines):
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
    return and_then(self.result)

class Compiler:
  def __init__(self, args, modules):
    self.src_info = SourceInfo(None, args[0] if len(args) > 0 else None, args[1:])
    self.modules = modules
    self.results = {}
  
  @property
  def action(self):
    return self.src_info.action
  
  @property
  def args(self):
    return self.src_info.args

  @property
  def lexer(self):
    return self.modules['lexer'].Lexer
  
  @property
  def preprocessor(self):
    return self.modules['preprocessor'].Preprocessor
  
  @property
  def parser(self):
    return self.modules['parser'].Parser

  def parse_args(self):
    if self.action is None:
      self.action_help()
      return

    attr = f'action_{self.action}'

    if not hasattr(self, attr):
      self.report_action('unknown action')
      return
    
    return getattr(self, attr)()

  def get_arg_pos(self, arg_idx):
    return SourcePosition(
      self.src_info,
      1,
      6 + len(self.action) + len(self.args) + sum(map(lambda arg: len(arg), self.args[:arg_idx])),
      len(self.args[arg_idx]), 0, True
    )

  def get_cmd_line(self):
    return [f'toyc {self.action} ' + ' '.join(map(lambda arg: arg if ' ' not in arg else f'"{arg}"', self.args))]
  
  def has_flag(self, flag):
    return flag in self.args

  def expect_arg(self, flag):
    try:
      idx = self.args.index(flag)
      if idx + 1 >= len(self.args):
        self.report_arg(f"expected argument for flag '{flag}'", idx)
        return None, None

      return self.args[idx + 1], idx + 1
    except ValueError:
      self.report_action(f"expected flag '{flag}' for action '{self.action}'")
      return None, None

  def report_action(self, msg):
    CompilerResult.print_error(
        CompilerError(msg, SourcePosition(self.src_info, 1, 6, len(self.action), 0, True)),
        self.get_cmd_line()
      )

  def report_arg(self, msg, arg_idx):
    CompilerResult.print_error(
      CompilerError(msg, self.get_arg_pos(arg_idx)),
      self.get_cmd_line()
    )

  def action_help(self):
    print(HELP)

  def action_build(self):
    filename, idx = self.expect_arg('-f')

    if filename is None:
      return
    
    filename = abspath(filename)

    if not isfile(filename):
      self.report_arg('not a valid file path', idx)
      return

    self.src_info = SourceInfo(filename, self.action, self.args)

    self.lex()
    self.preprocess()
    self.parse()
    # self.emit()

    # return self.results['emitter']
    return self.results['parser']

  def lex(self):
    self.results['lexer'] = self.lexer(self.src_info).gen().print_errors_and().result
  
  def preprocess(self):
    self.results['preprocessor'] = self.preprocessor(self.src_info, self.results['lexer']).gen().print_errors_and().result
  
  def parse(self):
    self.results['parser'] = self.parser(self.src_info, self.results['preprocessor']).gen().print_errors_and().result

def extend_pos(pos_left, pos_right):
  return SourcePosition(pos_left.src_info, pos_left.row, pos_left.col, (pos_right.col - pos_left.col) + pos_right.len, None, None)

def range_to_len(start, stop):
  return stop - start