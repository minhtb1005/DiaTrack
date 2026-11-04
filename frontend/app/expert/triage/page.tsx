"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { decideTriageReview, getTriageAuditReport, getTriageHandoff, listPendingTriageReviews, fmtDT } from "@/lib/api";
import { Button } from "@/components/ui/button";

type Case = { id: string; requester_id: string; message: string; latest_glucose_mgdl: number | null;
  symptom_onset: string | null; proposed_priority: string; rationale: string; source: string; created_at: string };

export default function TriageReviewPage() {
  const { user, loading } = useAuth();
  const allowed = !!user && ["nurse", "doctor", "admin"].includes(user.role);
  const [cases, setCases] = useState<Case[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [priority, setPriority] = useState("routine");
  const [message, setMessage] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [handoff, setHandoff] = useState<any>(null);
  const [audit, setAudit] = useState<any>(null);

  useEffect(() => {
    if (!allowed) return;
    const load = () => listPendingTriageReviews().then(d => setCases(d.cases || [])).catch(e => setError(e.message));
    load();
    getTriageAuditReport().then(setAudit).catch(e => setError(e.message));
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [allowed]);

  const choose = (item: Case) => {
    setSelected(item.id); setPriority(item.proposed_priority); setMessage(""); setNotes(""); setError(""); setHandoff(null);
    getTriageHandoff(item.id).then(setHandoff).catch(e => setError(e.message));
  };
  const submit = async (decision: "approved" | "revised" | "rejected") => {
    if (!selected) return;
    setBusy(true); setError("");
    try {
      await decideTriageReview(selected, { decision, priority, message: decision === "rejected" ? undefined : message, notes });
      setCases(previous => previous.filter(item => item.id !== selected)); setSelected(null);
      setAudit(await getTriageAuditReport());
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  if (loading) return <p>Đang tải…</p>;
  if (!user) return <p>Cần <Link href="/login">đăng nhập</Link>.</p>;
  if (!allowed) return <p>403 — Chỉ điều dưỡng, bác sĩ hoặc admin được duyệt phân luồng.</p>;
  return <main className="space-y-4 p-4">
    <h1 className="text-2xl font-bold">Ca phân luồng chờ duyệt</h1>
    <p className="text-base">Đề xuất chưa được gửi cho bệnh nhân. Dấu hiệu khẩn đã được cảnh báo ngay.</p>
    {audit && <section aria-label="Báo cáo kiểm toán" className="rounded-xl border bg-white p-4 dark:bg-slate-900">
      <h2 className="font-semibold">Đối chiếu quyết định điều dưỡng</h2>
      <p>{audit.disagreement_count}/{audit.reviewed_cases} ca khác đề xuất ({audit.disagreement_rate == null ? "chưa có dữ liệu" : `${(audit.disagreement_rate * 100).toFixed(1)}%`}).</p>
      <p>Gold red-flag v{audit.gold.version}: {audit.gold.red_flag_failures.length}/{audit.gold.red_flag_cases} ca sai.</p>
      {audit.gold.red_flag_failures.length > 0 && <p role="alert">Ca red-flag cần xử lý riêng: {audit.gold.red_flag_failures.join(", ")}</p>}
    </section>}
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {cases.length === 0 && <p>Không có ca chờ duyệt.</p>}
    {cases.map(item => <section key={item.id} className="rounded-xl border bg-white p-4 text-base dark:bg-slate-900">
      <h2 className="font-semibold">Ca {item.id.slice(0, 8)} · {fmtDT(item.created_at)}</h2>
      <p>Triệu chứng: {item.message}</p>
      <p>Đường huyết: {item.latest_glucose_mgdl ?? "chưa có"} mg/dL · Bắt đầu: {item.symptom_onset || "chưa rõ"}</p>
      <p>Đề xuất: {item.proposed_priority} · {item.rationale}</p>
      <p className="text-sm">Nguồn: {item.source}</p>
      <Button variant="outline" onClick={() => choose(item)}>Xem và duyệt</Button>
      {selected === item.id && <div className="mt-4 space-y-3">
        {handoff && <section aria-label="Phiếu bàn giao" className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
          <h3 className="font-semibold">Phiếu bàn giao</h3>
          <p>Triệu chứng: {handoff.symptoms}</p>
          <p>Đường huyết: {handoff.latest_glucose_mgdl ?? "chưa ghi nhận"} mg/dL</p>
          <p>Khởi phát: {handoff.symptom_onset || "chưa ghi nhận"}</p>
          <p>Dữ kiện thiếu: {handoff.missing_information.length ? handoff.missing_information.join(", ") : "Không có"}</p>
          <p>Lý do: {handoff.rationale}</p>
          <ul>{handoff.sources.map((source: any) => <li key={source.label}><a className="underline" href={source.href} target="_blank" rel="noreferrer">{source.label}</a></li>)}</ul>
          <p className="text-sm">{handoff.notice}</p>
        </section>}
        <label className="block">Mức ưu tiên
          <select aria-label="Mức ưu tiên cuối" value={priority} onChange={e => setPriority(e.target.value)} className="ml-2 rounded border p-2">
            <option value="routine">Thường</option><option value="soon">Khám sớm</option><option value="emergency">Khẩn cấp</option>
          </select>
        </label>
        <label className="block">Thông báo cho bệnh nhân
          <textarea aria-label="Thông báo cho bệnh nhân" value={message} onChange={e => setMessage(e.target.value)} className="mt-1 block w-full rounded border p-2" />
        </label>
        <label className="block">Ghi chú kiểm toán
          <textarea aria-label="Ghi chú kiểm toán" value={notes} onChange={e => setNotes(e.target.value)} className="mt-1 block w-full rounded border p-2" />
        </label>
        <div className="flex flex-wrap gap-2">
          <Button disabled={busy || message.trim().length < 10 || priority !== item.proposed_priority} onClick={() => submit("approved")}>Duyệt</Button>
          <Button disabled={busy || message.trim().length < 10} onClick={() => submit("revised")}>Sửa và duyệt</Button>
          <Button disabled={busy} variant="outline" onClick={() => submit("rejected")}>Từ chối</Button>
        </div>
      </div>}
    </section>)}
  </main>;
}
