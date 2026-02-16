import { useState, useEffect } from 'react';
import type { KLineData, TechnicalIndicator } from '../types/stock';
import { stockApi } from '../services/stockApi';

interface TechnicalIndicatorsProps {
  code: string;
}

// 计算简单移动平均线
function calculateSMA(data: KLineData[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null);
    } else {
      let sum = 0;
      for (let j = 0; j < period; j++) {
        sum += data[i - j].close;
      }
      result.push(sum / period);
    }
  }
  return result;
}

// 计算指数移动平均线
function calculateEMA(values: number[], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  const multiplier = 2 / (period + 1);

  let ema: number | null = null;
  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) {
      result.push(null);
    } else if (i === period - 1) {
      // SMA作为初始EMA
      let sum = 0;
      for (let j = 0; j < period; j++) {
        sum += values[j];
      }
      ema = sum / period;
      result.push(ema);
    } else {
      const currentEma = ema as number;
      ema = (values[i] - currentEma) * multiplier + currentEma;
      result.push(ema);
    }
  }
  return result;
}

// 计算RSI
function calculateRSI(data: KLineData[], period: number = 14): (number | null)[] {
  const result: (number | null)[] = [];
  const changes: number[] = [];

  for (let i = 0; i < data.length; i++) {
    if (i === 0) {
      changes.push(0);
      result.push(null);
    } else {
      changes.push(data[i].close - data[i - 1].close);
      if (i < period) {
        result.push(null);
      } else {
        let gains = 0;
        let losses = 0;
        for (let j = 1; j <= period; j++) {
          if (changes[i - j + 1] > 0) {
            gains += changes[i - j + 1];
          } else {
            losses -= changes[i - j + 1];
          }
        }
        const avgGain = gains / period;
        const avgLoss = losses / period;
        if (avgLoss === 0) {
          result.push(100);
        } else {
          const rs = avgGain / avgLoss;
          result.push(100 - 100 / (1 + rs));
        }
      }
    }
  }
  return result;
}

// 计算KDJ
function calculateKDJ(data: KLineData[], period: number = 9): Array<{ k: number; d: number; j: number }> {
  const result: Array<{ k: number; d: number; j: number }> = [];
  const rsvValues: number[] = [];

  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      rsvValues.push(50);
      result.push({ k: 50, d: 50, j: 50 });
    } else {
      let high = data[i].high;
      let low = data[i].low;
      for (let j = 1; j < period; j++) {
        high = Math.max(high, data[i - j].high);
        low = Math.min(low, data[i - j].low);
      }
      const rsv = high === low ? 50 : ((data[i].close - low) / (high - low)) * 100;
      rsvValues.push(rsv);

      const k = (2 * (result[i - 1]?.k || 50) + rsv) / 3;
      const d = (2 * (result[i - 1]?.d || 50) + k) / 3;
      const jVal = 3 * k - 2 * d;
      result.push({ k, d, j: jVal });
    }
  }
  return result;
}

export function TechnicalIndicators({ code }: TechnicalIndicatorsProps) {
  const [indicators, setIndicators] = useState<TechnicalIndicator[]>([]);
  const [loading, setLoading] = useState(true);
  const [klineData, setKlineData] = useState<KLineData[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const endDate = new Date().toISOString().slice(0, 10).replace(/-/g, '');
        const startDate = new Date(Date.now() - 60 * 24 * 60 * 60 * 1000)
          .toISOString()
          .slice(0, 10)
          .replace(/-/g, '');
        const data = await stockApi.getKLine(code, startDate, endDate, 'daily', 'qfq');
        setKlineData(data.reverse());
      } catch (err) {
        console.error('Failed to fetch data for indicators:', err);
      } finally {
        setLoading(false);
      }
    };

    if (code) {
      fetchData();
    }
  }, [code]);

  useEffect(() => {
    if (klineData.length === 0) return;

    const latest = klineData[klineData.length - 1];
    const prev = klineData.length > 1 ? klineData[klineData.length - 2] : null;

    const sma5 = calculateSMA(klineData, 5);
    const sma10 = calculateSMA(klineData, 10);
    const sma20 = calculateSMA(klineData, 20);
    const rsi = calculateRSI(klineData);
    const kdj = calculateKDJ(klineData);

    const latestSMA5 = sma5[sma5.length - 1];
    const latestSMA10 = sma10[sma10.length - 1];
    const latestSMA20 = sma20[sma20.length - 1];
    const latestRSI = rsi[rsi.length - 1];
    const latestKDJ = kdj[kdj.length - 1];

    const newIndicators: TechnicalIndicator[] = [
      {
        name: 'MA5',
        value: latestSMA5 || 0,
        signal: latestSMA5 && latestSMA10 ? (latestSMA5 > latestSMA10 ? 'buy' : 'sell') : 'neutral',
        description: '5日均线',
      },
      {
        name: 'MA10',
        value: latestSMA10 || 0,
        signal: latestSMA10 && latestSMA20 ? (latestSMA10 > latestSMA20 ? 'buy' : 'sell') : 'neutral',
        description: '10日均线',
      },
      {
        name: 'MA20',
        value: latestSMA20 || 0,
        description: '20日均线',
      },
      {
        name: 'RSI',
        value: latestRSI || 50,
        signal: latestRSI
          ? latestRSI > 70
            ? 'sell'
            : latestRSI < 30
              ? 'buy'
              : 'neutral'
          : 'neutral',
        description: '相对强弱指数',
      },
      {
        name: 'KDJ.K',
        value: latestKDJ?.k || 50,
        signal:
          latestKDJ && prev
            ? latestKDJ.k > (kdj[kdj.length - 2]?.k || 50)
              ? 'buy'
              : 'sell'
            : 'neutral',
        description: 'K值',
      },
      {
        name: 'KDJ.D',
        value: latestKDJ?.d || 50,
        description: 'D值',
      },
      {
        name: 'KDJ.J',
        value: latestKDJ?.j || 50,
        signal:
          latestKDJ && prev
            ? latestKDJ.j > (kdj[kdj.length - 2]?.j || 50)
              ? 'buy'
              : 'sell'
            : 'neutral',
        description: 'J值',
      },
    ];

    setIndicators(newIndicators);
  }, [klineData]);

  if (loading) {
    return <div className="indicators-loading">加载技术指标中...</div>;
  }

  return (
    <div className="technical-indicators">
      <h3>技术指标</h3>
      <div className="indicators-grid">
        {indicators.map((indicator) => (
          <div key={indicator.name} className={`indicator-card ${indicator.signal || ''}`}>
            <div className="indicator-name">{indicator.name}</div>
            <div className="indicator-value">
              {typeof indicator.value === 'number' ? indicator.value.toFixed(2) : '-'}
            </div>
            {indicator.description && (
              <div className="indicator-desc">{indicator.description}</div>
            )}
            {indicator.signal && (
              <div className={`indicator-signal ${indicator.signal}`}>
                {indicator.signal === 'buy' ? '买入' : indicator.signal === 'sell' ? '卖出' : '观望'}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
