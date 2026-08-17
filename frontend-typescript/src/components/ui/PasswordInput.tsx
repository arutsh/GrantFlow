import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import Input from "./Input";

type PasswordInputProps = Omit<React.ComponentProps<typeof Input>, "type" | "rightElement">;

export default function PasswordInput(props: PasswordInputProps) {
  const [visible, setVisible] = useState(false);

  return (
    <Input
      {...props}
      type={visible ? "text" : "password"}
      rightElement={
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="text-gray-400 hover:text-gray-600"
          aria-label={visible ? "Hide password" : "Show password"}
        >
          {visible ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      }
    />
  );
}
