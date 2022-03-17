from enum import Enum


class RequestAction(str, Enum):
    Install = "install"
    UnInstall = "uninstall"
    Upgrade = "upgrade"
