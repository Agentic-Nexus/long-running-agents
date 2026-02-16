import { useState, useEffect } from 'react';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { KLineData } from '../types/stock';
import { stockApi } from '../services/stockApi';

interface StockChartProps {
  code: string;
  period?: 'daily' | 'weekly' | 'monthly';
  adjust?: 'qfq' | 'hfq' | '';
}

export function StockChart({ code, period = 'daily', adjust = 'qfq' }: StockChartProps) {
  const [klineData, setKlineData] = useState<KLineData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchKLine = async () => {
      setLoading(true);
      setError(null);

      try {
        // 获取最近180天的数据
        const endDate = new Date().toISOString().slice(0, 10).replace(/-/g, '');
        const startDate = new Date(Date.now() - 180 * 24 * 60 * 60 * 1000)
          .toISOString()
          .slice(0, 10)
          .replace(/-/g, '');

        const data = await stockApi.getKLine(code, startDate, endDate, period, adjust);
        setKlineData(data);
      } catch (err) {
        setError('获取K线数据失败');
        console.error('Failed to fetch K-line data:', err);
      } finally {
        setLoading(false);
      }
    };

    if (code) {
      fetchKLine();
    }
  }, [code, period, adjust]);

  if (loading) {
    return <div className="chart-loading">加载K线数据中...</div>;
  }

  if (error) {
    return <div className="chart-error">{error}</div>;
  }

  if (klineData.length === 0) {
    return <div className="chart-empty">暂无K线数据</div>;
  }

  // 格式化日期用于显示
  const chartData = klineData.map((item) => ({
    ...item,
    dateStr: `${item.date.slice(0, 4)}-${item.date.slice(4, 6)}-${item.date.slice(6, 8)}`,
    // 成交量转换为万手
    volumeW: item.volume / 10000,
  }));

  // 计算价格范围
  const prices = klineData.flatMap((d) => [d.high, d.low]);
  const minPrice = Math.min(...prices) * 0.98;
  const maxPrice = Math.max(...prices) * 1.02;

  // 自定义tooltip
  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: KLineData & { dateStr: string } }> }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="chart-tooltip">
          <p className="tooltip-date">{data.dateStr}</p>
          <p>开盘: {data.open.toFixed(2)}</p>
          <p>最高: {data.high.toFixed(2)}</p>
          <p>最低: {data.low.toFixed(2)}</p>
          <p>收盘: {data.close.toFixed(2)}</p>
          <p>成交量: {(data.volume / 10000).toFixed(2)}万</p>
          <p>成交额: {(data.amount / 100000000).toFixed(2)}亿</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="stock-chart">
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
          <XAxis
            dataKey="dateStr"
            tick={{ fontSize: 10 }}
            interval="preserveStartEnd"
          />
          <YAxis
            yAxisId="price"
            domain={[minPrice, maxPrice]}
            tick={{ fontSize: 11 }}
            orientation="right"
          />
          <YAxis
            yAxisId="volume"
            orientation="left"
            tick={{ fontSize: 11 }}
            tickFormatter={(value) => `${value}万`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Bar
            yAxisId="volume"
            dataKey="volumeW"
            name="成交量(万手)"
            fill="#82ca9d"
            opacity={0.6}
          />
          <Line
            yAxisId="price"
            type="monotone"
            dataKey="close"
            name="收盘价"
            stroke="#ff7300"
            dot={false}
            strokeWidth={2}
          />
          <Line
            yAxisId="price"
            type="monotone"
            dataKey="open"
            name="开盘价"
            stroke="#8884d8"
            dot={false}
            strokeWidth={1}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
