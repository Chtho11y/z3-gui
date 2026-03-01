from z3 import *

class BinaryOp:
    def __init__(self, op, lhs_priority=0, rhs_priority=0):
        self.op = op
        self.lhs_priority = lhs_priority
        self.rhs_priority = rhs_priority

    def __str__(self):
        return self.op
    
    def eval(self, lhs, rhs):
        return eval(f"({lhs} {self.op} {rhs})")

    def compile(self, lhs, rhs):
        return eval(f"({lhs} {self.op} {rhs})")
    
    def to_expr_str(self, lhs_str, rhs_str):
        return f"{lhs_str} {self.op} {rhs_str}"
    
class AndOp(BinaryOp):
    def __init__(self):
        super().__init__("and", lhs_priority=11, rhs_priority=12)
    
    def compile(self, lhs, rhs):
        return z3.And(lhs, rhs)
    
    def to_expr_str(self, lhs_str, rhs_str):
        return f"z3.And({lhs_str}, {rhs_str})"

class OrOp(BinaryOp):
    def __init__(self):
        super().__init__("or", lhs_priority=13, rhs_priority=14)
    
    def compile(self, lhs, rhs):
        return z3.Or(lhs, rhs)
    
    def to_expr_str(self, lhs_str, rhs_str):
        return f"z3.Or({lhs_str}, {rhs_str})"

op_table = {
    "(": BinaryOp("(", lhs_priority=-2, rhs_priority=-1),
    "[": BinaryOp("[", lhs_priority=-2, rhs_priority=-1),
    
    "*": BinaryOp("*", lhs_priority=1, rhs_priority=2),
    "+": BinaryOp("+", lhs_priority=3, rhs_priority=4),
    "-": BinaryOp("-", lhs_priority=3, rhs_priority=4),

    "=": BinaryOp("==", lhs_priority=9, rhs_priority=10),
    "==": BinaryOp("==", lhs_priority=9, rhs_priority=10),
    "!=": BinaryOp("!=", lhs_priority=9, rhs_priority=10),
    ">": BinaryOp(">", lhs_priority=9, rhs_priority=10),
    "<": BinaryOp("<", lhs_priority=9, rhs_priority=10),
    ">=": BinaryOp(">=", lhs_priority=9, rhs_priority=10),
    "<=": BinaryOp("<=", lhs_priority=9, rhs_priority=10),

    "&&": AndOp(),
    "||": OrOp(),

    ",": BinaryOp(",", lhs_priority=101, rhs_priority=100), # 仅解析参数列表用，不会出现在最终的Z3表达式中
}