from compiler_utils import CompilerComponent, CompilerResult, SourcePosition
from utils          import *
from data           import *
from plugin         import plugin_call

class FieldIgnore:
  def __init__(self, to_match):
    self.to_match = to_match

class AsField:
  def __init__(self, name, to_match):
    self.name = name
    self.to_match = to_match

class UndefinedSequence:
  def __init__(self, *to_match):
    self.to_match = to_match

class Pattern:
  def __init__(self, *to_match):
    self.to_match = to_match

PATTERNS = {
  'var': Pattern('type', 'id', FieldIgnore('='), 'expr', FieldIgnore(';')),

  'fn': Pattern(
    'type',
    'id',
    FieldIgnore('('),
    AsField('params', UndefinedSequence('type', 'name', )),
    FieldIgnore(')'),
    'block'
  )
}

class Parser(CompilerComponent):
  def __init__(self, src_info, tokens):
    super().__init__(src_info)

    self.tokens = tokens

  def gen(self):
    pass