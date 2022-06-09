from compiler_utils import CompilerComponent, CompilerResult
from utils          import Out, json
from data           import Node, Token

OUT_FALSE = Out(False, node=None)

class macro_dbg:
  def __repr__(self):
    return f'{type(self).__name__}({self.__dict__})'

class as_field(macro_dbg):
  def __init__(self, name, to_match):
    self.name = name
    self.to_match = to_match

def field(to_match):
  if not isinstance(to_match, str):
    raise Exception("expected str to match")

  return as_field(to_match, to_match)

class one_of(macro_dbg):
  def __init__(self, *one_of_them_to_match):
    self.one_of_them_to_match = one_of_them_to_match

class undefined_seq(macro_dbg):
  def __init__(self, to_match, sep=None, allow_trailing_seps=False, require_sep_at_edges=False, min=None, max=None):
    self.to_match = to_match
    self.sep = sep
    self.allow_trailing_seps = allow_trailing_seps
    self.require_sep_at_edges = require_sep_at_edges
    self.min = min
    self.max = max

class undefined_seq_counter(undefined_seq):
  pass

class take_from(macro_dbg):
  def __init__(self, to_match, to_take):
    self.to_match = to_match
    self.to_take = to_take

class match_but_get(macro_dbg):
  def __init__(self, to_match, get_value_fn):
    self.to_match = to_match
    self.get_value = get_value_fn

class pattern(macro_dbg):
  def __init__(self, kind, *to_match):
    self.kind = kind
    self.to_match = to_match

PATTERNS = [
  pattern('var',
    field('type'), field('id'),
    as_field('body',
      one_of(
        match_but_get(';', lambda self, matched: None),
        take_from(pattern(None, '=', field('expr'), ';'), 'expr')
      )
    )
  ),

  pattern('expr',
    as_field('nodes', one_of('term', 'bin', 'un')),
  ),

  pattern('un',
    as_field('op', undefined_seq(one_of('+', '-', '*', '&'), min=1)), as_field('node', 'term'),
  ),

  pattern('par',
    '(', as_field('node', 'expr'), ')',
  ),

  pattern('term',
    as_field('node', one_of('id', 'digit', 'par')),
  ),

  pattern('type',
    as_field('_kind', one_of('builtin', 'id')), as_field('ptr_level', undefined_seq_counter('*')),
  ),

  pattern('builtin',
    as_field('_kind', one_of('char', 'short', 'int', 'long')),
  ),
]

