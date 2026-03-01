from z3_compile_error import NameNotFoundError
from z3_ops import op_table
from z3_variable import Variable
from z3 import Solver, Int

class SolverContext:
    def __init__(self, size):
        self.solver = Solver()
        self.variables = {}
        self.size = size

        self.errors = []
        self.constraints = []
    
    def add_variable(self, vid, vname, board, range=None, var_type=Int):
        self.variables[vid] = Variable(vid, vname, board, v_range=range)
        for c in self.variables[vid].get_basic_constraints():
            self.constraints.append(c)

class GlobalContext:
    def __init__(self, board_size=9):
        self.board_size = board_size
        self.constraints_table = {}
        self.variable_table = {}
        self.vars = {}
        self.op_list = {}
        self.function_list = {}
        self.keywords = ["for", "in"]
        self.rules = {}
        self.solver_context = None

        for op_name, op_impl in op_table.items():
            self.register_operator(op_name, op_impl)
        
        self.current_vid = None
        self.current_cid = None
    
    def add_variable(self, var_id, name, board_state, constraints):
        self.vars[var_id] = {
            "id": var_id,
            "name": name,
            "board": board_state,
            "constraints": constraints,
        }
        self.variable_table.setdefault(name, []).append(self.vars[var_id])
        for c in constraints:
            if c['id'] == 0:
                continue
            self.constraints_table.setdefault(c["name"], []).append({
                "variable_id": var_id,
                "constraint": c,
            })
    
    def register_function(self, func_name, func_impl):
        self.function_list[func_name] = func_impl
    
    def register_operator(self, op_name, op_impl):
        self.op_list[op_name] = op_impl
    
    def get_variable(self, var_name):
        if var_name not in self.variable_table:
            raise NameNotFoundError(f"Variable '{var_name}' not found in context.")
        candidates = self.variable_table[var_name]
        for var in candidates:
            if var["id"] == self.current_vid:
                return var
        raise NameNotFoundError(f"Ambiguous variable name '{var_name}' in context.")
    
    def get_constraint(self, constraint_name):
        ctx_constraint_id = self.current_cid
        ctx_var_id = self.current_vid
        if constraint_name not in self.constraints_table:
            raise NameNotFoundError(f"Constraint '{constraint_name}' not found in context.")
        candidates = self.constraints_table[constraint_name]
        for c in candidates:
            if c["constraint"]["id"] == ctx_constraint_id:
                return c["constraint"]
        scoped_candidates = [c for c in candidates if c["variable_id"] == ctx_var_id]
        if len(scoped_candidates) == 1:
            return scoped_candidates[0]["constraint"]
        raise NameNotFoundError(f"Ambiguous constraint name '{constraint_name}' in context.")
    
    def init_solver(self):
        self.solver_context = SolverContext(self.board_size)
        for var_id, var in self.vars.items():
            self.solver_context.add_variable(var_id, var["name"], var["board"])

    def bind(self, cid, vid):
        self.current_cid = cid
        self.current_vid = vid

    def get_current_variable(self):
        if self.current_vid is None:
            raise NameNotFoundError("No variable currently bound in context.")
        return self.vars[self.current_vid]
    
    def get_current_constraint(self):
        if self.current_cid is None:
            raise NameNotFoundError("No constraint currently bound in context.")
        for c_list in self.constraints_table.values():
            for c in c_list:
                if c["constraint"]["id"] == self.current_cid:
                    return c["constraint"]
        raise NameNotFoundError("Current constraint not found in context.")

    def get_current_region(self):
        constraint = self.get_current_constraint()
        return constraint["region"]
    
    def get_solver_variable(self, var_name):
        var = self.get_variable(var_name)
        return self.solver_context.variables[var["id"]]
    
    def to_dict(self):
        return self.vars
    
    def to_editor_context(self):
        var_dict = set()
        function_dict = set(self.function_list.keys())

        for var_id, var in self.vars.items():
            if var["name"] in self.keywords or len(var["name"]) == 0:
                continue
            var_dict.add(var["name"])
        
        for c_name, c_list in self.constraints_table.items():
            if c_name in self.keywords or len(c_list) == 0:
                continue
            var_dict.add(c_name)
        
        return {
            "variables": var_dict,
            "functions": function_dict,
            "keywords": self.keywords,
        }