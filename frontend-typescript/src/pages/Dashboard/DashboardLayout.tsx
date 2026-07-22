import React, { useState } from "react";
import {
  Menu,
  X,
  Home,
  FileText,
  BarChart3,
  HeartHandshake,
  Sparkles,
  Settings,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import Button from "../../components/ui/Button";
import { AIChatPanel } from "@/pages/Budgets/components/AIChatPanel";
import { useAiChat } from "@/context/AiChatContext";
import { useAuth } from "@/context/AuthContext";
import ogfIcon from "@/assets/logos/ogf-icon.svg";
import { Link, NavLink } from "react-router-dom";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [isGranteesExpanded, setIsGranteesExpanded] = useState(false);
  const { isAiOpen, toggleAi } = useAiChat();
  const { isDonor } = useAuth();

  return (
    <div className="flex w-full h-screen bg-gray-50">
      {/* Sidebar */}
      <aside
        className={`
          fixed md:static top-0 left-0 h-full z-20
          bg-slate-700 text-white transition-all duration-300 flex flex-col
          ${isOpen ? "w-64" : "w-16"}
        `}
      >
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-2 overflow-hidden">
            <img src={ogfIcon} alt="" className="h-7 w-auto flex-shrink-0" />
            {isOpen && (
              <span className="font-bold text-base whitespace-nowrap">
                Open Grant <span className="text-teal-400">Flow</span>
              </span>
            )}
          </div>
          <Button
            variant="icon"
            onClick={() => setIsOpen(!isOpen)}
            className="text-white md:hidden"
          >
            {isOpen ? <X size={24} /> : <Menu size={24} />}
          </Button>
        </div>

        <nav className="flex-1">
          <ul className="space-y-1">
            <li>
              <Link
                to="/dashboard"
                className="flex items-center gap-3 px-4 py-2 hover:bg-blue-600/60 rounded transition-colors"
              >
                <Home size={20} />
                {isOpen && <span>Home</span>}
              </Link>
            </li>
            <li>
              <Link
                to="/budgets"
                className="flex items-center gap-3 px-4 py-2 hover:bg-blue-600/60 rounded transition-colors"
              >
                <FileText size={20} />
                {isOpen && <span>Budgets</span>}
              </Link>
            </li>
            <li>
              <Link
                to="/reports"
                className="flex items-center gap-3 px-4 py-2 hover:bg-blue-600/60 rounded transition-colors"
              >
                <BarChart3 size={20} />
                {isOpen && <span>Reports</span>}
              </Link>
            </li>
            {isDonor && <li className="my-2 border-t border-slate-600" />}
            {isDonor && (
              <li>
                <button
                  onClick={() => setIsGranteesExpanded(!isGranteesExpanded)}
                  className="w-full flex items-center gap-3 px-4 py-2 hover:bg-blue-600/60 rounded transition-colors"
                >
                  <HeartHandshake size={20} />
                  {isOpen && (
                    <>
                      <span className="flex-1 text-left">Grantees</span>
                      {isGranteesExpanded ? (
                        <ChevronDown size={16} />
                      ) : (
                        <ChevronRight size={16} />
                      )}
                    </>
                  )}
                </button>
                {isOpen && isGranteesExpanded && (
                  <ul className="mt-1 space-y-1">
                    <li>
                      <Link
                        to="/donor-dashboard"
                        className="block px-4 py-2 pl-11 text-sm hover:bg-blue-600/60 rounded transition-colors"
                      >
                        Overview
                      </Link>
                    </li>
                    <li
                      className="px-4 py-2 pl-11 text-sm text-slate-400 cursor-default"
                      title="Coming soon"
                    >
                      List of Grantees
                    </li>
                    <li
                      className="px-4 py-2 pl-11 text-sm text-slate-400 cursor-default"
                      title="Coming soon"
                    >
                      Budgets
                    </li>
                    <li
                      className="px-4 py-2 pl-11 text-sm text-slate-400 cursor-default"
                      title="Coming soon"
                    >
                      Reports
                    </li>
                  </ul>
                )}
              </li>
            )}
          </ul>
        </nav>

        {/* Settings link pinned above AI Mode */}
        <div className="px-3 pb-1">
          <NavLink
            to="/settings"
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-slate-600 text-slate-300 hover:text-white transition-colors"
          >
            <Settings size={20} className="flex-shrink-0" />
            {isOpen && <span className="text-sm font-medium">Settings</span>}
          </NavLink>
        </div>

        {/* AI Mode button pinned to bottom of sidebar */}
        <div className="p-3 border-t border-slate-600">
          <button
            onClick={toggleAi}
            title="AI Mode"
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
              isAiOpen
                ? "bg-blue-600 text-white"
                : "hover:bg-slate-600 text-slate-300 hover:text-white"
            }`}
          >
            <Sparkles size={20} className="flex-shrink-0" />
            {isOpen && <span className="text-sm font-medium">AI Mode</span>}
          </button>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-10 md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Main content + AI panel */}
      <div className="flex flex-1 overflow-hidden">
        <main className="flex-1 p-8 overflow-auto bg-gray-50">{children}</main>

        {isAiOpen && <AIChatPanel />}
      </div>
    </div>
  );
}
