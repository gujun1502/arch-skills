import React, { useState, useMemo } from "react";
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer,
} from "recharts";

/* ------------------------------------------------------------------ *
 * 报价博弈引擎 / Bid Pricing Game Engine
 * 蒙特卡洛 + 公共随机数。对每个候选报价，在同一批对手实现上评估
 * 中标概率、中标利润、预期利润，扫出利润最大化报价点。
 * 三种评分规则：最低价 / 均值基准 / 均值×随机K。
 * 非对称惩罚 (α 上浮扣分, δ 下浮扣分) 作为横切参数。
 * ------------------------------------------------------------------ */

// 确定性 PRNG —— 同参数同曲线，便于复现与对比
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function gaussian(rng) {
  let u = 0, v = 0;
  while (u === 0) u = rng();
  while (v === 0) v = rng();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

const M = 2200;        // 模拟次数
const G = 73;          // 报价网格点
const LO = 0.72, HI = 1.0;
const T0 = 90;         // 对手基准技术分

function computeCurve(p) {
  const { rule, C, costRate, n, center, sigma, wPrice, techAdv, aUp, dDn, kLo, kHi, trim } = p;
  const cost = costRate * C;
  const floor = 0.6 * C;
  const rng = mulberry32(20260614);

  // 公共随机数：对手报价矩阵 + K 向量，一次抽样，所有候选报价共用
  const others = new Array(M);
  for (let m = 0; m < M; m++) {
    const row = new Array(n - 1);
    for (let j = 0; j < n - 1; j++) {
      let x = center * C + gaussian(rng) * sigma * C;
      x = Math.min(C, Math.max(floor, x));
      row[j] = x;
    }
    others[m] = row;
  }
  const Ks = new Array(M);
  for (let m = 0; m < M; m++) Ks[m] = kLo + rng() * (kHi - kLo);

  // 对手报价分布直方图（与报价无关，画在仪表屏底部作为“战场”）
  const counts = new Array(G).fill(0);
  for (let m = 0; m < M; m++) {
    for (let j = 0; j < n - 1; j++) {
      const f = others[m][j] / C;
      let gi = Math.round(((f - LO) / (HI - LO)) * (G - 1));
      if (gi >= 0 && gi < G) counts[gi]++;
    }
  }
  const cMax = Math.max(1, ...counts);

  const data = [];
  let best = null;
  for (let g = 0; g < G; g++) {
    const f = LO + (HI - LO) * (g / (G - 1));
    const b = f * C;
    let wins = 0;

    for (let m = 0; m < M; m++) {
      const row = others[m];

      if (rule === "low") {
        let mn = b;
        for (let j = 0; j < n - 1; j++) if (row[j] < mn) mn = row[j];
        if (b <= mn + 1e-9 && b >= floor) wins++;
        continue;
      }

      // 均值 / 去掉最高最低
      let sum = b, mx = b, mnv = b;
      for (let j = 0; j < n - 1; j++) {
        const o = row[j]; sum += o;
        if (o > mx) mx = o;
        if (o < mnv) mnv = o;
      }
      let mean;
      if (trim && n >= 4) mean = (sum - mx - mnv) / (n - 2);
      else mean = sum / n;
      const base = rule === "avgK" ? Ks[m] * mean : mean;

      const devMe = ((b - base) / base) * 100;
      let psMe = 100 - (devMe > 0 ? aUp * devMe : dDn * -devMe);
      if (psMe < 0) psMe = 0;
      const myTotal = wPrice * psMe + (1 - wPrice) * (T0 + techAdv);

      let iWin = true;
      for (let j = 0; j < n - 1; j++) {
        const o = row[j];
        const dev = ((o - base) / base) * 100;
        let ps = 100 - (dev > 0 ? aUp * dev : dDn * -dev);
        if (ps < 0) ps = 0;
        const tot = wPrice * ps + (1 - wPrice) * T0;
        if (tot >= myTotal) { iWin = false; break; }
      }
      if (iWin) wins++;
    }

    const pwin = wins / M;
    const margin = b - cost;
    const eprofit = pwin * margin;
    const datum = {
      bidPct: +(f * 100).toFixed(2),
      pwin: +(pwin * 100).toFixed(2),
      margin: +margin.toFixed(0),
      marginPct: +(((b - cost) / cost) * 100).toFixed(1),
      eprofit: +eprofit.toFixed(0),
      comp: +((counts[g] / cMax) * 24).toFixed(2),
    };
    data.push(datum);
    if (eprofit > 0 && (best === null || eprofit > best.eprofit)) best = datum;
  }
  if (!best) best = data[data.length - 1];
  return { data, best, cost, centerPct: center * 100 };
}

/* ------------------------------ UI ------------------------------ */

const COL = {
  canvas: "#EDEEF1", panel: "#FFFFFF", ink: "#14171D", sub: "#6B7280",
  line: "#E3E5EA", screen: "#14171D", teal: "#2DD4BF", amber: "#F4B740",
  coral: "#FF6584",
};
const MONO = "ui-monospace, 'SFMono-Regular', Menlo, 'JetBrains Mono', monospace";
const SANS = "-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', sans-serif";

const fmtY = (v) => "¥" + v.toLocaleString("zh-CN") + "万";

function Slider({ label, sub, value, min, max, step, onChange, display }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
        <span style={{ fontSize: 12.5, color: COL.ink, fontWeight: 500 }}>
          {label}
          {sub && <span style={{ color: COL.sub, fontWeight: 400, marginLeft: 6, fontSize: 11 }}>{sub}</span>}
        </span>
        <span style={{ fontFamily: MONO, fontSize: 12.5, color: COL.ink, fontWeight: 600 }}>{display}</span>
      </div>
      <input className="bg-slider" type="range" min={min} max={max} step={step}
        value={value} onChange={(e) => onChange(parseFloat(e.target.value))} style={{ width: "100%" }} />
    </div>
  );
}

