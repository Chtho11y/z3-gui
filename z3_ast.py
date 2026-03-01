from tokenizer import Tokenizer, TokenType, Token
from context import GlobalContext
from z3_compile_error import NameNotFoundError, Z3CompileError, Z3RuntimeError
from z3_variable import ValueType, Value

def find_right_barket(tokens, left_v, right_v, start_index, fallback=False):
    depth = 0
    for i in range(start_index, len(tokens)):
        if tokens[i].value == left_v:
            depth += 1
        elif tokens[i].value == right_v:
            depth -= 1
            if depth == 0:
                return i
    if fallback:
        return len(tokens)
    raise Z3CompileError(f"Unmatched '{left_v}' starting at token index {start_index}")

class AstForNode:
    def __init__(self, vars, iterable_expr, body):
        self.vars = vars
        self.iterable_expr = iterable_expr
        self.body = body

    def parse(tokens, start_index, ctx: GlobalContext):
        # 解析for循环，例如 for i in row(reg1):
        if tokens[start_index].type != TokenType.KEYWORD or tokens[start_index].value != 'for':
            # Fallback to normal expression parsing if it's not a for loop
            expr_end = find_right_barket(tokens, '', ';', start_index, fallback=True)
            _, expr = AstExprNode.parse(tokens, start_index, expr_end, ctx)
            return expr_end + 1, expr
        
        # 解析变量列表
        vars = []
        i = start_index + 1
        while i < len(tokens) and not (tokens[i].type == TokenType.KEYWORD and tokens[i].value == 'in'):
            if tokens[i].type == TokenType.VAR:
                vars.append(tokens[i].value)
            else:
                raise Z3CompileError(f"Unexpected token [{tokens[i].type}]{tokens[i].value} in variable list of for loop at index {i}")
            i += 1
            if i < len(tokens) and tokens[i].value == ',':
                i += 1  # 跳过逗号
            elif i < len(tokens) and tokens[i].type == TokenType.KEYWORD and tokens[i].value == 'in':
                break
            else:
                raise Z3CompileError(f"Expected ',' in variable list of for loop at index {i}, got [{tokens[i].type}]{tokens[i].value}")
        
        i += 1  # 跳过'in'关键字
        
        # 解析可迭代对象表达式
        iterable_start = i
        while i < len(tokens) and not (tokens[i].type == TokenType.SYMBOL and tokens[i].value == ':'):
            i += 1
        
        if i >= len(tokens) or tokens[i].value != ':':
            raise Z3CompileError("Expected ':' after iterable expression in for loop")
        
        _, iterable_expr = AstExprNode.parse(tokens, iterable_start, i, ctx)
        
        i += 1  # 跳过':'符号
        
        loop_end, body = AstForNode.parse(tokens, i, ctx)
        
        return loop_end + 1, AstForNode(vars, iterable_expr, body)
    
    def to_str(self, indent=0):
        res = f"{' ' * indent}for {', '.join(self.vars)} in {self.iterable_expr.to_str()}:"
        res += "\n" + self.body.to_str(indent + 4)
        return res
        
class AstExprsNode:
    def __init__(self, args):
        self.args = args
    
    def parse(tokens, start_index, end_index, ctx: GlobalContext):
        args = []
        expr_node = AstExprNode.parse(tokens, start_index, end_index, ctx)
        while expr_node.op == ",":
            args.append(expr_node.args[0])
            expr_node = expr_node.args[1]
        return end_index, AstExprsNode(args)
    
    def to_str(self):
        return ", ".join(arg.to_str() for arg in self.args)

