from compiler_utils import CompilerComponent, CompilerResult
from utils          import Out, json
from data           import Node, Token

OUT_FALSE = Out(False, node=None)

class macro_dbg:
  def __repr__(self):
    return f'{type(self).__name__}({self.__dict__})'

class as_field(macro_dbg):
  def __init__(self, name, to_match, store_also_when_dont_match=True):
    self.name = name
    self.to_match = to_match
    self.store_also_when_dont_match = store_also_when_dont_match

def field(to_match):
  if not isinstance(to_match, str):
    raise Exception("expected str to match")

  return as_field(to_match, to_match)

class one_of(macro_dbg):
  def __init__(self, *one_of_them_to_match):
    self.one_of_them_to_match = one_of_them_to_match

class undefined_seq(macro_dbg):
  def __init__(self, to_match, sep=None, allow_trailing_seps=False, insert_seps=False, require_sep_at_edges=False, min=None, max=None):
    self.to_match = to_match
    self.sep = sep
    self.allow_trailing_seps = allow_trailing_seps
    self.insert_seps = insert_seps
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

class get_field(macro_dbg):
  def __init__(self, name):
    self.name = name

class mark_as(macro_dbg):
  def __init__(self, to_match, name):
    self.to_match = to_match
    self.name = name

class optional(macro_dbg):
  def __init__(self, to_match):
    self.to_match = to_match

class inline_pattern(macro_dbg):
  def __init__(self, *to_match):
    self.to_match = to_match

class pattern(macro_dbg):
  def __init__(self, kind, *to_match, take_just=None):
    self.kind = kind
    self.to_match = to_match
    self.take_just = take_just

