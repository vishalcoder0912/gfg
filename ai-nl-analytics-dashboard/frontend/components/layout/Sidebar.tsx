import React from 'react';
import { LayoutDashboard, BarChart3, MessageSquare, Settings, Database } from 'lucide-react';

const Sidebar = () => {
  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', active: true },
    { icon: Database, label: 'Datasets', active: false },
    { icon: BarChart3, label: 'Analytics', active: false },
    { icon: MessageSquare, label: 'AI Chat', active: false },
    { icon: Settings, label: 'Settings', active: false },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen flex flex-col">
      <div className="p-6">
        <h1 className="text-2xl font-bold text-indigo-600 flex items-center gap-2">
          <BarChart3 className="w-8 h-8" />
          <span>InsightAI</span>
        </h1>
      </div>
      
      <nav className="flex-1 px-4 py-4 space-y-1">
        {menuItems.map((item) => (
          <button
            key={item.label}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              item.active 
                ? 'bg-indigo-50 text-indigo-700' 
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`}
          >
            <item.icon className={`w-5 h-5 ${item.active ? 'text-indigo-600' : 'text-gray-400'}`} />
            {item.label}
          </button>
        ))}
      </nav>

      <div className="p-4 border-t border-gray-100">
        <div className="bg-indigo-600 rounded-xl p-4 text-white">
          <p className="text-xs font-medium opacity-80 uppercase tracking-wider mb-1">Hackathon Pro</p>
          <p className="text-sm font-bold mb-3">Upgrade for more AI</p>
          <button className="w-full py-2 bg-white text-indigo-600 rounded-lg text-xs font-bold hover:bg-indigo-50 transition-colors">
            Get Pro
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
