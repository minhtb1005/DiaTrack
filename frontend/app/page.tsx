import Link from "next/link";
import { ArrowUpRight, ArrowRight, Heart, Check, NotebookPen, CalendarDays, ShieldCheck, BookOpen, Plus, Sun } from "lucide-react";

export default function HomePage() {
  return <div className="pitch">
    <section className="pitch-hero" aria-labelledby="pitch-title">
      <div className="pitch-intro">
        <p className="eyebrow"><span /> MỖI NGÀY MỘT CHÚT AN TÂM</p>
        <h1 id="pitch-title">Chăm sóc đường huyết.<br/><em>Nhẹ nhàng hơn,</em><br/>mỗi ngày.</h1>
        <p className="pitch-lead">Một nơi để ghi lại chỉ số, nhớ lịch thuốc đã duyệt và chuẩn bị thông tin cho bác sĩ. DiaTrack cùng bạn giữ nhịp chăm sóc sức khỏe giữa những lần tái khám.</p>
        <div className="pitch-actions"><Link className="primary-action" href="/register">Bắt đầu cùng DiaTrack <ArrowUpRight aria-hidden size={22}/></Link><a className="text-action" href="#cach-su-dung">Tìm hiểu cách sử dụng <ArrowRight aria-hidden size={20}/></a></div>
        <div className="pitch-reassurance"><ShieldCheck aria-hidden size={22}/><span>Bạn chủ động theo dõi. Bác sĩ quyết định điều trị.</span></div>
      </div>
      <div className="pitch-visual" aria-label="Minh họa hành trình sử dụng DiaTrack">
        <div className="visual-orbit orbit-one"/><div className="visual-orbit orbit-two"/>
        <div className="daily-card">
          <div className="daily-top"><div className="daily-symbol"><Sun aria-hidden size={28}/></div><span>MỘT NGÀY CỦA BẠN<br/><strong>Chăm sóc từ những điều nhỏ</strong></span><span className="demo-label">Minh họa</span></div>
          <div className="daily-reading"><span>Sổ theo dõi đường huyết</span><div className="reading-placeholder">Hôm nay,<br/><strong>bạn thấy thế nào?</strong></div><p>Ghi chỉ số và vài lời về bữa ăn, giấc ngủ hay cảm nhận của bạn.</p></div>
          <Link href="/tracker" className="daily-add"><Plus aria-hidden size={22}/> Ghi chỉ số hôm nay <ArrowRight aria-hidden size={20}/></Link>
          <div className="daily-line"><span className="step-dot"><Check aria-hidden size={17}/></span><div><strong>Theo dõi từng ngày</strong><span>Thông tin được giữ lại để xem cùng bác sĩ</span></div></div>
          <div className="daily-line"><span className="step-dot warm"><CalendarDays aria-hidden size={18}/></span><div><strong>Sẵn sàng cho lần tái khám</strong><span>Mang theo bản tóm tắt dễ theo dõi</span></div></div>
        </div>
        <div className="care-note"><Heart aria-hidden size={24}/><span>Đều đặn từng chút.<br/><strong>Hiểu mình thêm mỗi ngày.</strong></span></div>
      </div>
    </section>
    <div className="pitch-principles"><span><Check aria-hidden/> Chữ rõ, thao tác đơn giản</span><span><Check aria-hidden/> Thông tin có thể xem lại</span><span><Check aria-hidden/> Bác sĩ luôn giữ vai trò quyết định</span></div>
    <section id="cach-su-dung" className="pitch-section">
      <div className="section-heading"><div><p className="eyebrow">BẮT ĐẦU TỪ VIỆC NHỎ</p><h2>Ba bước. Một nhịp chăm sóc.</h2></div><p>Không cần nhớ tất cả trong đầu.<br/>Mỗi việc đều có một nơi rõ ràng.</p></div>
      <div className="journey-grid">
        <article><span className="journey-number">01</span><NotebookPen aria-hidden className="journey-icon"/><h3>Ghi lại hôm nay</h3><p>Nhập chỉ số đường huyết, thời điểm đo và điều bạn muốn lưu ý. Xem lại lịch sử bất cứ khi nào cần.</p><Link href="/tracker">Mở sổ theo dõi <ArrowUpRight aria-hidden size={20}/></Link></article>
        <article><span className="journey-number">02</span><Heart aria-hidden className="journey-icon"/><h3>Giữ nhịp mỗi ngày</h3><p>Xem lịch thuốc bác sĩ đã duyệt, ghi nhận việc dùng thuốc và tìm hiểu kiến thức chăm sóc bản thân.</p><Link href="/medications">Xem lịch thuốc <ArrowUpRight aria-hidden size={20}/></Link></article>
        <article><span className="journey-number">03</span><CalendarDays aria-hidden className="journey-icon"/><h3>Tái khám có chuẩn bị</h3><p>Tổng hợp những điều đã ghi lại thành hồ sơ để bạn và bác sĩ có thêm thông tin khi trao đổi.</p><Link href="/previsit">Chuẩn bị tái khám <ArrowUpRight aria-hidden size={20}/></Link></article>
      </div>
    </section>
    <section className="doctor-story">
      <div className="story-mark"><span>DÀNH CHO BÁC SĨ</span><div className="paper-preview"><div/><div/><div/><p>Nhìn lại hành trình.<br/><strong>Dành thời gian cho người bệnh.</strong></p><ShieldCheck aria-hidden size={46}/></div></div>
      <div><p className="eyebrow">THÔNG TIN LIỀN MẠCH HƠN</p><h2>Mỗi lần khám,<br/>bớt một khoảng trống.</h2><p>Nhật ký tại nhà giúp cuộc trao đổi bắt đầu từ những gì đã xảy ra. Bác sĩ có thể xem xu hướng, đối chiếu bản ghi và rà soát bản tóm tắt trước tái khám.</p><ul><li><Check aria-hidden/> Xem lại chỉ số theo thời gian</li><li><Check aria-hidden/> Đối chiếu nhận định với bản ghi gốc</li><li><Check aria-hidden/> Giữ quyền quyết định kế hoạch điều trị</li></ul><Link className="text-action" href="/expert/patients">Mở không gian bác sĩ <ArrowUpRight aria-hidden size={22}/></Link></div>
    </section>
    <section className="pitch-section faq-section"><div><p className="eyebrow">BẠN CÓ THỂ MUỐN BIẾT</p><h2>Bắt đầu dễ dàng.<br/>Sử dụng an tâm.</h2><Link href="/hoc" className="text-action"><BookOpen aria-hidden size={21}/> Khám phá bài học</Link></div><div className="faq-list">
      <details><summary>Tôi không quen dùng công nghệ, có sử dụng được không?</summary><p>Bạn có thể bắt đầu bằng một việc: mở Sổ đường huyết, nhập chỉ số vừa đo rồi chọn Lưu chỉ số. Các mục lịch thuốc và tái khám được đặt riêng để dễ tìm.</p></details>
      <details><summary>DiaTrack có thay bác sĩ tư vấn điều trị không?</summary><p>Không. DiaTrack hỗ trợ ghi chép và tổng hợp thông tin. Nội dung không thay thế chẩn đoán hoặc chỉ định của bác sĩ. Bạn không nên tự đổi thuốc dựa trên ứng dụng.</p></details>
      <details><summary>Tôi cần chuẩn bị gì để bắt đầu?</summary><p>Tạo tài khoản và chuẩn bị chỉ số từ máy đo đường huyết của bạn. Nếu chưa có chỉ số, bạn vẫn có thể tìm hiểu giao diện và các bài học.</p></details>
      <details><summary>Lịch thuốc lấy từ đâu?</summary><p>Bác sĩ nhập lịch theo đơn và duyệt trước khi lịch hiển thị cho bạn. Ứng dụng không tự kê thuốc hay quyết định liều.</p></details>
    </div></section>
    <section className="pitch-final"><span className="eyebrow">MỘT KHỞI ĐẦU NHỎ, NGAY HÔM NAY</span><h2>Để việc chăm sóc bản thân<br/>trở thành một nhịp quen.</h2><Link href="/register" className="primary-action">Tạo tài khoản <ArrowUpRight aria-hidden size={22}/></Link><p>Đã có tài khoản? <Link href="/login">Đăng nhập tại đây</Link></p></section>
    <p className="pitch-disclaimer">DiaTrack hiện là bản demo hỗ trợ theo dõi đái tháo đường. Không sử dụng ứng dụng thay cho chăm sóc y tế khi cần hỗ trợ khẩn cấp.</p>
  </div>;
}