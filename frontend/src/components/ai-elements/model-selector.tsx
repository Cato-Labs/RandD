"use client";

import { useControllableState } from "@radix-ui/react-use-controllable-state";
import { CheckIcon } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";
import { createContext, useContext, useMemo } from "react";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

interface ModelSelectorContextValue {
  value: string | undefined;
  setValue: (value: string | undefined) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
}

const ModelSelectorContext = createContext<ModelSelectorContextValue | null>(
  null
);

export const useModelSelector = () => {
  const context = useContext(ModelSelectorContext);
  if (!context) {
    throw new Error(
      "ModelSelector components must be used within ModelSelector"
    );
  }
  return context;
};

export type ModelSelectorProps = ComponentProps<typeof Dialog> & {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string | undefined) => void;
};

export const ModelSelector = ({
  value: valueProp,
  defaultValue,
  onValueChange,
  open: openProp,
  defaultOpen = false,
  onOpenChange,
  children,
  ...props
}: ModelSelectorProps) => {
  const [value, setValue] = useControllableState({
    defaultProp: defaultValue,
    onChange: onValueChange,
    prop: valueProp,
  });

  const [open, setOpen] = useControllableState({
    defaultProp: defaultOpen,
    onChange: onOpenChange,
    prop: openProp,
  });

  const modelSelectorContext = useMemo(
    () => ({ open, setOpen, setValue, value }),
    [value, setValue, open, setOpen]
  );

  return (
    <ModelSelectorContext.Provider value={modelSelectorContext}>
      <Dialog onOpenChange={setOpen} open={open} {...props}>
        {children}
      </Dialog>
    </ModelSelectorContext.Provider>
  );
};

export type ModelSelectorTriggerProps = ComponentProps<typeof DialogTrigger>;

export const ModelSelectorTrigger = (props: ModelSelectorTriggerProps) => (
  <DialogTrigger {...props} />
);

export type ModelSelectorContentProps = ComponentProps<typeof DialogContent> & {
  title?: ReactNode;
};

export const ModelSelectorContent = ({
  className,
  children,
  title = "Model Selector",
  ...props
}: ModelSelectorContentProps) => (
  <DialogContent
    aria-describedby={undefined}
    className={cn("p-0", className)}
    {...props}
  >
    <DialogTitle className="sr-only">{title}</DialogTitle>
    <Command>{children}</Command>
  </DialogContent>
);

export type ModelSelectorInputProps = ComponentProps<typeof CommandInput>;

export const ModelSelectorInput = (props: ModelSelectorInputProps) => (
  <CommandInput {...props} />
);

export type ModelSelectorListProps = ComponentProps<typeof CommandList>;

export const ModelSelectorList = (props: ModelSelectorListProps) => (
  <CommandList {...props} />
);

export type ModelSelectorEmptyProps = ComponentProps<typeof CommandEmpty>;

export const ModelSelectorEmpty = (props: ModelSelectorEmptyProps) => (
  <CommandEmpty {...props} />
);

export type ModelSelectorGroupProps = ComponentProps<typeof CommandGroup>;

export const ModelSelectorGroup = (props: ModelSelectorGroupProps) => (
  <CommandGroup {...props} />
);

export type ModelSelectorItemProps = ComponentProps<typeof CommandItem>;

export const ModelSelectorItem = ({
  className,
  value,
  onSelect,
  children,
  ...props
}: ModelSelectorItemProps) => {
  const { value: selected, setValue, setOpen } = useModelSelector();
  const isSelected = value !== undefined && selected === value;

  return (
    <CommandItem
      className={cn("items-start gap-3", className)}
      onSelect={(selectedValue) => {
        setValue(selectedValue);
        setOpen(false);
        onSelect?.(selectedValue);
      }}
      value={value}
      {...props}
    >
      {children}
      <CheckIcon
        className={cn(
          "ml-auto size-4 shrink-0 self-center",
          isSelected ? "opacity-100" : "opacity-0"
        )}
      />
    </CommandItem>
  );
};

export type ModelSelectorNameProps = ComponentProps<"span">;

export const ModelSelectorName = ({
  className,
  ...props
}: ModelSelectorNameProps) => (
  <span className={cn("font-medium text-sm", className)} {...props} />
);

export type ModelSelectorVendorProps = ComponentProps<"span">;

export const ModelSelectorVendor = ({
  className,
  ...props
}: ModelSelectorVendorProps) => (
  <span
    className={cn(
      "rounded-sm bg-muted px-1.5 py-0.5 text-muted-foreground text-xs",
      className
    )}
    {...props}
  />
);

export type ModelSelectorDescriptionProps = ComponentProps<"span">;

export const ModelSelectorDescription = ({
  className,
  ...props
}: ModelSelectorDescriptionProps) => (
  <span
    className={cn("text-muted-foreground text-xs", className)}
    {...props}
  />
);

export type ModelSelectorModelIdProps = ComponentProps<"code">;

export const ModelSelectorModelId = ({
  className,
  ...props
}: ModelSelectorModelIdProps) => (
  <code
    className={cn("font-mono text-[11px] text-muted-foreground", className)}
    {...props}
  />
);
