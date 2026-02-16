import { NavLink } from 'react-router-dom';
import { Home, LineChart, MessageSquare, Search, Settings } from 'lucide-react';
import { useAppStore } from '../store';
import './Sidebar.css';

const menuItems = [
  { path: '/', icon: Home, label: '首页' },
  { path: '/stocks', icon: Search, label: '股票搜索' },
  { path: '/analysis', icon: LineChart, label: '分析报告' },
  { path: '/chat', icon: MessageSquare, label: '智能问答' },
  { path: '/settings', icon: Settings, label: '设置' },
];

const Sidebar = () => {
  const { sidebarCollapsed } = useAppStore();

  return (
    <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
      <nav className="sidebar-nav">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `sidebar-item ${isActive ? 'active' : ''}`
            }
          >
            <item.icon size={20} />
            {!sidebarCollapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
};

export default Sidebar;
