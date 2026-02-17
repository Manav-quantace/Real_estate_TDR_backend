from enum import Enum


class WorkflowType(str, Enum):
    # EXACTLY 4 workflows
    saleable = "saleable"
    slum = "slum"
    subsidized = "subsidized"
    clearland = "clearland"