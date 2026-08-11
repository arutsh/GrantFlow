import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, LogOut, Menu, Settings } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

function initialsFor(name?: string | null): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() ?? "").join("") || "?";
}

// Global user menu, rendered once by DashboardLayout so it's present on
// every authenticated page — the single place to log out or reach account
// settings, rather than each page rolling its own. Below `md:` it also
// carries the button that opens the off-canvas nav drawer, since the
// drawer itself is off-screen and can't host its own opener while closed.
export function TopBar({ onOpenMenu }: { onOpenMenu: () => void }) {
  const { username, logout } = useAuth();
  const navigate = useNavigate();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="h-16 flex-shrink-0 flex items-center justify-between px-4 sm:px-6 bg-white border-b border-slate-200">
      <button
        type="button"
        onClick={onOpenMenu}
        aria-label="Open navigation menu"
        className="md:hidden flex items-center justify-center w-9 h-9 -ml-1 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors"
      >
        <Menu size={22} />
      </button>
      <div className="relative ml-auto" ref={menuRef}>
        <button
          type="button"
          onClick={() => setIsMenuOpen((open) => !open)}
          aria-haspopup="menu"
          aria-expanded={isMenuOpen}
          className="flex items-center gap-2.5 pl-2 pr-3 py-1.5 rounded-full hover:bg-slate-100 transition-colors"
        >
          <span className="w-8 h-8 rounded-full bg-slate-700 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">
            {initialsFor(username)}
          </span>
          <span className="text-sm font-medium text-slate-700 hidden sm:inline max-w-[10rem] truncate">
            {username}
          </span>
          <ChevronDown
            size={16}
            className={`text-slate-400 transition-transform ${isMenuOpen ? "rotate-180" : ""}`}
          />
        </button>

        {isMenuOpen && (
          <div
            role="menu"
            className="absolute right-0 mt-2 w-52 bg-white border border-slate-200 rounded-xl shadow-lg py-1.5 z-30"
          >
            <div className="px-4 py-2 border-b border-slate-100">
              <p className="text-sm font-semibold text-slate-900 truncate">{username}</p>
            </div>
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setIsMenuOpen(false);
                navigate("/settings");
              }}
              className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <Settings size={16} />
              Account Settings
            </button>
            <button
              type="button"
              role="menuitem"
              onClick={handleLogout}
              className="w-full flex items-center gap-2.5 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <LogOut size={16} />
              Logout
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
