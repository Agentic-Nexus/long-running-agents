import './Home.css';

const Home = () => {
  return (
    <div className="home">
      <h2>欢迎使用股票分析系统</h2>
      <div className="home-cards">
        <div className="home-card">
          <h3>股票搜索</h3>
          <p>搜索和查看股票信息</p>
        </div>
        <div className="home-card">
          <h3>分析报告</h3>
          <p>查看股票分析报告</p>
        </div>
        <div className="home-card">
          <h3>智能问答</h3>
          <p>与AI助手交流</p>
        </div>
      </div>
    </div>
  );
};

export default Home;
