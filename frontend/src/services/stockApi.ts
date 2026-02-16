import axios from 'axios';
import type { StockSearchResult, StockQuote, KLineData, StockInfo } from '../types/stock';

const API_BASE_URL = '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export const stockApi = {
  // 股票搜索
  searchStocks: async (query: string, limit: number = 20): Promise<StockSearchResult[]> => {
    const response = await apiClient.get('/stocks/search', {
      params: { q: query, limit },
    });
    return response.data;
  },

  // 获取股票实时行情
  getStockQuote: async (code: string): Promise<StockQuote> => {
    const response = await apiClient.get(`/stocks/quote/${code}`);
    return response.data;
  },

  // 获取K线数据
  getKLine: async (
    code: string,
    startDate?: string,
    endDate?: string,
    period: string = 'daily',
    adjust: string = 'qfq'
  ): Promise<KLineData[]> => {
    const response = await apiClient.get(`/stocks/kline/${code}`, {
      params: { start_date: startDate, end_date: endDate, period, adjust },
    });
    return response.data;
  },

  // 获取股票详细信息
  getStockInfo: async (code: string): Promise<StockInfo> => {
    const response = await apiClient.get(`/stocks/${code}`);
    return response.data;
  },
};
