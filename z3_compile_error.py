
class NameNotFoundError(Exception):
    """Raised when a name is not found in the current context."""
    pass

class Z3CompileError(Exception):
    """Raised when there is an error during the compilation of constraints to Z3."""
    pass

class Z3RuntimeError(Exception):
    """Raised when there is an error during the execution of Z3 solver."""
    pass