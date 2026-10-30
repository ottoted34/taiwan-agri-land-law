import { DISCLAIMER } from "../components/ui";

export default function About() {
  return <article style={{ maxWidth: 860 }}>
    <h1>非官方聲明及資料授權</h1>
    <div className="callout danger" style={{ marginBottom: 16 }}><strong>非官方網站聲明</strong><p style={{ margin: "6px 0 0" }}>{DISCLAIMER}</p></div>
    <section className="card" style={{ marginBottom: 14 }}>
      <h2>資料來源與授權處理</h2>
      <ul>
        <li><strong>法規條文</strong>：取自法務部全國法規資料庫開放資料 API。依著作權法第 9 條第 1 項第 1 款，法律、命令不得為著作權之標的；資料集依政府資料開放授權條款利用。</li>
        <li><strong>函釋</strong>：取自農業部農村發展及水土保持署「農地及農舍法規檢索系統」公開之通案函釋。公文依著作權法第 9 條不得為著作權標的。本站轉錄官方公開文字並附原文連結；官方系統已遮蔽之當事人資訊（如「○○」）照原樣呈現，本站不另行補充個人資料。</li>
        <li><strong>農業技術資料</strong>：僅收錄農業資料開放平臺之出版品<strong>書目資料</strong>（政府資料開放授權條款）及官方連結。出版品全文之著作權屬原發布機關，本站<strong>不鏡像</strong>PDF或全文。</li>
        <li><strong>robots.txt 不允許自動擷取之網站</strong>（如農糧署全球資訊網）本站不自動擷取，相關資料以其他官方開放管道取得或標示需人工補充。</li>
      </ul>
    </section>
    <section className="card" style={{ marginBottom: 14 }}>
      <h2>個人資料</h2>
      <p>本站不收集使用者個人資料，不使用追蹤或分析服務，搜尋於您的瀏覽器內執行。本站不收錄非公開申請案件、地籍個案資訊、內部公文或內部審查資料。</p>
    </section>
    <section className="card">
      <h2>程式碼授權</h2>
      <p>程式碼以 MIT 授權釋出。網站名稱、版面不使用任何政府機關標誌，以免誤認為官方網站。發現資料錯誤請至 <a href="https://github.com/ottoted34/taiwan-agri-land-law/issues" target="_blank" rel="noopener noreferrer">GitHub Issues</a> 回報，並附官方依據。</p>
    </section>
  </article>;
}
