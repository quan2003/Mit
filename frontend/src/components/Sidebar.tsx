"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, History, BarChart2, Leaf, Video } from "lucide-react";

const navItems = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/live", label: "Camera Live", icon: Video },
    { href: "/history", label: "Lịch Sử", icon: History },
    { href: "/stats", label: "Thống Kê", icon: BarChart2 },
];

export default function Sidebar() {
    const pathname = usePathname();
    return (
        <aside className="w-60 bg-gray-900 border-r border-gray-800 flex flex-col">
            {/* Logo */}
            <div className="flex items-center gap-3 px-6 py-5 border-b border-gray-800">
                <div className="w-9 h-9 rounded-xl bg-emerald-500 flex items-center justify-center">
                    <Leaf className="w-5 h-5 text-white" />
                </div>
                <div>
                    <p className="font-bold text-white text-sm">CayMit AI</p>
                    <p className="text-gray-500 text-xs">Disease Detection</p>
                </div>
            </div>

            {/* Nav */}
            <nav className="flex-1 px-3 py-4 space-y-1">
                {navItems.map(({ href, label, icon: Icon }) => {
                    const active = pathname === href;
                    return (
                        <Link
                            key={href}
                            href={href}
                            className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${active
                                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                : "text-gray-400 hover:bg-gray-800 hover:text-white"
                                }`}
                        >
                            <Icon className="w-4 h-4" />
                            {label}
                        </Link>
                    );
                })}
            </nav>

            <div className="px-6 py-4 border-t border-gray-800">
                <p className="text-gray-600 text-xs">v1.0.0 · Cây Mít</p>
            </div>
        </aside>
    );
}
