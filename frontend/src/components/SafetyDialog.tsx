import React from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose } from "@/components/ui/dialog";

interface SafetyDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  message?: string;
}

export function SafetyDialog({ isOpen, onOpenChange, onConfirm, message }: SafetyDialogProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Safety Halt Triggered</DialogTitle>
          <DialogDescription>
            {message || "The agent has prepared an action but requires your explicit confirmation to proceed (e.g. submitting an application)."}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="mt-4">
          <DialogClose asChild>
            <button className="px-4 py-2 bg-secondary text-secondary-foreground rounded hover:bg-secondary/80">
              Cancel
            </button>
          </DialogClose>
          <button onClick={() => {
            onConfirm();
            onOpenChange(false);
          }} className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/80">
            Confirm & Submit
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
