"""
The main context handler to enable more precise error logs etc.
"""

class Context:
    """
    Describes the current context that the program is in
    """
    task: str = "initializing"  # task always with "ing" at the end
    software: str = "main program"
    failure_severity: int = 10


context = Context()
