import { useState, useCallback } from 'react';
import type { StockSearchResult } from '../types/stock';
import { stockApi } from '../services/stockApi';

interface StockSearchProps {
  onStockSelect: (code: string) => void;
}

export function StockSearch({ onStockSelect }: StockSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const data = await stockApi.searchStocks(query.trim());
      setResults(data);
    } catch (err) {
      setError('搜索失败，请稍后重试');
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="stock-search">
      <div className="search-input-group">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入股票代码或名称搜索..."
          className="search-input"
        />
        <button onClick={handleSearch} disabled={loading} className="search-button">
          {loading ? '搜索中...' : '搜索'}
        </button>
      </div>

      {error && <div className="search-error">{error}</div>}

      {results.length > 0 && (
        <ul className="search-results">
          {results.map((stock) => (
            <li
              key={stock.code}
              className="search-result-item"
              onClick={() => {
                onStockSelect(stock.code);
                setResults([]);
                setQuery('');
              }}
            >
              <span className="stock-code">{stock.code}</span>
              <span className="stock-name">{stock.name}</span>
              <span className="stock-market">{stock.market}</span>
              {stock.price !== undefined && (
                <span className="stock-price">
                  {stock.price.toFixed(2)}
                  {stock.change !== undefined && (
                    <span className={stock.change >= 0 ? 'positive' : 'negative'}>
                      {stock.change >= 0 ? '+' : ''}
                      {stock.change.toFixed(2)}
                    </span>
                  )}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
