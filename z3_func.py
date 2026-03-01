
from context import GlobalContext
from z3_variable import ValueType, Value
from z3_compile_error import Z3RuntimeError

class Z3Function:
    def __init__(self, name):
        self.name = name
    
    def impl(self, args, ctx: GlobalContext):
        pass

    def __call__(self, args, ctx):
        return self.impl(args, ctx)

class ZipFunction(Z3Function):
    def __init__(self):
        super().__init__("zip")
    
    def impl(self, args, ctx: GlobalContext):
        if len(args) != 2:
            raise ValueError("zip function requires exactly 2 arguments.")
        arg1, arg2 = args
        res = []
        for v1, v2 in zip(arg1.value, arg2.value):
            res.append((v1, v2))
        return Value(ValueType.VARLIST, res)
    
class SumFunction(Z3Function):
    def __init__(self):
        super().__init__("sum")
    
    def impl(self, args, ctx: GlobalContext):
        if len(args) == 0:
            args.append(Value(ValueType.REGION, ctx.get_current_region()))
        for i in range(len(args)):
            args[i] = args[i].unwarp(ctx)
        
        sum_expr = 0
        for arg in args:
            if arg.type == ValueType.VARLIST:
                for var in arg.value:
                    sum_expr += var
            elif arg.type == ValueType.NUMBER:
                sum_expr += arg.value
            else:
                raise TypeError("sum function only supports variables and numbers.")

        return Value(ValueType.VARLIST, [sum_expr])

function_list = {
    "zip": ZipFunction(),

    "sum": SumFunction(),
}