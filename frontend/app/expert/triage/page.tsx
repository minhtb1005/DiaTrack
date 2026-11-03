"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { decideTriageReview, listPendingTriageReviews, fmtDT } from "@/lib/api";
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

  useEffect(() => {
    if (!allowed) return;
    const load = () => listPendingTriageReviews().then(d => setCases(d.cases || [])).catch(e => setError(e.message));
    load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [allowed]);

  const choose = (item: Case) => {
    setSelected(item.id); setPriority(item.proposed_priority); setMessage(""); setNotes(""); setError("");
  };
  const submit = async (decision: "approved" | "revised" | "rejected") => {
    if (!selected) return;
    setBusy(true); setError("");
    try {
      await decideTriageReview(selected, { decision, priority, message: decision === "rejected" ? undefined : message, notes });
      setCases(previous => previous.filter(item => item.id !== selected)); setSelected(null);
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  if (loading) return <p>Đang tải…</p>;
  if (!user) return <p>Cần <Link href="/login">đăng nhập</Link>.</p>;
  if (!allowed) return <p>403 — Chỉ điều dưỡng, bác sĩ hoặc admin được duyệt phân luồng.</p>;
  return <main className="space-y-4 p-4">
    <h1 className="text-2xl font-bold">Ca phân luồng chờ duyệt</h1>
    <p className="text-base">Đề xuất chưa được gửi cho bệnh nhân. Dấu hiệu khẩn đã được cảnh báo ngay.</p>
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
