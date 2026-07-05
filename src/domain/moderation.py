from enum import Enum


class ModerationAction(str, Enum):
    ALLOW = "allow"
    FLAG = "flag"
    BLOCK = "block"
