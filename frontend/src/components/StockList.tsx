import { useState, useEffect } from 'react';
import type { StockQuote } from '../types/stock';
import { stockApi } from '../services/stockApi';

interface StockListProps {
  codes: string[];
  onStockSelect: (code: string) => void;
}

export function StockList({ codes, onStockSelect }: StockListProps) {
  const [quotes, setQuotes] = useState<Map<string, StockQuote>>(new Map());
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchQuotes = async () => {
      if (codes.length === 0) return;

      setLoading(true);
      try {
        const quotePromises = codes.map(async (code) => {
          try {
            const quote = await stockApi.getStockQuote(code);
            return [code, quote] as [string, StockQuote];
          } catch {
            return null;
          }
        });

        const results = await Promise.all(quotePromises);
        const quoteMap = new Map<string, StockQuote>();
        results.forEach((result) => {
          if (result) {
            quoteMap.set(result[0], result[1]);
          }
        });
        setQuotes(quoteMap);
      } catch (err) {
        console.error('Failed to fetch quotes:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchQuotes();
    const interval = setInterval(fetchQuotes, 30000);
    return () => clearInterval(interval);
  }, [codes]);

  if (codes.length === 0) {
    return (
      <div className="stock-list-empty">
        <p>暂无关注的股票</p>
        <p className="hint">使用上方搜索添加股票</p>
      </div>
    );
  }

  return (
    <div className="stock-list">
      {loading && quotes.size === 0 && <div className="loading">加载中...</div>}
      <div className="stock-grid">
        {codes.map((code) => {
          const quote = quotes.get(code);
          return (
            <div
              key={code}
              className="stock-card"
              onClick={() => onStockSelect(code)}
            >
              <div className="stock-card-header">
                <span className="stock-code">{code}</span>
                <span className="stock-name">{quote?.name || code}</span>
              </div>
              {quote ? (
                <div className="stock-card-body">
                  <div className="stock-price">{quote.price.toFixed(2)}</div>
                  <div className={`stock-change ${quote.change >= 0 ? 'positive' : 'negative'}`}>
                    {quote.change >= 0 ? '+' : ''}
                    {quote.change.toFixed(2)} ({quote.change_percent.toFixed(2)}%)
                  </div>
                  <div className="stock-volume">
                    成交量: {(quote.volume / 10000).toFixed(2)}万
                  </div>
                </div>
              ) : (
                <div className="stock-card-loading">加载中...</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
