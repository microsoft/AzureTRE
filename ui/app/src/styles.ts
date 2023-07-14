import { getTheme } from "@fluentui/react";

const { palette } = getTheme();

export const successButtonStyles = {
  root: {
    background: palette.green,
    color: palette.white,
    borderColor: palette.green
  },
  rootDisabled: {
    background: 'rgb(16 124 16 / 60%)',
    color: palette.white,
    borderColor: palette.green,
    iconColor: palette.white
  },
  iconDisabled: {
    color: palette.white
  }
}

export const destructiveButtonStyles = {
  root: {
    marginRight: 5,
    background: palette.red,
    color: palette.white,
    borderColor: palette.red
  },
  rootDisabled: {
    background: 'rgb(232 17 35 / 60%)',
    color: palette.white,
    borderColor: palette.red
  },
  iconDisabled: {
    color: palette.white
  }
}
