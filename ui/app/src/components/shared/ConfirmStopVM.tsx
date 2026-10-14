import React from "react";
import { DefaultButton, Dialog, DialogFooter, PrimaryButton } from "@fluentui/react";

interface ConfirmStopVMProps {
  onConfirm: () => void;
  onDismiss: () => void;
}

export const ConfirmStopVM: React.FunctionComponent<ConfirmStopVMProps> = (props: ConfirmStopVMProps) => (
  <Dialog
    hidden={false}
    onDismiss={props.onDismiss}
    dialogContentProps={{
      title: "Stop VM?",
      subText: "This powers off the VM. The resource remains enabled in TRE and can be started again.",
    }}
  >
    <DialogFooter>
      <PrimaryButton text="Stop VM" onClick={props.onConfirm} />
      <DefaultButton text="Cancel" onClick={props.onDismiss} />
    </DialogFooter>
  </Dialog>
);
