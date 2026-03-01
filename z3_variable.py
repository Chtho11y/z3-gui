from z3 import Int
from enum import Enum
from context import GlobalContext
from typing import List

class Variable:
    def __init__(self, var_id, name, board_state, v_range=None, dtype=Int):
        self.id = var_id
        self.origin_name = name
        self.board = board_state
        self.v_range = v_range

        name = ''.join(c for c in name if c.isalnum() or c == '_')  #去掉非法字符
        self.name = f"v_{var_id}_{name}"

        self.vars = {}
        self.var_name = {}

        for i in range(0, len(board_state)):
            for j in range(0, len(board_state)):
                cell_id = f"{self.name}_{i}_{j}"
                self.vars[(i, j)] = Int(cell_id)
                self.var_name[(i, j)] = cell_id
        
    def get_basic_constraints(self):
        constraints = []
        n = len(self.board)
        if self.v_range:
            for i in range(0, n):
                for j in range(0, n):
                    constraints.append(self.vars[(i, j)] >= self.v_range[0])
                    constraints.append(self.vars[(i, j)] <= self.v_range[1])

                    if self.board[i][j] != "":
                        constraints.append(self.vars[(i, j)] == int(self.board[i][j]))

        return constraints
    
    def select(self, regions: List):
        selected_vars = []
        for region in regions:
            for (i, j) in region:
                selected_vars.append(self.vars[(i, j)])
        return selected_vars
    
class ValueType(Enum):
    VARIABLE = 'VARIABLE'
    NUMBER = 'NUMBER'
    STRING = 'STRING'
    FUNCTION = 'FUNCTION'
    BOOL = 'BOOL'
    REGION = 'REGION'
    VARLIST = 'VARLIST'

class Value:
    def __init__(self, value_type: ValueType, value):
        self.type = value_type
        self.value = value
    
    def unwarp(self, context: GlobalContext):
        var = context.get_current_variable()
        region = context.get_current_region()
        if self.type == ValueType.REGION:
            return Value(ValueType.VARLIST, var.select(self.value))
        if self.type == ValueType.FUNCTION:
            func = self.value
            return func([], context).unwarp(context)
        if self.type == ValueType.VARIABLE:
            return Value(ValueType.VARLIST, self.value.select(region))
        return self