class AstRuleNode:
    def __init__(self, rule_name, args):
        self.rule_name = rule_name
        self.args = args

    def parse(tokens, start_index, ctx: GlobalContext):
        # 解析规则注解，例如 @sudoku(X, 9)
        if tokens[start_index].type != TokenType.ANNOTATION:
            raise Z3CompileError("Expected annotation token")
        
        annotation_token = tokens[start_index]
        if start_index + 1 >= len(tokens) or tokens[start_index + 1].value != '(':
            return start_index + 1, AstRuleNode(annotation_token.value[1:], [])  # 没有参数，直接返回
        
        args = []
        end_index = find_right_barket(tokens, '(', ')', start_index + 1)
        start_index += 2  # 跳过注解和左括号
        args = AstExprsNode.parse(tokens, start_index, end_index, ctx)
        return end_index + 1, AstRuleNode(annotation_token.value[1:], args.args)

    def to_str(self, indent=0):
        if self.args:
            return f"@{self.rule_name}({', '.join(arg.to_str() for arg in self.args)})"
        else:
            return f"@{self.rule_name}"
        
    def to_constraints(self, ctx: GlobalContext):
        if self.rule_name not in ctx.rules:
            raise NameNotFoundError(f"Rule '{self.rule_name}' not found in context.")
        rule_impl = ctx.rules[self.rule_name]
        return rule_impl.to_z3(self.args, ctx)

class AstExprNode:
    def __init__(self, op, args):
        self.op = op
        self.args = args

    def parse(tokens, start_index, end_index, ctx: GlobalContext):
        # 解析表达式，例如 sum(X[i]) == 45
        # 这里只是一个简单的示例，实际需要处理更多情况
        if start_index >= end_index:
            raise Z3CompileError("Unexpected end of tokens while parsing expression")
        
        max_priority = -1000
        main_op_index = -1
        
        for i in range(start_index, end_index):
            if tokens[i].type == TokenType.SYMBOL and tokens[i].value in ctx.op_list:
                op = ctx.op_list[tokens[i].value]
                if op.rhs_priority > max_priority: # 相比上一个最大值，现在它位于右侧
                    max_priority = op.lhs_priority # 相比下一个最大值，现在它位于左侧
                    main_op_index = i
        
        if main_op_index == -1:
            # 没有找到操作符，可能是一个变量或数字
            if tokens[start_index].type == TokenType.VAR:
                return start_index + 1, AstVarNode(tokens[start_index].value)
            elif tokens[start_index].type == TokenType.NUMBER:
                return start_index + 1, AstNumberNode(tokens[start_index].value)
            else:
                raise Z3CompileError(f"Unexpected token [{tokens[start_index].type}]{tokens[start_index].value} at index {start_index}")
        
        main_op = ctx.op_list[tokens[main_op_index].value]
        if main_op.op in ["(", "["]:  # 函数调用或索引访问
            right_index = find_right_barket(tokens, main_op.op, ")" if main_op.op == "(" else "]", main_op_index)
            if main_op.op == "(" and main_op_index == start_index and right_index == end_index - 1:
                # 纯括号
                return AstExprNode.parse(tokens, start_index + 1, end_index - 1, ctx)
            elif main_op.op == "(":
                func_name = tokens[main_op_index - 1].value if main_op_index > start_index else None
                if func_name is None or func_name not in ctx.function_list:
                    raise NameNotFoundError(f"Function '{func_name}' not found in context.")
                _, args_node = AstExprsNode.parse(tokens, main_op_index + 1, right_index, ctx)
                return right_index + 1, AstCallNode(func_name, args_node.args)
            else:  # 索引访问
                _, collection_node = AstExprNode.parse(tokens, start_index, main_op_index, ctx)
                _, index_node = AstExprNode.parse(tokens, main_op_index + 1, right_index, ctx)
                return right_index + 1, AstAccessNode(collection_node, index_node)

        # 二元操作
        _, left_node = AstExprNode.parse(tokens, start_index, main_op_index, ctx)
        _, right_node = AstExprNode.parse(tokens, main_op_index + 1, end_index, ctx)
        return end_index, AstExprNode(main_op.op, [left_node, right_node])
    
    def to_str(self, indent=0):
        print(self.op, self.args)
        left_str = self.args[0].to_str()
        right_str = self.args[1].to_str()
        return f"{' ' * indent}({left_str} {self.op} {right_str})"

