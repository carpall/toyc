from copy     import copy, deepcopy
from pathlib  import Path
from os.path  import exists as file_exists
from os       import getcwd
from utils    import *
from data     import *
from datetime import datetime
from xlexer   import Lexer

class Preprocessor(CompilerComponent):
  def __init__(self, src_info, tokens, symbols=[]):
    super().__init__(src_info)

    self.tokens = tokens
    self.idx = 0
    self.skip_tokens_until_endif = False
    self.conditions_count = 0
    self.symbols = symbols
    self.output = []
  
  @property
  def cur(self):
    return self.tokens[self.idx]
  
  # returns the last token
  @property
  def lst(self):
    return self.tokens[-1]

  def eof(self):
    return self.idx >= len(self.tokens)

  def advance_and_get_cur(self):
    self.idx += 1

    return Option(None) if self.eof() else Option(self.cur)

  def is_symbol(self, name):
    for symbol in self.symbols:
      if symbol.name == name:
        return Out(True, symbol=symbol)
    
    return Out(False)

  def expand_id(self, token):
    match token.value:
      case '__FILE__':
        self.output.append(Token('str', self.src_info.filename, token.pos))

      case '__LINE__':
        self.output.append(Token('digit', str(token.pos.row), token.pos))
        
      case '__DATE__':
        date = datetime.today().strftime('%Y/%m/%d')
        self.output.append(Token('str', date, token.pos))
      
      case '__TIME__':
        time = datetime.today().strftime('%H:%M:%S')
        self.output.append(Token('str', time, token.pos))
      
      case '__TIMESTAMP__':
        timestamp = datetime.today().strftime('%Y/%m/%d %H:%M:%S')
        self.output.append(Token('str', timestamp, token.pos))

      case _:
        self.output.append(token)

  def define_symbol(self, symbol_to_define):
    for (i, symbol) in enumerate(self.symbols):
      if symbol.name == symbol_to_define.name:
        self.symbols[i] = symbol_to_define
        return

    self.symbols.append(symbol_to_define)

  def undefine_symbol(self, name):
    for (i, symbol) in enumerate(self.symbols):
      if symbol.name == name:
        self.symbols.pop(i)
        return

  def collect_macro_call_arg(self):
    argument = []
    l_brackets = 0

    while True:
      token = self.advance_and_get_cur()

      if token.is_none:
        self.report("expected ')' or ',' found eof", self.lst.pos)
        break
        
      token = token.unwrap()

      if token.kind == ',' and l_brackets == 0:
        return (True, argument)

      if token.kind == ')' and l_brackets == 0:
        return (False, argument)

      if token.kind in ['(', '[', '{', '<']:
        l_brackets += 1

      if token.kind in [')', ']', '}', '>']:
        l_brackets -= 1
      
      argument.append(token)

  def collect_macro_call_args(self):
    arguments = []
    
    while True:
      (has_next, arg) = self.collect_macro_call_arg()
      
      arguments.append(arg)

      if not has_next:
        break

    return arguments

  def expand_symbol(self, symbol, token):
    expanded_tokens = []

    match symbol.__class__.__name__:
      case 'PreprocessorIdentifier':
        expanded_tokens = Preprocessor(self.src_info, symbol.value, copy(self.symbols)).gen().print_errors_and().result

      case 'PreprocessorMacro':
        if self.advance_and_get_cur().is_some_with(lambda t: t.kind == '('):
          actual_args = self.collect_macro_call_args()

          if len(actual_args) != len(symbol.args):
            self.report("wrong arg number in macro call", token.pos)
            expanded_tokens = []
          else:
            sub_preprocessor = Preprocessor(self.src_info, symbol.value, copy(self.symbols))
            sub_preprocessor.output = expanded_tokens

            for (arg, actual_arg) in zip(symbol.args, actual_args):
              sub_preprocessor.define_symbol(PreprocessorIdentifier(arg, actual_arg))

            sub_preprocessor.undefine_symbol(token.value)
            sub_preprocessor.gen().print_errors()

        else:
          expanded_tokens = [token]

    for token in expanded_tokens:
      token = deepcopy(token)

      token.pos = token.pos
      self.output.append(token)
  
  def collect_tokens_until_newline(self):
    tokens = []

    while not self.eof():
      current_token = self.advance_and_get_cur()

      if not (t := current_token.is_some_and()).unwrap() or t.value.pos.is_on_new_line:
        self.idx -= 1
        break

      tokens.append(t.value)

    return tokens

  def include_file(self, path, path_pos):
    if self.src_info.filename == path:
      self.report("the header is including it self", path_pos)
      return

    lexer_result = Lexer(SourceInfo(path)).gen().print_errors_and()
    preprocessor = Preprocessor(self.src_info, lexer_result.result, self.symbols)
    preprocessor.output = self.output
    preprocessor.gen().print_errors()

    # self.merge_symbols(preprocessor.symbols)

  def is_defined(self, name):
    for symbol in self.symbols:
      if symbol.name == name:
        return True

    return False

  def collect_macro_args(self):
    args = []
    can_push = True

    while True:
      if (arg := self.advance_and_get_cur().is_some_and()).unwrap():
        arg = arg.value
        report_unexpected_token = lambda: self.report("unexpected token in macro definition", arg.pos)

        match arg.kind:
          case 'id':
            if not can_push:
              report_unexpected_token()

            can_push = False
            args.append(arg.value)

          case ',':
            can_push = True

          case ')':
            break

          case _:
            report_unexpected_token()
        
      else:
        self.report("expected ')' or ',' found eof", self.lst.pos)

    # skipping ')'
    self.idx += 1

    return args

  def expand_preprocessor_directive(self, directive):
    has_to_skip_until_endif = self.skip_tokens_until_endif
    conditions_count = self.conditions_count
    report_invalid_directive = lambda: self.report('invalid directive', directive.pos)

    if directive.kind != 'id':
      report_invalid_directive()
      return

    if directive.value == 'endif' and conditions_count == 0:
      self.report("unmatched 'endif'", directive.pos)
      return

    if has_to_skip_until_endif:
      match directive.value:
        case 'ifdef' | 'ifndef':
          self.conditions_count += 1

        case 'endif':
          self.conditions_count -= 1
          self.skip_tokens_until_endif = self.conditions_count > 0

      return

    match directive.value:
      case 'define':
        token = self.advance_and_get_cur()

        if token.is_none or token.is_some_with(lambda t: t.kind != 'id'):
          self.report("expected identifier after 'define' directive", token.unwrap_or(directive).pos)

        if (symbol_token := token.is_some_and()).unwrap():
          symbol_token = symbol_token.value
          cur_token = self.advance_and_get_cur()

          # macro definition
          macro_args_option = cur_token.is_some_and_then(
            lambda token:
              Option(self.collect_macro_args()) if token.kind == '(' and token.pos.spacing == 0 and not token.pos.is_on_new_line else Option(None)
          )

          # going back to the macro identifier token
          self.idx -= 1

          symbol_tokens = self.collect_tokens_until_newline()

          self.define_symbol(
            PreprocessorMacro(symbol_token.value, macro_args.value, symbol_tokens) \
              if (macro_args := macro_args_option.is_some_and()).unwrap() else PreprocessorIdentifier(symbol_token.value, symbol_tokens)
          )

      case 'ifdef' | 'ifndef':
        self.conditions_count += 1
        
        if (token_to_check := self.advance_and_get_cur().is_some_and()).unwrap():
          token_to_check = token_to_check.value

          is_defined = self.is_defined(token_to_check.value)
          self.skip_tokens_until_endif = not is_defined if directive.value == 'ifdef' else is_defined
        else:
          self.report(f"expected identifier after '{directive.name}' directive", directive.pos)

      case 'endif':
        self.conditions_count -= 1

      case 'undef':
        if (symbol_to_undefine := self.advance_and_get_cur().is_some_and()).unwrap():
          symbol_to_undefine = symbol_to_undefine.value

          if symbol_to_undefine.kind != 'id':
            self.report("expected identifier after 'undef'", symbol_to_undefine.pos)
          else:
            self.undefine_symbol(symbol_to_undefine.value)

      case 'include':
        current_token = self.advance_and_get_cur()
        report_invalid_path_token = lambda pos: self.report("expected path as string token or between '<' '>' tokens", pos)

        if not (path_token := current_token.is_some_and()).unwrap():
          report_invalid_path_token(directive.pos)
          return

        path_token = path_token.value
        report_invalid_path = lambda pos: self.report('invalid path', pos)

        match path_token.kind:
          case 'str':
            base = Path(self.src_info.filename).parent.absolute()
            filename = f'{base}/{path_token.value}'

            if not file_exists(filename):
              report_invalid_path(path_token.pos)
            else:
              self.include_file(filename, path_token.pos)

          case '<':
            base = f'{getcwd()}/std'
            (relative_path, end_col_pos) = self.collect_standard_path_inside_include()
            relative_path_pos = SourcePosition(
              self.src_info,
              path_token.pos.row,
              path_token.pos.col,
              end_col_pos - path_token.pos.col + 1,
              path_token.pos.spacing,
              path_token.pos.is_on_new_line
            )

            filename = abspath(f'{base}/{relative_path}')

            if not file_exists(filename):
              report_invalid_path(path_token.pos)
            else:
              self.include_file(filename, relative_path_pos)
          
          case _:
            report_invalid_path_token(path_token.pos)
  
      case 'pragma':
        raise NotImplementedError('implement pragma directive')

      case _:
        report_invalid_directive()

  def extend_token_or_write_current(self):
    token = self.cur

    if self.skip_tokens_until_endif and token.kind != '#':
      return

    match token.kind:
      case '#':
        directive_token = self.advance_and_get_cur()

        if directive_token.is_some:
          self.expand_preprocessor_directive(directive_token.unwrap())
        else:
          self.report("expected preprocessor directive after '#'", token.pos)
      
      case 'id':
        if (out_symbol := self.is_symbol(token.value)).unwrap():
          self.expand_symbol(out_symbol.symbol, token)
        else:
          self.expand_id(token)

      case _:
        self.output.append(token)

  def gen(self):
    while not self.eof():
      self.extend_token_or_write_current()
      self.idx += 1

    return CompilerResult(self.errors_bag, self.output)