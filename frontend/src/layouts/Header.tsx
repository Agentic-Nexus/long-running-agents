import { Menu } from 'lucide-react';
import { useAppStore } from '../store';
import './Header.css';

const Header = () => {
  const { toggleSidebar } = useAppStore();

  return (
    <header className="header">
      <div className="header-left">
        <button className="menu-button" onClick={toggleSidebar}>
          <Menu size={20} />
        </button>
        <h1 className="header-title">股票分析系统</h1>
      </div>
      <div className="header-right">
        <span className="header-user">用户</span>
      </div>
    </header>
  );
};

export default Header;
