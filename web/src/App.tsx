import { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { DISCLAIMER } from "./components/ui";
import Home from "./pages/Home";
import SearchPage from "./pages/Search";
import LawList from "./pages/LawList";
import LawPage from "./pages/LawPage";
import Compare from "./pages/Compare";
import InterpPage from "./pages/InterpPage";
import TechPage from "./pages/TechPage";
import Sources from "./pages/Sources";
import Guide from "./pages/Guide";
import About from "./pages/About";
import Assist from "./pages/Assist";

const NAV: [string, string][] = [
  ["/search", "全站搜尋"], ["/laws", "法規"], ["/search?type=interp", "函釋"], ["/search?type=tech", "農業技術"],
  ["/assist", "案件審查輔助"], ["/sources", "資料來源"], ["/guide", "使用說明"],
];

export default function App() {
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  useEffect(() => { setOpen(false); if (!loc.hash) window.scrollTo(0, 0); }, [loc.pathname, loc.search, loc.hash]);
  return <>
    <a className="skip" href="#content">跳到主要內容</a>
    <div className="notice-bar">非官方網站｜資料僅供檢索參考，法律適用以主管機關正式資料及個案審認為準。<Link to="/about">聲明</Link></div>
    <header className="site">
      <div className="site-inner">
        <Link to="/" className="brand"><span className="logo" aria-hidden>農</span><span>農地法規函釋知識庫<small>Taiwan Agricultural Land Law &amp; Knowledge Hub</small></span></Link>
        <button className="menu-btn" aria-expanded={open} aria-controls="mainnav" onClick={() => setOpen(!open)}>選單</button>
        <nav id="mainnav" className={`main ${open ? "open" : ""}`} aria-label="主選單">
          {NAV.map(([to, label]) => {
            const [path, qs] = to.split("?");
            const active = loc.pathname === path && (qs ? loc.search.includes(qs) : !loc.search.includes("type=") || path !== "/search");
            return <NavLink key={to} to={to} className={() => (active ? "active" : "")}>{label}</NavLink>;
          })}
        </nav>
      </div>
    </header>
    <main id="content">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/laws" element={<LawList />} />
        <Route path="/law/:id" element={<LawPage />} />
        <Route path="/law/:id/compare" element={<Compare />} />
        <Route path="/interp/:id" element={<InterpPage />} />
        <Route path="/tech/:id" element={<TechPage />} />
        <Route path="/sources" element={<Sources />} />
        <Route path="/guide" element={<Guide />} />
        <Route path="/about" element={<About />} />
        <Route path="/assist" element={<Assist />} />
        <Route path="*" element={<div className="card"><h1>找不到頁面</h1><p><Link to="/">回首頁</Link></p></div>} />
      </Routes>
    </main>
    <footer className="site"><div className="inner">
      <p style={{ marginTop: 0 }}><strong>非官方網站聲明：</strong>{DISCLAIMER}</p>
      <p className="row" style={{ gap: 16 }}><Link to="/about">聲明及資料授權</Link><Link to="/sources">資料來源與涵蓋範圍</Link>
        <a href="https://github.com/ottoted34/taiwan-agri-land-law" target="_blank" rel="noopener noreferrer">GitHub 原始碼</a></p>
    </div></footer>
  </>;
}