class Parser(CompilerComponent):
  def __init__(self, src_info, tokens):
    super().__init__(src_info)

    self.tokens = tokens
    self.idx = 0
    self.nodes_in_progress = []
  
  @property
  def cur(self):
    return self.cur_plus(0)
  
  @property
  def bck(self):
    return self.cur_plus(-1)
  
  @property
  def node(self):
    return self.nodes_in_progress[-1]

  def cur_plus(self, count):
    return self.tokens[self.idx + count] if not self.eof(count) else Token('eof', '', self.tokens[-1].pos)
  
  def advance(self, count=1):
    self.idx += count
    return self.idx

  def eof(self, count=0):
    return self.idx + count >= len(self.tokens)

  def has_pattern_for(self, pattern_name):
    for pattern in PATTERNS:
      if pattern.kind == pattern_name:
        return Out(True, pattern=pattern)
    
    return Out(False)
  
  def process_undefined_seq_macro(self, pattern_to_match):
    nodes = []

    if pattern_to_match.require_sep_at_edges and pattern_to_match.sep is not None:
      if not self.match_pattern(pattern_to_match.sep).unwrap():
        return OUT_FALSE

    while True:
      has_to_require_sep = len(nodes) > 0 and pattern_to_match.sep is not None

      if has_to_require_sep:
        if not self.match_pattern(pattern_to_match.sep).unwrap():
          has_to_require_sep = False
          break

      if not (matches := self.match_pattern(pattern_to_match.to_match)).unwrap():
        if has_to_require_sep and not pattern_to_match.allow_trailing_seps and not pattern_to_match.require_sep_at_edges:
          self.report(f"trailing '{self.bck.value}' not allowed", self.bck.pos)
        
        break

      nodes.append(matches.node)
    
    if not has_to_require_sep and pattern_to_match.require_sep_at_edges and pattern_to_match.sep is not None:
      if not self.match_pattern(pattern_to_match.sep).unwrap():
        return OUT_FALSE
    
    if pattern_to_match.min is not None and len(nodes) < pattern_to_match.min or \
        pattern_to_match.max is not None and len(nodes) > pattern_to_match.max:
      return OUT_FALSE
    
    return Out(True, node=nodes)
  
  def process_one_of_macro(self, pattern_to_match):
    # matched_nodes = []

    for to_match in pattern_to_match.one_of_them_to_match:
      if (matches := self.match_pattern(to_match)).unwrap():
        # matched_nodes.append(matches.node)
        return Out(True, node=matches.node)
    
    # match len(matched_nodes):
    #   case 0:
    #     pass
    #   
    #   case 1:
    #     return Out(True, node=matched_nodes[0])
    #   
    #   case _:
    #     raise Exception(f'ambiguous syntax in: {pattern_to_match}')
    
    return OUT_FALSE

  def process_as_field_macro(self, pattern_to_match):
    r = Out((matches := self.match_pattern(pattern_to_match.to_match)).unwrap())

    if pattern_to_match.name == 'kind':
      raise Exception(f'invalid name in: {pattern_to_match}')

    setattr(self.node, pattern_to_match.name, matches.node)

    return r
  
  def process_str_macro(self, pattern_to_match):
    if (has_pattern := self.has_pattern_for(pattern_to_match)).unwrap():
      return self.match_pattern(has_pattern.pattern)

    if self.cur.kind != pattern_to_match:
      return OUT_FALSE

    self.advance()
    return Out(True, node=self.bck)

  def process_pattern_macro(self, pattern_to_match):
    self.nodes_in_progress.append(Node(pattern_to_match.kind))

    for step in pattern_to_match.to_match:
      if not self.match_pattern(step).unwrap():
        self.nodes_in_progress.pop()
        return OUT_FALSE

      # if hasattr(matches, 'field_name') and matches.field_name is not None:
      #   setattr(node, matches.field_name, matches.field_value)
    
    return Out(True, node=self.nodes_in_progress.pop())

  def process_undefined_seq_counter_macro(self, pattern_to_match):
    if (undefined_seq := self.process_undefined_seq_macro(pattern_to_match)):
      undefined_seq.node = len(undefined_seq.node)
    
    return undefined_seq
  
  def process_take_from_macro(self, pattern_to_match):
    if not (matches := self.match_pattern(pattern_to_match.to_match)).unwrap():
      return OUT_FALSE

    return Out(True, node=getattr(matches.node, pattern_to_match.to_take))
  
  def process_match_but_get_macro(self, pattern_to_match):
    if not (matches := self.match_pattern(pattern_to_match.to_match)).unwrap():
      return OUT_FALSE

    return Out(True, node=pattern_to_match.get_value(pattern_to_match, matches))

  def match_pattern(self, pattern_to_match):
    attr = f'process_{type(pattern_to_match).__name__}_macro'

    if not hasattr(self, attr):
      raise Exception(f"unexpected pattern type '{type(pattern_to_match)}'")

    return getattr(self, attr)(pattern_to_match)

  # def try_parse_node(self):
  #   matched_nodes = []
  #   starting_idx = self.idx
  # 
  #   for pattern in PATTERNS:
  #     if (matches := self.match_pattern(pattern)).unwrap() and pattern.can_be_matched_alone:
  #       matched_nodes.append((matches.node, self.idx))
  #     
  #     self.idx = starting_idx
  #   
  #   return Out(len(matched_nodes) == 1, matched_nodes=matched_nodes)

  # def parse_node(self):
  #   match len(matched_nodes := self.try_parse_node().matched_nodes):
  #     case 0:
  #       self.report('invalid syntax', self.cur.pos)
  #       matched_nodes.append((Node('bad'), self.idx + 1))
  # 
  #     case 1:
  #       pass
  #     
  #     case _:
  #       self.report('ambiguous syntax', self.cur.pos)
  #   
  #   self.idx = matched_nodes[0][1]
  #   return matched_nodes[0][0]

  def parse_node(self):
    starting_idx = self.idx

    for pattern in PATTERNS:
      if (matches := self.match_pattern(pattern)).unwrap():
        return matches.node
      
      self.idx = starting_idx
      
    self.advance()
    self.report('unexpected token here', self.cur.pos)

  def gen(self):
    nodes = []

    while not self.eof():
      nodes.append(self.parse_node())

    return CompilerResult(self.errors_bag, nodes)