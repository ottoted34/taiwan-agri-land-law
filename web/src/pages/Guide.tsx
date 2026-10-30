import { Link } from "react-router-dom";

export default function Guide() {
  return <article style={{ maxWidth: 860 }}>
    <h1>使用說明</h1>
    <section className="card" style={{ marginBottom: 14 }}>
      <h2>搜尋方式</h2>
      <table className="t"><tbody>
        <tr><th>關鍵字</th><td>直接輸入，如「資材室」。多個詞以空白分隔時全部須符合。常見設施名稱會自動帶入同義詞（如 資材室＝農業資材室）。</td></tr>
        <tr><th>發文字號</th><td>「農保規字第1150230515號」，或只輸入數字「1150230515」。</td></tr>
        <tr><th>法規條號</th><td>「農業發展條例第8條之1」「申請農業用地作農業設施容許使用審查辦法 第29-1條」。</td></tr>
        <tr><th>日期</th><td>民國「115/7/28」「115年7月28日」或西元「2026-07-28」。篩選區可輸入起迄期間。</td></tr>
      </tbody></table>
    </section>
    <section className="card" style={{ marginBottom: 14 }}>
      <h2>資料分類</h2>
      <ul>
        <li><span className="tag law">法規條文</span> 法律、命令（全國法規資料庫）及行政規則（農地及農舍法規檢索系統）。</li>
        <li><span className="tag interp">函釋</span> 主管機關之解釋函、解釋令。每件均附官方原文連結。</li>
        <li><span className="tag tech">技術參考資料</span> 試驗研究機構出版品書目。<strong>不具法律效力</strong>，僅供農業經營合理性之專業參考。</li>
      </ul>
    </section>
    <section className="card" style={{ marginBottom: 14 }}>
      <h2>函釋效力標示怎麼看</h2>
      <ul>
        <li><strong>未查得停止適用</strong>：本站收錄資料中沒有發現停止適用資訊，<strong>不等於仍然有效</strong>。</li>
        <li><strong>可能受修法影響</strong>：函釋所引用之條文（或整部法規全文）在發文後曾修正。請比對修正內容。</li>
        <li><strong>後續函釋補充變更／效力待查核</strong>：後續函釋文字提及本函，系統比對後提示查核，未經人工確認。</li>
        <li><strong>官方停止適用／廢止</strong>：限有官方明文依據並經人工確認者。</li>
      </ul>
      <p className="small">系統不會以 AI 或演算法宣稱某件函釋有效或失效。</p>
    </section>
    <section className="card" style={{ marginBottom: 14 }}>
      <h2>法規與函釋的關聯</h2>
      <ul>
        <li><strong>官方列示</strong>：農地及農舍法規檢索系統於該法規「解釋內容」所列之函釋（法規層級）。</li>
        <li><strong>系統比對</strong>：函釋內文出現「法規名稱＋條號」時自動建立，為演算法建議。</li>
        <li><strong>人工確認</strong>：經人工查核並附依據者。</li>
      </ul>
    </section>
    <section className="card">
      <h2>案件審查輔助</h2>
      <p><Link to="/assist">案件審查輔助</Link>：輸入案件客觀事實（可點選常見主題協助描述），系統依內容自動判斷相關主題，列出<strong>可能適用的法規條文</strong>，
        以及<strong>協助判斷</strong>之資料（待釐清事項、相關函釋及其效力查核資訊、注意事項、農業技術參考）。這是以檢索及規則為基礎的輔助工具，<strong>不是 AI 法律分析</strong>，也不提供准駁結論。</p>
      <p>選擇<strong>案件所在縣市</strong>後，會一併列出本站已收錄、且與案件主題相關之該縣市地方規定；尚未查核之縣市會標示「尚未查核」。輸入日期可提示該日期後法規是否曾修正。請勿輸入個人資料。</p>
    </section>
  </article>;
}
