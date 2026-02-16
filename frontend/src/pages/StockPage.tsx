import { useState, useEffect } from 'react';
import { StockSearch } from '../components/StockSearch';
import { StockList } from '../components/StockList';
import { StockChart } from '../components/StockChart';
import { TechnicalIndicators } from '../components/TechnicalIndicators';
import type { StockQuote, StockInfo } from '../types/stock';
import { stockApi } from '../services/stockApi';
import './StockPage.css';

export function StockPage() {
  const [watchedStocks, setWatchedStocks] = useState<string[]>(() => {
    const saved = localStorage.getItem('watchedStocks');
    return saved ? JSON.parse(saved) : [];
  });
  const [selectedStock, setSelectedStock] = useState<string | null>(null);
  const [quote, setQuote] = useState<StockQuote | null>(null);
  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null);
  const [period, setPeriod] = useState<'daily' | 'weekly' | 'monthly'>('daily');

  useEffect(() => {
    localStorage.setItem('watchedStocks', JSON.stringify(watchedStocks));
  }, [watchedStocks]);

  useEffect(() => {
    if (!selectedStock) return;

    const fetchQuote = async () => {
      try {
        const data = await stockApi.getStockQuote(selectedStock);
        setQuote(data);
      } catch (err) {
        console.error('Failed to fetch quote:', err);
      }
    };

    const fetchInfo = async () => {
      try {
        const data = await stockApi.getStockInfo(selectedStock);
        setStockInfo(data);
      } catch (err) {
        console.error('Failed to fetch info:', err);
      }
    };

    fetchQuote();
    fetchInfo();

    const interval = setInterval(fetchQuote, 10000);
    return () => clearInterval(interval);
  }, [selectedStock]);

  const handleStockSelect = (code: string) => {
    if (!watchedStocks.includes(code)) {
      setWatchedStocks((prev) => [...prev, code]);
    }
    setSelectedStock(code);
  };

  const removeStock = (code: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setWatchedStocks((prev) => prev.filter((c) => c !== code));
    if (selectedStock === code) {
      setSelectedStock(null);
    }
  };

  return (
    <div className="stock-page">
      <header className="stock-page-header">
        <h1>股票分析系统</h1>
      </header>

      <div className="stock-page-content">
        <aside className="stock-sidebar">
          <StockSearch onStockSelect={handleStockSelect} />
          <div className="watched-stocks">
            <h3>自选股票</h3>
            <StockList
              codes={watchedStocks}
              onStockSelect={(code) => setSelectedStock(code)}
            />
          </div>
        </aside>

        <main className="stock-main">
          {selectedStock ? (
            <>
              <div className="stock-header">
                <div className="stock-title">
                  <h2>{stockInfo?.name || selectedStock}</h2>
                  <span className="stock-code">{selectedStock}</span>
                  {stockInfo?.industry && <span className="stock-industry">{stockInfo.industry}</span>}
                </div>
                {quote && (
                  <div className="stock-quote">
                    <span className="quote-price">{quote.price.toFixed(2)}</span>
                    <span className={`quote-change ${quote.change >= 0 ? 'positive' : 'negative'}`}>
                      {quote.change >= 0 ? '+' : ''}
                      {quote.change.toFixed(2)} ({quote.change_percent.toFixed(2)}%)
                    </span>
                  </div>
                )}
              </div>

              <div className="stock-chart-section">
                <div className="period-selector">
                  <button
                    className={period === 'daily' ? 'active' : ''}
                    onClick={() => setPeriod('daily')}
                  >
                    日线
                  </button>
                  <button
                    className={period === 'weekly' ? 'active' : ''}
                    onClick={() => setPeriod('weekly')}
                  >
                    周线
                  </button>
                  <button
                    className={period === 'monthly' ? 'active' : ''}
                    onClick={() => setPeriod('monthly')}
                  >
                    月线
                  </button>
                </div>
                <StockChart code={selectedStock} period={period} />
              </div>

              <TechnicalIndicators code={selectedStock} />

              {stockInfo && (
                <div className="stock-info">
                  <h3>股票信息</h3>
                  <div className="info-grid">
                    <div className="info-item">
                      <span className="info-label">市场:</span>
                      <span className="info-value">{stockInfo.market}</span>
                    </div>
                    {stockInfo.listing_date && (
                      <div className="info-item">
                        <span className="info-label">上市日期:</span>
                        <span className="info-value">{stockInfo.listing_date}</span>
                      </div>
                    )}
                    {stockInfo.total_shares && (
                      <div className="info-item">
                        <span className="info-label">总股本:</span>
                        <span className="info-value">{stockInfo.total_shares}</span>
                      </div>
                    )}
                    {stockInfo.circulating_shares && (
                      <div className="info-item">
                        <span className="info-label">流通股本:</span>
                        <span className="info-value">{stockInfo.circulating_shares}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="stock-empty">
              <p>请搜索并选择一只股票</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
