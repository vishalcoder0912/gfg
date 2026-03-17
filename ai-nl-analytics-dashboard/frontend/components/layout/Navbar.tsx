import React from 'react';
import { Search, Bell, User, HelpCircle } from 'lucide-react';

const Navbar = () => {
  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-8 sticky top-0 z-10">
      <div className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <input
            type="text"
            placeholder="Search datasets or insights..."
            className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="p-2 text-gray-500 hover:bg-gray-50 rounded-lg transition-colors relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
        </button>
        <button className="p-2 text-gray-500 hover:bg-gray-50 rounded-lg transition-colors">
          <HelpCircle className="w-5 h-5" />
        </button>
        <div className="h-8 w-px bg-gray-200 mx-2"></div>
        <button className="flex items-center gap-3 pl-2 group">
          <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-sm border border-indigo-200 group-hover:bg-indigo-200 transition-colors">
            JD
          </div>
          <div className="text-left hidden sm:block">
            <p className="text-sm font-bold text-gray-900 leading-none">John Doe</p>
            <p className="text-xs text-gray-500 mt-1">Admin User</p>
          </div>
        </button>
      </div>
    </header>
  );
};

export default Navbar;
