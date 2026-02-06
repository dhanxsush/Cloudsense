import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Menu, X, LogOut, User, Bell } from 'lucide-react';
import apiClient from '@/services/api';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export default function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    const checkAuth = () => {
      const currentUser = apiClient.getUser();
      const isAuth = apiClient.isAuthenticated();
      setUser(currentUser);
      setIsLoggedIn(isAuth);
    };
    
    checkAuth();
    // Re-check auth state when the component mounts or when returning from login
    window.addEventListener('focus', checkAuth);
    return () => window.removeEventListener('focus', checkAuth);
  }, []);

  const handleLogout = () => {
    apiClient.logout();
    setUser(null);
    setIsLoggedIn(false);
    navigate('/');
  };

  const navigateTo = (path) => {
    navigate(path);
    setMobileMenuOpen(false);
  };

  return (
    <nav className="bg-slate-900 border-b border-slate-800 sticky top-0 z-50 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <button
            onClick={() => navigateTo('/')}
            className="flex items-center space-x-2 cursor-pointer hover:opacity-80 transition-opacity"
          >
            <span className="text-2xl font-bold text-cyan-400">CloudSense</span>
          </button>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-1">
            <button
              onClick={() => navigateTo('/')}
              className="px-3 py-2 text-slate-300 hover:text-cyan-400 transition-colors text-sm font-medium rounded hover:bg-slate-800/50"
            >
              Home
            </button>
            {isLoggedIn && (
              <>
                <button
                  onClick={() => navigateTo('/dashboard')}
                  className="px-3 py-2 text-slate-300 hover:text-cyan-400 transition-colors text-sm font-medium rounded hover:bg-slate-800/50"
                >
                  Dashboard
                </button>
                <button
                  onClick={() => navigateTo('/analysis')}
                  className="px-3 py-2 text-slate-300 hover:text-cyan-400 transition-colors text-sm font-medium rounded hover:bg-slate-800/50"
                >
                  Analysis
                </button>
                <button
                  onClick={() => navigateTo('/chat')}
                  className="px-3 py-2 text-slate-300 hover:text-cyan-400 transition-colors text-sm font-medium rounded hover:bg-slate-800/50"
                >
                  Chatbot
                </button>
              </>
            )}
          </div>

          {/* Right Side Actions */}
          <div className="hidden md:flex items-center space-x-3">
            {isLoggedIn && user ? (
              <>
                {/* Notification Bell */}
                <div className="relative group">
                  <button className="p-2.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors duration-200">
                    <Bell className="w-5 h-5" />
                    <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                  </button>
                  <div className="absolute right-0 mt-1 w-48 bg-slate-800 rounded-lg border border-slate-700 shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 p-3 text-xs text-slate-300">
                    <p className="font-semibold mb-1 text-slate-200">Notifications</p>
                    <p>No new notifications</p>
                  </div>
                </div>

                {/* User Profile Dropdown */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button className="flex items-center space-x-2 px-3 py-1.5 rounded-lg hover:bg-slate-800 transition-colors duration-200 group">
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-cyan-500 to-cyan-600 flex items-center justify-center shadow-lg">
                        <User className="w-4 h-4 text-white" />
                      </div>
                      <span className="text-sm font-medium text-slate-300 group-hover:text-slate-100 max-w-[120px] truncate">
                        {user.username || 'User'}
                      </span>
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="bg-slate-800 border-slate-700 shadow-xl">
                    <div className="px-2 py-2 text-sm">
                      <p className="font-semibold text-slate-100">{user.username}</p>
                      <p className="text-xs text-slate-400 break-words max-w-[200px]">{user.email}</p>
                    </div>
                    <DropdownMenuSeparator className="bg-slate-700" />
                    <DropdownMenuItem
                      onClick={() => navigate('/settings')}
                      className="text-slate-300 cursor-pointer hover:bg-slate-700 hover:text-slate-100"
                    >
                      Settings
                    </DropdownMenuItem>
                    <DropdownMenuSeparator className="bg-slate-700" />
                    <DropdownMenuItem
                      onClick={handleLogout}
                      className="text-red-400 cursor-pointer hover:bg-slate-700 hover:text-red-300"
                    >
                      <LogOut className="w-4 h-4 mr-2" />
                      Logout
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : (
              <>
                <Button
                  onClick={() => navigate('/login')}
                  variant="outline"
                  size="sm"
                  className="text-slate-300 border-slate-600 hover:bg-slate-800 hover:text-slate-100"
                >
                  Login
                </Button>
                <Button
                  onClick={() => navigate('/signup')}
                  size="sm"
                  className="bg-cyan-600 hover:bg-cyan-700 text-white font-medium"
                >
                  Sign Up
                </Button>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 text-slate-300 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition-colors"
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden pb-4 space-y-1 bg-slate-800/50 rounded-b-lg">
            <button
              onClick={() => navigateTo('/')}
              className="block w-full text-left px-4 py-2 text-slate-300 hover:text-cyan-400 hover:bg-slate-700 rounded transition-colors"
            >
              Home
            </button>
            {isLoggedIn && (
              <>
                <button
                  onClick={() => navigateTo('/dashboard')}
                  className="block w-full text-left px-4 py-2 text-slate-300 hover:text-cyan-400 hover:bg-slate-700 rounded transition-colors"
                >
                  Dashboard
                </button>
                <button
                  onClick={() => navigateTo('/analysis')}
                  className="block w-full text-left px-4 py-2 text-slate-300 hover:text-cyan-400 hover:bg-slate-700 rounded transition-colors"
                >
                  Analysis
                </button>
                <button
                  onClick={() => navigateTo('/chat')}
                  className="block w-full text-left px-4 py-2 text-slate-300 hover:text-cyan-400 hover:bg-slate-700 rounded transition-colors"
                >
                  Chatbot
                </button>
              </>
            )}
            <div className="pt-2 border-t border-slate-700 space-y-1">
              {user ? (
                <>
                  <button
                    onClick={() => navigate('/settings')}
                    className="block w-full text-left px-4 py-2 text-slate-300 hover:text-cyan-400 hover:bg-slate-700 rounded transition-colors"
                  >
                    Settings
                  </button>
                  <button
                    onClick={handleLogout}
                    className="block w-full text-left px-4 py-2 text-red-400 hover:text-red-300 hover:bg-slate-700 rounded transition-colors"
                  >
                    <LogOut className="w-4 h-4 mr-2 inline" />
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => navigate('/login')}
                    className="block w-full text-left px-4 py-2 text-slate-300 hover:text-cyan-400 hover:bg-slate-700 rounded transition-colors"
                  >
                    Login
                  </button>
                  <button
                    onClick={() => navigate('/signup')}
                    className="block w-full text-left px-4 py-2 text-cyan-400 hover:text-cyan-300 hover:bg-slate-700 rounded font-medium transition-colors"
                  >
                    Sign Up
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
