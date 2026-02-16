// 股票相关类型定义

export interface StockSearchResult {
  code: string;
  name: string;
  market: string;
  price?: number;
  change?: number;
}

export interface StockQuote {
  code: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  amount: number;
  timestamp: string;
}

export interface KLineData {
  code: string;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  amount: number;
}

export interface StockInfo {
  code: string;
  name: string;
  market: string;
  industry?: string;
  listing_date?: string;
  total_shares?: string;
  circulating_shares?: string;
}

export interface TechnicalIndicator {
  name: string;
  value: number;
  signal?: 'buy' | 'sell' | 'neutral';
  description?: string;
}