PATTERNS = [
  pattern('var',
    field('type'), field('id'),
    one_of(
      as_field('body', match_but_get(';', lambda parser, matched: None)),
      inline_pattern('=', as_field('body', 'expr'), ';')
    )
  ),

  pattern('fn',
    field('type'), field('id'),
    '(',
      as_field('params',
        undefined_seq(pattern('param', field('type'), field('id')), sep=',')
      ),
    ')',
    as_field('body', one_of(
      match_but_get(';', lambda parser, matched: None),
      'block'
    ))
  ),

  pattern('block',
    '{',
      as_field('_', undefined_seq('statement')),
    '}',
    take_just=get_field('_')
  ),

  pattern('statement',
    as_field('_', one_of(
      'var',
      'if_',
      'while_',
      'block',
      'return_',
      take_from(pattern(None, as_field('_', 'continue'), ';'), '_'),
      take_from(pattern(None, as_field('_', 'break'), ';'), '_'),
      take_from(pattern(None, as_field('_', 'expr'), ';'), '_'),
    )),
    take_just=get_field('_')
  ),

  pattern('return_',
    'return', as_field('body', optional('expr')), ';'
  ),

  pattern('while_',
    'while', '(', field('expr'), ')', as_field('body', 'block')
  ),

  pattern('if_',
    'if', '(', field('expr'), ')', as_field('body', 'block'),

    as_field('elseif_nodes', undefined_seq(
      pattern('elseif_node',
        inline_pattern('else', 'if'), '(', field('expr'), ')', as_field('body', 'block')
      )
    )),

    as_field('else_node',
      optional(
        take_from(pattern(None, 'else', as_field('body', 'block')), 'body')
      )
    )
  ),

  pattern('expr',
    as_field('nodes',
      undefined_seq(
        undefined_seq('term', sep=one_of('*', '/'), insert_seps=True, min=1),
      sep=one_of('+', '-'), insert_seps=True, min=1)
    ),

    as_field('inline_if', optional(pattern('inline_if_node',
      '?', as_field('then_expr', 'expr'), ':', as_field('else_expr', 'expr')
    ))),
  ),

  pattern('un',
    as_field('op', undefined_seq(one_of('+', '-', '*', '&'), min=1)), as_field('expr', 'term'),
  ),

  pattern('term',
    as_field('_', one_of(inline_pattern('(', field('expr'), ')'), 'un', 'id', 'digit')),
    take_just=get_field('_')
  ),

  pattern('type',
    one_of(
      inline_pattern(

        as_field('is_unsigned',
          match_but_get(
            optional(one_of('signed', 'unsigned')), lambda parser, matched: matched.node.value == 'unsigned' if matched.node is not None else False
          )
        ),

        as_field('name', take_from(one_of(
            pattern('i8', 'char'),
            pattern('i16', 'short'),
            pattern('i16', one_of(inline_pattern('short', 'int'), 'short')),
            pattern('f32', 'float'),

            pattern('f64', one_of(inline_pattern('long', 'double'), 'double')),

            pattern('i32', one_of(inline_pattern('long', 'int'), 'int')),

            pattern('i64', one_of(inline_pattern('long', 'long', 'int'), inline_pattern('long', 'long'), 'long')),
          ), 'kind'),
          store_also_when_dont_match=False
        )
      ),

      as_field('name', 'id', store_also_when_dont_match=False)
    ),

    as_field('ptr_level', undefined_seq_counter('*')),
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
        if not (sep_matches := self.match_pattern(pattern_to_match.sep)).unwrap():
          has_to_require_sep = False
          break
        
        if pattern_to_match.insert_seps:
          nodes.append(sep_matches.node)

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

  def process_get_field_macro(self, pattern_to_match):
    reversed = self.nodes_in_progress[::-1]

    for node in reversed:
      if hasattr(node, pattern_to_match.name):
        return Out(True, node=getattr(node, pattern_to_match.name))
    
    raise Exception(f'no such field: {pattern_to_match.name}')

  def process_mark_as_macro(self, pattern_to_match):
    if not (m := self.match_pattern(pattern_to_match.to_match)).unwrap():
      return OUT_FALSE
    
    m.node.kind = pattern_to_match.name

    return Out(True, node=m.node)
  
  def process_optional_macro(self, pattern_to_match):
    if (m := self.match_pattern(pattern_to_match.to_match)).unwrap():
      return m
    
    return Out(True, node=None)

  def process_as_field_macro(self, pattern_to_match):
    r = self.match_pattern(pattern_to_match.to_match)

    if pattern_to_match.name == 'kind':
      raise Exception(f'invalid name in: {pattern_to_match}')

    if pattern_to_match.store_also_when_dont_match or r.unwrap():
      setattr(self.node, pattern_to_match.name, r.node)

    return r
  
  def process_inline_pattern_macro(self, pattern_to_match):
    starting_idx = self.idx
    r = Out(True, node=None)

    for step in pattern_to_match.to_match:
      if not self.match_pattern(step).unwrap():
        r = OUT_FALSE
        break
    
    if not r.unwrap():
      self.idx = starting_idx
    
    return r

  def process_str_macro(self, pattern_to_match):
    if (has_pattern := self.has_pattern_for(pattern_to_match)).unwrap():
      if not (m := self.match_pattern(has_pattern.pattern)).unwrap():
        return OUT_FALSE

      if has_pattern.pattern.take_just is not None:
        self.nodes_in_progress.append(m.node)
        m = self.match_pattern(has_pattern.pattern.take_just)
        self.nodes_in_progress.pop()

      return m

    if self.cur.kind != pattern_to_match:
      return OUT_FALSE

    self.advance()
    return Out(True, node=self.bck)

  def process_pattern_macro(self, pattern_to_match):
    starting_idx = self.idx
    r = True
    self.nodes_in_progress.append(Node(pattern_to_match.kind))

    for step in pattern_to_match.to_match:
      if not self.match_pattern(step).unwrap():
        r = False
        break

      # if hasattr(matches, 'field_name') and matches.field_name is not None:
      #   setattr(node, matches.field_name, matches.field_value)
    
    if not r:
      self.idx = starting_idx
    
    return Out(r, node=self.nodes_in_progress.pop())

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

    return Out(True, node=pattern_to_match.get_value(self, matches))

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
    for pattern in PATTERNS:
      if (matches := self.match_pattern(pattern)).unwrap():
        return matches.node
      
    self.advance()
    self.report('unexpected token here', self.cur.pos)

  def gen(self):
    nodes = []

    while not self.eof():
      nodes.append(self.parse_node())

    return CompilerResult(self.errors_bag, nodes)