class AstAccessNode:
    def __init__(self, collection, index):
        self.collection = collection
        self.index = index
    
    def to_str(self):
        return f"{self.collection.to_str()}[{self.index.to_str()}]"
    
    def to_constraints(self, ctx: GlobalContext):
        collection_val = self.collection.to_constraints(ctx)
        index_val = self.index.to_constraints(ctx)
        if index_val.type == ValueType.NUMBER:
            if collection_val.type == ValueType.VARIABLE:
                var = collection_val.value
                idx = index_val.value
                return Value(ValueType.VARLIST, var.select([idx]))
            elif self.collection_val.type == ValueType.REGION:
                return Value(ValueType.REGION, [collection_val.value[idx]])
            elif self.collection_val.type == ValueType.VARLIST:
                return Value(ValueType.VARLIST, [collection_val.value[idx]])
        elif index_val.type == ValueType.REGION:
            if collection_val.type == ValueType.VARIABLE:
                var = collection_val.value
                idxs = index_val.value
                return Value(ValueType.VARLIST, var.select(idxs))
        
        raise Z3RuntimeError("Unsupported index or array type for access operation")

class AstCallNode:    
    def __init__(self, func_name, args):
        self.func_name = func_name
        self.args = args

    def to_str(self):
        return f"{self.func_name}({', '.join(arg.to_str() for arg in self.args)})"

class AstVarNode:
    def __init__(self, name):
        self.name = name
    
    def to_str(self):
        return self.name
    
    def to_constraints(self, ctx: GlobalContext):
        v = ctx.get_solver_variable(self.name)
        return Value(ValueType.VARIABLE, v)
            
class AstNumberNode:
    def __init__(self, value):
        self.value = value
        if isinstance(value, str) and value.isdigit():
            self.value = int(value)

    def to_str(self):
        return str(self.value)
    
    def to_constraints(self, ctx: GlobalContext):
        return Value(ValueType.NUMBER, self.value)

class AstGlobalNode:
    def __init__(self, exprs):
        self.exprs = exprs

    def parse(tokens, ctx: GlobalContext):
        node = AstGlobalNode([])
        i = 0
        while i < len(tokens):
            if tokens[i].type == TokenType.KEYWORD and tokens[i].value == 'for':
                i, node_for = AstForNode.parse(tokens, i, ctx)
                node.exprs.append(node_for)
            elif tokens[i].type == TokenType.ANNOTATION:
                i, node_rule = AstRuleNode.parse(tokens, i, ctx)
                node.exprs.append(node_rule)
            else:
                end_index = find_right_barket(tokens, '', ';', i, fallback=True)
                i, node_expr = AstExprNode.parse(tokens, i, end_index, ctx)
                node.exprs.append(node_expr)
        return node
    
    def get_constraints(self, vid, cid, ctx: GlobalContext):
        constraints = []
        for expr in self.exprs:
            constraints.extend(expr.get_constraints(vid, cid, ctx))

        return constraints
    
    def to_str(self, indent=0):
        return "\n".join(expr.to_str(indent) for expr in self.exprs)

def compile_single_constraint(constraint_str, constraint_id, var_id, region, ctx: GlobalContext):
    if constraint_id == 0:
        return None
    # 定义符号列表（按长度降序排列）
    symbols = list(ctx.op_list.keys())  # 从上下文中获取操作符列表
    symbols.extend([':', '(', ')', '[', ']', '{', '}', ','])
    keywords = ctx.keywords  # 从上下文中获取关键字列表
    tokenizer = Tokenizer(symbols, keywords)  # 从上下文中获取函数列表作为关键字

    tokens = tokenizer.tokenize(constraint_str)
    print("Tokens:", tokens)
    node = AstGlobalNode.parse(tokens, ctx)
    print("Parsed AST:")
    try:    
        print(node.to_str())
    except Exception as e:
        import traceback
        traceback.print_exc()
    return node
