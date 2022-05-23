from compiler_utils import CompilerComponent
from utils          import *
from data           import *
from plugin         import plugin_call

class Parser(CompilerComponent):
  def __init__(self, src_info, tokens):
    super().__init__(src_info)

    self.tokens = tokens
    self.idx = 0

  @property
  def cur(self):
    return self.tokens[self.idx]

  def eof(self):
    return self.idx >= len(self.tokens)
  
  def save_idx(self):
    return self.idx

  def update_idx(self, new_idx):
    self.idx = new_idx
  
  def advance(self, count=1):
    self.idx += count

  def get_expecting_error_msg(self, method, args):
    return f"expected '{args[0]}'" if method.__name__ == 'match_token' else f"expected '{method.__name__.replace('match_', '')}'"

  def expect(self, method, *args):
    if not (matches := method(*args)).unwrap():
      self.report(self.get_expecting_error_msg(method, args), self.cur.pos)
    
    self.update_idx(matches.new_idx)
    return matches
  
  def expect_any(self, *methods_and_args):
    for method, args in methods_and_args:
      if (matches := method(*args)).unwrap():
        self.update_idx(matches.new_idx)
        return matches
    
    self.report(
      f"expected one of '{' '.join([self.get_expecting_error_msg(method, args) for method, args in methods_and_args])}'",
      self.cur.pos
    )
    return Out(False, new_idx=self.idx + 1, node=None)

  def match_token(self, kind):
    return Out(self.cur.kind == kind, new_idx=self.idx + 1, node=self.cur)

  def collect_typed_decl(self, type):
    decl_name = self.expect(self.match_token, 'id').node.value
    
    match self.cur.kind:
      case '(': # fn decl
        params = self.collect_fn_params_decl()
        block = self.expect_any((self.match_block, ), (self.match_token, ';')).node

        return FnNode(decl_name, params, block)

      case ';' | '=': # global var decl
        pass

  def next_node(self):
    if (matches_node := plugin_call('match_next_node', self.next_node)).unwrap():
      node = matches_node.node
      self.update_idx(matches_node.new_idx)
    elif (matches_type := self.match_type()).unwrap():
      self.update_idx(matches_type.new_idx)
      node = self.collect_typed_decl(matches_type.node)
    else:
      self.advance()
      node = BadNode(self.cur)
      self.report('unexpected token', self.cur.pos)
    
    return node

  def gen(self):
    self.output = []

    while not self.eof():
      node = self.next_node()

      self.output.append(node)

    return self.output