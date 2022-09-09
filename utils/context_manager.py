# This script stores information about the current state of the program
# By storing the "context" of all current operations, errors reports can be generated much easier

class Context:
    task: str = "initializing"  # task always with "ing" at the end
    software: str = "main program"
    failure_severity: int = 10


context = Context()
