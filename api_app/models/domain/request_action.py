from enum import StrEnum


class RequestAction(StrEnum):
    Install = "install"
    UnInstall = "uninstall"
    Upgrade = "upgrade"
