import { editBudget, createBudget } from "@/api/budgetApi";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import { useMutation } from "@tanstack/react-query";

import { useEffect, useMemo, useRef, useState } from "react";
import { BudgetLine, NewBudgetLine } from "../types/budget";
import { useDetailedBudget } from "../SingleBudgetViewContext";
import Input from "@/components/ui/Input";
import Select from "@/components/ui/Select";
import { createBudgetLine, updateBudgetLines } from "@/api/gatewayApi";

interface ExtraField {
  key: string;
  value: string;
}

export function AddBudgetLineModal({
  budgetLine,
  isOpen,
  onClose,
  onSave,
}: {
  budgetLine: BudgetLine | undefined;
  isOpen: boolean;
  onClose: () => void;
  onSave: (line: any) => void; // Replace `any` with proper BudgetLine type
}) {
  const {
    budget,
    setBudget,
    budgetCategories,
    existingExtraKeys,
    budgetCategoryNames,
  } = useDetailedBudget();
  const [categoryName, setCategoryName] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [categoryNameError, setCategoryNameError] = useState<string | null>(
    null,
  );
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState<number>(0);
  const [extraFields, setExtraFields] = useState<ExtraField[]>([]);
  const fieldRefs = useRef<Record<string, HTMLInputElement>>({});
  const [errorFields, setErrorFields] = useState<Set<string>>(new Set());
  const [serverError, setServerError] = useState<boolean | string | null>(
    false,
  );

  useEffect(() => {
    if (budgetLine) {
      // setCategoryId(budgetLine.category?.id ?? "");
      setCategoryName(budgetLine.category?.id ?? "");
      setDescription(budgetLine.description ?? "");
      setAmount(budgetLine.amount ?? 0);
      setExtraFields(
        Object.entries(budgetLine.extra_fields ?? {}).map(([key, value]) => ({
          key,
          value: String(value ?? ""),
        })),
      );
    } else {
      // Reset when adding
      setNewCategory("");
      setDescription("");
      setAmount(0);
      setExtraFields([]);
    }
  }, [budgetLine]);

  // When modal opens, prepopulate existing fields
  useEffect(() => {
    if (isOpen) {
      const prefilled =
        existingExtraKeys?.map((key) => ({
          key,
          value: "",
        })) ?? [];
      setExtraFields(prefilled);
    }
  }, [isOpen, existingExtraKeys]);

  const handleNewCategoryName = (name: string) => {
    const found = budgetCategoryNames.find(
      (item) => item.toLocaleLowerCase() === name.trim().toLocaleLowerCase(),
    );
    setNewCategory(name);

    if (!found) {
      setCategoryNameError(null);
    } else {
      setCategoryNameError("The category exists, please choose from the list");
    }
  };
  const handleAddExtraField = () => {
    setExtraFields([...extraFields, { key: "", value: "" }]);
  };

  const handleRemoveExtraField = (index: number) => {
    setExtraFields(extraFields.filter((_, i) => i !== index));
  };

  const handleExtraFieldChange = (
    index: number,
    field: "key" | "value",
    value: string,
  ) => {
    const newFields = [...extraFields];
    newFields[index][field] = value;
    if (field === "key") {
      const lowerValue = value.toLowerCase().trim();
      const duplicateInNew = newFields.some(
        (f, i) => i !== index && f.key.toLowerCase().trim() === lowerValue,
      );
      if (duplicateInNew) {
        setErrorFields((prev) => new Set(prev).add(`key-${index}`));
      } else {
        setErrorFields((prev) => {
          const newSet = new Set(prev);
          newSet.delete(`key-${index}`);
          return newSet;
        });
      }
    }

    setExtraFields(newFields);
  };

  const mutation = useMutation({
    mutationFn: (newLine: NewBudgetLine | BudgetLine) => {
      if ("id" in newLine) {
        return updateBudgetLines(newLine);
      }

      return createBudgetLine(newLine);
    },

    onSuccess: (newBudgetLine) => {
      setServerError(false);
      if (!budget) return;
      if (budgetLine) {
        // Editing existing line
        const updatedLines = budget.lines?.map((line) =>
          line.id === newBudgetLine.id ? newBudgetLine : line,
        );
        const updatedBudget = {
          ...budget,
          lines: updatedLines,
        };
        setBudget(updatedBudget);
        onClose();
        return;
      } else {
        const updatedBudget = {
          ...budget,
          lines: [...(budget?.lines ?? []), newBudgetLine],
        };
        setBudget(updatedBudget);
      }

      onClose();
    },
    onError: () => {
      setServerError("Failed to Creat, Please try again");
    },
  });

  const handleSave = () => {
    // Construct extraFields as object
    const extraFieldsObj = extraFields.reduce(
      (acc, { key, value }) => {
        if (key && value) acc[key] = value;
        return acc;
      },
      {} as Record<string, string>,
    );

    const newLine = {
      budget_id: budget?.id ?? "",
      description: description,
      amount: amount,
      extra_fields: extraFieldsObj,
      category_name: newCategory,
      // Empty string when no category is picked (the Select's default,
      // unselected state) must become undefined, not "" — the backend
      // validates this as a UUID and 422s on an empty string.
      category_id:
        categoryName && categoryName !== "__new" ? categoryName : undefined,
    };

    if (budgetLine) {
      const existingLine = {
        ...newLine,
        id: budgetLine.id,
      } satisfies BudgetLine;
      mutation.mutate(existingLine);
    } else {
      mutation.mutate(newLine);
    }
    // onSave(newLine);

    // Reset form
    setCategoryName("");
    setDescription("");
    setAmount(0);
    setExtraFields([]);
  };

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={() => onClose()} title="New Budget Line">
      {/* Category */}
      <Select
        label="Category"
        name="category"
        value={categoryName}
        onChange={(e) => {
          setCategoryName(e);
        }}
        placeholder="-- Select Category --"
        allowCreate={true}
        createLabel="Create New..."
        options={
          budgetCategories?.map((c) => ({ label: c.name, value: c.id })) ?? []
        }
      />
      {categoryName === "__new" && (
        <Input
          name="categories"
          type="text"
          placeholder="New category name"
          value={newCategory}
          onChange={(e) => handleNewCategoryName(e.target.value)}
          showLabel={false}
          errorMsg={categoryNameError}
        />
      )}

      {/* Description */}
      <Input
        label="Description"
        name="description"
        type="text"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />

      {/* Amount */}
      <Input
        label="Amount"
        name="amount"
        type="number"
        value={amount}
        onChange={(e) => setAmount(parseFloat(e.target.value))}
      />

      {/* Extra Fields */}
      <div className="mb-4">
        <h3 className="font-semibold mb-2">Extra Fields</h3>
        {extraFields.map((field, index) => (
          <div key={index} className="flex gap-2 mb-2">
            <Input
              name={field.key}
              showLabel={false}
              type="text"
              placeholder="Key"
              value={field.key}
              onChange={(e) =>
                handleExtraFieldChange(index, "key", e.target.value)
              }
              disabled={
                existingExtraKeys?.includes(field.key) &&
                !errorFields.has(`key-${index}`)
              } // existing keys locked
              ref={(el) => {
                if (el) fieldRefs.current[`key-${index}`] = el;
              }}
              errorMsg={
                errorFields.has(`key-${index}`)
                  ? "This key already exists"
                  : null
              }
            />
            <Input
              name={field.value}
              type="text"
              showLabel={false}
              placeholder="Value"
              value={field.value}
              onChange={(e) =>
                handleExtraFieldChange(index, "value", e.target.value)
              }
            />
            {!existingExtraKeys?.includes(field.key) && (
              <Button
                type="button"
                onClick={() => handleRemoveExtraField(index)}
                variant="simpleX"
              >
                X
              </Button>
            )}
          </div>
        ))}
        <Button type="button" variant="text" onClick={handleAddExtraField}>
          + Add Field
        </Button>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button variant="primary" onClick={handleSave}>
          Save
        </Button>
      </div>
    </Modal>
  );
}
