"use client";
import { useAuth } from "@/lib/auth";
import VoicePersonaPicker from "@/components/VoicePersonaPicker";
import Link from "next/link";
import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SettingsPage() {
  const { user, loading, refresh } = useAuth();
  const [status, setStatus] = useState("");
  const [saving, setSaving] = useState(false);

  async function saveType(value: "type1" | "type2" | "unknown") {
    setSaving(true); setStatus("");
    try {
      const response = await fetch(`${API}/v1/auth/me/diabetes-type`, { method: "PATCH", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ diabetes_type: value }) });
      if (!response.ok) throw new Error("save failed");
      await refresh(); setStatus("Đã lưu thông tin tự khai báo.");
    } catch { setStatus("Chưa lưu được. Vui lòng thử lại."); }
    finally { setSaving(false); }
  }

  if (loading) return <div className="mx-auto max-w-2xl p-6 text-sm">Đang tải…</div>;
  if (!user) {
    return (
      <div className="mx-auto max-w-2xl p-6 text-sm">
        Bạn cần <Link href="/login" className="underline">đăng nhập</Link> để đổi giọng đọc.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl rounded-2xl border bg-white p-6 shadow-sm dark:bg-slate-900 dark:border-slate-700">
      <h1 className="text-3xl font-semibold">Cài đặt</h1>
      {user.role === "user" && <section className="mt-6 rounded-xl border p-4"><h2 className="text-lg font-semibold">Loại đái tháo đường trong hồ sơ</h2><p className="mt-2 text-sm">Đây là thông tin bạn tự khai báo, không phải chẩn đoán. Tư vấn AI chỉ dành cho người đã biết mình mắc týp 2. Dấu hiệu cấp cứu vẫn được cảnh báo.</p><label htmlFor="settings-diabetes-type" className="mt-4 block font-semibold">Chọn loại theo hồ sơ bác sĩ</label><select id="settings-diabetes-type" className="mt-2 w-full min-h-12 rounded-lg border px-3 dark:bg-slate-800" value={user.diabetes_type || "unknown"} disabled={saving} onChange={e=>saveType(e.target.value as "type1"|"type2"|"unknown")}><option value="unknown">Chưa rõ hoặc chưa được xác nhận</option><option value="type2">Týp 2</option><option value="type1">Týp 1</option></select>{status && <p role="status" className="mt-3">{status}</p>}</section>}
      <h2 className="mt-4 text-sm font-semibold">Giọng đọc bạn muốn nghe</h2>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        Đổi giọng đọc bất cứ lúc nào — giọng mới dùng ngay cho mọi câu trả lời.
      </p>
      <div className="mt-3">
        <VoicePersonaPicker userId={user.id} showSkip={false} />
      </div>
    </div>
  );
}