function Seg({ value, onChange, options }) {
  return (
    <div style={{ display: "flex", background: "#F1F2F5", borderRadius: 8, padding: 3, gap: 3 }}>
      {options.map((o) => {
        const on = o.k === value;
        return (
          <button key={o.k} onClick={() => onChange(o.k)}
            style={{
              flex: 1, border: "none", cursor: "pointer", borderRadius: 6,
              padding: "7px 4px", fontSize: 12, fontFamily: SANS, fontWeight: on ? 600 : 500,
              background: on ? COL.ink : "transparent", color: on ? "#fff" : COL.sub,
              transition: "all .15s",
            }}>
            {o.t}
          </button>
        );
      })}
    </div>
  );
}

function Card({ tag, value, note, accent }) {
  return (
    <div style={{ background: COL.panel, border: `1px solid ${COL.line}`, borderRadius: 12, padding: "13px 14px" }}>
      <div style={{ fontFamily: MONO, fontSize: 9.5, letterSpacing: 1, color: COL.sub, textTransform: "uppercase", marginBottom: 7 }}>{tag}</div>
      <div style={{ fontFamily: MONO, fontSize: 22, fontWeight: 700, color: accent || COL.ink, lineHeight: 1 }}>{value}</div>
      {note && <div style={{ fontSize: 11, color: COL.sub, marginTop: 5, fontFamily: MONO }}>{note}</div>}
    </div>
  );
}

function ChartTip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{ background: "#0E1015", border: "1px solid rgba(255,255,255,.12)", borderRadius: 8, padding: "9px 11px", fontFamily: MONO, fontSize: 11.5 }}>
      <div style={{ color: "#fff", fontWeight: 700, marginBottom: 5 }}>{d.bidPct}% C</div>
      <div style={{ color: COL.teal }}>中标概率 {d.pwin}%</div>
      <div style={{ color: COL.amber }}>中标利润 ¥{d.margin}万 · {d.marginPct}%</div>
      <div style={{ color: "#cfd3da" }}>预期利润 ¥{d.eprofit}万</div>
    </div>
  );
}

export default function App() {
  const [rule, setRule] = useState("avg");
  const [C, setC] = useState(1000);
  const [costRate, setCostRate] = useState(0.8);
  const [n, setN] = useState(8);
  const [dcenter, setDcenter] = useState(0.08); // 对手中心下浮率
  const [sigma, setSigma] = useState(0.03);
  const [wPrice, setWPrice] = useState(0.4);
  const [techAdv, setTechAdv] = useState(2);
  const [aUp, setAUp] = useState(2.0);
  const [dDn, setDDn] = useState(1.0);
  const [kLo, setKLo] = useState(0.95);
  const [kHi, setKHi] = useState(1.0);
  const [trim, setTrim] = useState(true);

  const params = { rule, C, costRate, n, center: 1 - dcenter, sigma, wPrice, techAdv, aUp, dDn, kLo, kHi, trim };
  const { data, best, cost, centerPct } = useMemo(() => computeCurve(params), [JSON.stringify(params)]);

  // 策略提示
  const hint = useMemo(() => {
    if (rule === "low") {
      return "最低价规则：向成本线探底的纯价格博弈，技术分不参与。最优点落在中标概率上升放缓与利润率下降的拐点；低于成本下限即废标。";
    }
    const q = (dDn / (aUp + dDn)).toFixed(2);
    const sens = (100 / n).toFixed(1);
    let s = `基准价对你自身报价的敏感度 ≈ 1/n = ${sens}%——你抬高报价会同时把基准价拉高（不动点效应）${trim ? "；去掉最高最低后，若你不在被剔除之列，敏感度进一步下降" : ""}。`;
    if (aUp > dDn) s += ` 惩罚非对称 (α>δ)：超基准价扣分更狠，最优报价被压向基准价下方，理论目标分位 δ/(α+δ)=${q}。`;
    else if (dDn > aUp) s += ` 惩罚非对称 (δ>α)：低于基准价扣分更狠，最优报价上移，理论目标分位 δ/(α+δ)=${q}。`;
    else s += " 惩罚对称：最优报价目标对手报价中位附近。";
    if (rule === "avgK") s += ` 随机系数 K∈[${kLo},${kHi}] 制造外生不确定性，无法精确命中基准价，最优报价整体下移以对冲。`;
    return s;
  }, [rule, aUp, dDn, n, trim, kLo, kHi]);

  const optAmt = ((best.bidPct / 100) * C).toFixed(0);

  return (
    <div style={{ background: COL.canvas, minHeight: "100%", fontFamily: SANS, color: COL.ink, padding: 18 }}>
      <style>{`
        .bg-slider{-webkit-appearance:none;appearance:none;height:3px;border-radius:2px;background:#D6D9E0;outline:none;}
        .bg-slider::-webkit-slider-thumb{-webkit-appearance:none;width:15px;height:15px;border-radius:50%;background:${COL.ink};cursor:pointer;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.28);}
        .bg-slider::-moz-range-thumb{width:13px;height:13px;border-radius:50%;background:${COL.ink};cursor:pointer;border:2px solid #fff;}
        .bg-main{display:grid;grid-template-columns:352px 1fr;gap:16px;max-width:1180px;margin:0 auto;}
        @media(max-width:880px){.bg-main{grid-template-columns:1fr;}}
        .bg-cards{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:14px;}
        @media(max-width:520px){.bg-cards{grid-template-columns:repeat(2,1fr);}}
      `}</style>

      {/* 标题栏 */}
      <div style={{ maxWidth: 1180, margin: "0 auto 16px", display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 8 }}>
        <div>
          <div style={{ fontSize: 21, fontWeight: 700, letterSpacing: -0.2 }}>报价博弈引擎</div>
          <div style={{ fontFamily: MONO, fontSize: 10.5, letterSpacing: 1.5, color: COL.sub, marginTop: 3 }}>BID PRICING GAME ENGINE</div>
        </div>
        <div style={{ fontFamily: MONO, fontSize: 10.5, color: COL.sub, textAlign: "right" }}>
          MONTE CARLO · {M.toLocaleString()} TRIALS · COMMON RANDOM NUMBERS<br />
          <span style={{ color: COL.ink }}>n−1 = {n - 1} 家对手 · 中心 {(100 - dcenter * 100).toFixed(0)}%C · σ {(sigma * 100).toFixed(0)}%C</span>
        </div>
      </div>

      <div className="bg-main">
        {/* 控制台 */}
        <div style={{ background: COL.panel, border: `1px solid ${COL.line}`, borderRadius: 14, padding: 18 }}>
          <Seg value={rule} onChange={setRule} options={[
            { k: "low", t: "最低价" }, { k: "avg", t: "均值基准" }, { k: "avgK", t: "均值×K" },
          ]} />

          <Group title="项目" />
          <Slider label="招标控制价" value={C} min={100} max={5000} step={50} onChange={setC} display={`¥${C}万`} />
          <Slider label="你的成本" sub="占控制价" value={costRate} min={0.5} max={0.95} step={0.01} onChange={setCostRate}
            display={`¥${(costRate * C).toFixed(0)}万 · ${(costRate * 100).toFixed(0)}%`} />

          <Group title="对手画像" />
          <Slider label="参与方家数 n" value={n} min={2} max={12} step={1} onChange={setN} display={`${n} 家`} />
          <Slider label="对手中心下浮率" value={dcenter} min={0} max={0.25} step={0.005} onChange={setDcenter} display={`${(dcenter * 100).toFixed(1)}%`} />
          <Slider label="离散度 σ" value={sigma} min={0.01} max={0.08} step={0.005} onChange={setSigma} display={`${(sigma * 100).toFixed(1)}%C`} />

          <Group title="评分规则" />
          {rule !== "low" && (
            <>
              <Slider label="价格分权重" value={wPrice} min={0.1} max={0.8} step={0.05} onChange={setWPrice} display={`${(wPrice * 100).toFixed(0)}%`} />
              <Slider label="上浮扣分率 α" sub="每超 1%" value={aUp} min={0.5} max={5} step={0.1} onChange={setAUp} display={`${aUp.toFixed(1)} 分`} />
              <Slider label="下浮扣分率 δ" sub="每低 1%" value={dDn} min={0.5} max={5} step={0.1} onChange={setDDn} display={`${dDn.toFixed(1)} 分`} />
            </>
          )}
          {rule === "avgK" && (
            <>
              <Slider label="K 下界" value={kLo} min={0.9} max={1.0} step={0.005} onChange={setKLo} display={kLo.toFixed(3)} />
              <Slider label="K 上界" value={kHi} min={0.95} max={1.05} step={0.005} onChange={setKHi} display={kHi.toFixed(3)} />
            </>
          )}
          {rule !== "low" && (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
              <span style={{ fontSize: 12.5, color: COL.ink, fontWeight: 500 }}>去掉最高最低</span>
              <button onClick={() => setTrim(!trim)} style={{
                width: 42, height: 24, borderRadius: 12, border: "none", cursor: "pointer", position: "relative",
                background: trim ? COL.ink : "#D6D9E0", transition: "all .15s",
              }}>
                <span style={{
                  position: "absolute", top: 3, left: trim ? 21 : 3, width: 18, height: 18, borderRadius: "50%",
                  background: "#fff", transition: "all .15s", boxShadow: "0 1px 2px rgba(0,0,0,.25)",
                }} />
              </button>
            </div>
          )}

          {rule !== "low" && (
            <>
              <Group title="你的牌" />
              <Slider label="技术分相对优势 Δ" value={techAdv} min={-5} max={8} step={0.5} onChange={setTechAdv} display={`${techAdv > 0 ? "+" : ""}${techAdv} 分`} />
            </>
          )}
        </div>

        {/* 仪表屏 + 读数 */}
        <div>
          <div style={{ background: COL.screen, borderRadius: 14, padding: "16px 14px 8px", border: `1px solid ${COL.line}` }}>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "0 6px 10px", fontFamily: MONO, fontSize: 10.5 }}>
              <span style={{ color: COL.teal }}>● 中标概率 %</span>
              <span style={{ color: COL.amber }}>● 预期利润 ¥万</span>
              <span style={{ color: COL.coral }}>┃ 最优报价</span>
              <span style={{ color: "#6B7280" }}>▒ 对手分布</span>
            </div>
            <ResponsiveContainer width="100%" height={336}>
              <ComposedChart data={data} margin={{ top: 6, right: 8, bottom: 18, left: -6 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis dataKey="bidPct" type="number" domain={[LO * 100, HI * 100]}
                  ticks={[75, 80, 85, 90, 95, 100]} tickFormatter={(v) => v + "%"}
                  tick={{ fill: "#7C8290", fontFamily: MONO, fontSize: 10.5 }}
                  stroke="rgba(255,255,255,0.12)"
                  label={{ value: "你的报价（% 控制价）", position: "insideBottom", offset: -10, fill: "#7C8290", fontSize: 11, fontFamily: SANS }} />
                <YAxis yAxisId="left" domain={[0, 100]} tick={{ fill: "#7C8290", fontFamily: MONO, fontSize: 10 }} stroke="rgba(255,255,255,0.12)" width={34} />
                <YAxis yAxisId="right" orientation="right" tick={{ fill: "#7C8290", fontFamily: MONO, fontSize: 10 }} stroke="rgba(255,255,255,0.12)" width={42} />
                <Tooltip content={<ChartTip />} cursor={{ stroke: "rgba(255,255,255,0.18)" }} />

                <defs>
                  <linearGradient id="ga" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={COL.amber} stopOpacity={0.22} />
                    <stop offset="100%" stopColor={COL.amber} stopOpacity={0} />
                  </linearGradient>
                </defs>

                <Area yAxisId="left" dataKey="comp" stroke="none" fill="rgba(255,255,255,0.07)" isAnimationActive={false} />
                <ReferenceLine yAxisId="left" x={centerPct} stroke="#5A6070" strokeDasharray="3 4"
                  label={{ value: rule === "low" ? "对手中心" : "基准价≈", fill: "#7C8290", fontSize: 10, fontFamily: MONO, position: "top" }} />
                <Area yAxisId="right" dataKey="eprofit" stroke={COL.amber} strokeWidth={2.4} fill="url(#ga)" isAnimationActive={false} dot={false} />
                <Line yAxisId="left" dataKey="pwin" stroke={COL.teal} strokeWidth={2.4} dot={false} isAnimationActive={false} />
                <ReferenceLine yAxisId="right" x={best.bidPct} stroke={COL.coral} strokeWidth={1.6}
                  label={{ value: "最优 " + best.bidPct + "%", fill: COL.coral, fontSize: 10.5, fontFamily: MONO, fontWeight: 700, position: "insideTopRight" }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-cards">
            <Card tag="OPTIMAL BID 最优报价" value={`${best.bidPct}%`} note={`¥${optAmt}万`} accent={COL.coral} />
            <Card tag="WIN PROB 中标概率" value={`${best.pwin}%`} accent={COL.teal} />
            <Card tag="MARGIN 中标利润" value={`¥${best.margin}`} note={`万 · ${best.marginPct}%`} accent={COL.amber} />
            <Card tag="E[PROFIT] 预期利润" value={`¥${best.eprofit}`} note="万 = 概率 × 利润" />
          </div>

          <div style={{ background: COL.panel, border: `1px solid ${COL.line}`, borderRadius: 12, padding: "13px 15px", marginTop: 12 }}>
            <div style={{ fontFamily: MONO, fontSize: 9.5, letterSpacing: 1, color: COL.coral, textTransform: "uppercase", marginBottom: 6 }}>策略提示</div>
            <div style={{ fontSize: 12.5, lineHeight: 1.7, color: "#374151" }}>{hint}</div>
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 1180, margin: "14px auto 0", fontSize: 11, color: COL.sub, fontFamily: MONO, textAlign: "center" }}>
        对手报价分布（中心/σ）目前为人工假设 —— 接入历史中标公告数据做经验校准后，本引擎从计算器变为护城河。
      </div>
    </div>
  );
}

function Group({ title }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "18px 0 12px" }}>
      <span style={{ fontFamily: MONO, fontSize: 10, letterSpacing: 1.5, color: "#9AA0AC", textTransform: "uppercase" }}>{title}</span>
      <span style={{ flex: 1, height: 1, background: "#EBECEF" }} />
    </div>
  );
}
